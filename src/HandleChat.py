import copy, os, re, sys, time
from src.functions import rmatch, user_input
from src.PlanManager import PlanBase, Plan

_AI_LOOP_CONTINUE = object()
#
class HandleChat():

	#

	def Chat(self):
		self.hLG.echo("Handle.Chat() STARTING! MODE: {}".format(self.Options.get('MODE', 'build')),{'color':True})
		#
		# Load all existing plans on start
		from src.PlanManager import PlanBase
		PlanBase.LoadAll(self.Options.get('plans_path', 'plans'))
		#
		# Tool training: on fresh sessions, let the AI demonstrate tool usage once
		self._chat_tool_training()
		#
		_auto_continue_count = 0
		_skip_you = False
		while True:
			#
			if not _skip_you:
				# Check if tool training was injected mid-session — skip You() prompt
				if getattr(self, '_train_skip_you', False):
					self._train_skip_you = False
					_skip_you = True
					continue
				# Check if timer message was injected — skip You() prompt
				if getattr(self, '_timer_skip_you', False):
					self._timer_skip_you = False
					_skip_you = True
					continue
				x = self.You() # return: 0, 1, 2=continue, 3=break, 5=start build, 6=new session
				self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False})
				_auto_continue_count = 0  # reset on any direct user interaction
			else:
				x = 0
				_skip_you = False
			if x==5:
				self.StartBuild()
			elif x==6:
				return 6
			elif x>=3:
				return x # return 2=continue or 3=break, 4=update handle
			elif x==2:
				continue
			elif x==1:
				continue # direct tool call — skip AI, show prompt again
			
			#
			# AI()
			x = self.AI()
			self.hLG.echo("Handle.Chat() AI() response: {}".format(x),{'color':False})
			#
			self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1

			# After planDone — switch to BUILD mode and auto-continue
			if self._handle_plan_just_done():
				_skip_you = True
				continue

			# Blocked tool in plan mode — prompt user
			if getattr(self, '_plan_blocked_tool_alert', None):
				_skip_you = self._handle_plan_blocked_alert()
				continue

			# Auto-re-enter AI() when plan tasks remain and ALL_TASKS mode is on
			_auto_continue_count, _reenter = self._handle_auto_continue(_auto_continue_count)
			if _reenter:
				_skip_you = True
				continue

	#

	def You(self, data=None, opts=None):
		if opts is None:
			opts = {}
		# Prepare user content
		inp = data
		#
		if inp==None:
			self.hLG.echo("You: ",{ 'end':'', 'flush':True, 'color':True, 'colorValue':'green', 'debugOnly':False, 'streamDone':True})
			try:
				inp = user_input({'quit_with_ctrlx':True, 'poll_callback': self.hTMR.poll})
			except Exception as E:
				sys.exit(1)
		
		# Handle user commands
		if rmatch(inp,"^!.*"):
			cmds = self.cmds.cmds
			for k in cmds:
				if rmatch(inp,cmds[k]['regex']):
					return cmds[k]['func'](inp)
			return 2 # as continue
		# Repeat user input. Content too large
		if len(inp)>self.Options['AI_MAX_CONTENT_LEN']:
			print("FAILED: content length too large. ( {} / {} )".format( len(inp), self.Options['AI_MAX_CONTENT_LEN'] ))
			return 2 # as continue / repeat
		
		# Append user content
		if inp != None:
			# Prepend pending tool notice if any
			notice = getattr(self, '_pending_tool_notice', None)
			if notice:
				inp = notice + "\n\n" + inp
				self._pending_tool_notice = None
			self._last_response_hash = None
			# Reset consecutive error tracking on new user input
			self.tool_errors = 0
			self._last_failed_tool = None
			self._last_failed_tool_count = 0
			self.Response('user',{'content':inp})
		return 0 # Input without command or successed command with input data

	#

	def _get_tip_summary(self):
		try:
			tips = self.hTM.list()
			if not tips:
				return ""
			parts = []
			for key, info in sorted(tips.items()):
				if key.startswith('_cache/'):
					continue
				parts.append("{} ({} entr{})".format(info['title'], info['count'], 'ies' if info['count'] != 1 else 'y'))
			if not parts:
				return ""
			return "[Tips: {} — use <GetTip> to retrieve, <ReinsertTip> to bring into context]".format(', '.join(parts))
		except Exception:
			return ""

	#

	def _is_plan_complete(self):
		"""Check if the model has signaled plan completion.
		Checks the planDone tool-call flag, and optionally scans assistant
		messages for text patterns (controlled by PLAN_COMPLETE_TEXT_SCAN)."""
		# Fast path: explicit <planDone/> tool call
		if getattr(self, '_plan_done_called', False):
			return True
		# Optional: scan assistant text for plan-completion phrases
		if not self.Options.get('PLAN_COMPLETE_TEXT_SCAN', True):
			return False
		for msg in reversed(self.hHM.msgs):
			if msg.get('role') != 'assistant':
				continue
			content = msg.get('content', '')
			if not content.strip():
				continue
			patterns = [
				r'plan\s+is\s+(ready|complete|done|finished)',
				r'`?!?MODE\s+build',
				r'switch\s+to\s+build',
				r'start\s+building',
				r'planning\s+(is\s+)?(complete|done|finished)',
			]
			lower = content.lower()
			for p in patterns:
				if re.search(p, lower):
					self._plan_done_called = True
					return True
		return False

	#

	def _try_auto_continue(self):
		"""If in BUILD mode with pending tasks and auto-continue enabled,
		advance to next task and inject a continuation user message.
		Returns True if a message was injected."""
		if self.Options.get('MODE') != 'build':
			self.bg_log("_try_auto_continue: not build mode")
			return False
		if not self.Options.get('AUTO_CONTINUE_TASKS', True):
			self.bg_log("_try_auto_continue: AUTO_CONTINUE_TASKS disabled")
			return False

		from src.PlanManager import PlanBase
		if not PlanBase.draft:
			self.bg_log("_try_auto_continue: no draft")
			return False

		# If model already advanced via <nextTask>, there's an in_progress task.
		# Inject its instruction without calling nextTask() again (avoids skip).
		in_progress_task = None
		for t in PlanBase.draft.tasks.values():
			if t.status == 'in_progress':
				in_progress_task = t
				break

		if not in_progress_task:
			# Don't call nextTask() here — the outer Chat loop will find the
			# first pending task via StartBuild (or the model will call startBuild).
			# Calling nextTask() from inside AI() can cause premature advancement.
			task_statuses = [(tid, t.status) for tid, t in PlanBase.draft.tasks.items()]
			self.bg_log("_try_auto_continue: no in_progress task — statuses={}".format(task_statuses))
			return False
		else:
			next_instruction = in_progress_task.instruction or '(continue with the plan)'

		total = len(PlanBase.draft.tasks)
		completed = sum(1 for t in PlanBase.draft.tasks.values() if t.status == 'completed')
		task_number = completed + 1

		task_label = next_instruction[:60] + '...' if len(next_instruction) > 60 else next_instruction
		msg = "continue task {} / {}...\n{}".format(task_number, total, next_instruction)
		self.Response('user', {'content': msg})
		self.hLG.echo("Auto-continue: task {}/{} — {}".format(task_number, total, task_label),
			{'color': True, 'colorValue': 'green', 'debugOnly': False})
		self._write_current_task()
		return True

	#

	def _write_current_task(self):
		"""Write current task state to current_task.txt for tail -f monitoring."""
		from src.PlanManager import PlanBase
		path = os.path.join(os.getcwd(), 'current_task.txt')
		if not PlanBase.draft:
			with open(path, 'w') as f:
				f.write("No active plan.\n")
			return
		plan = PlanBase.draft
		current = next((t for t in plan.tasks.values() if t.status == 'in_progress'), None)
		total = len(plan.tasks)
		done = sum(1 for t in plan.tasks.values() if t.status == 'completed')
		blocked = sum(1 for t in plan.tasks.values() if t.status == 'blocked')
		now = time.strftime('%Y-%m-%d %H:%M:%S')
		lines = [
			"Plan: {}".format(plan.title or '(untitled)'),
			"Progress: {}/{} completed ({} blocked)".format(done, total, blocked),
		]
		if current:
			lines.extend([
				"--- Current Task ---",
				"ID: {}".format(current.id),
				"Title: {}".format(current.title or '(no title)'),
				"Instruction: {}".format(current.instruction or '(no instruction)'),
				"Status: {}".format(current.status),
			])
		else:
			lines.append("No task in progress.")
		lines.append("Updated: {}".format(now))
		with open(path, 'w') as f:
			f.write('\n'.join(lines) + '\n')

	#

	def _check_ai_interrupt(self):
		"""Non-blocking check for Ctrl+D key press at iteration boundaries."""
		import select
		if not sys.stdin.isatty():
			return False
		try:
			if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
				import tty, termios
				fd = sys.stdin.fileno()
				old = termios.tcgetattr(fd)
				try:
					tty.setraw(fd)
					ch = sys.stdin.read(1)
					return ch == '\x04'
				finally:
					termios.tcsetattr(fd, termios.TCSADRAIN, old)
		except:
			pass
		return False

	#

	def _show_ai_interrupt_menu(self):
		"""Show menu when Ctrl+D interrupts the AI loop."""
		self.hLG.echo("\n  ═══ AI Loop Interrupted ═══",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  1. Continue AI loop",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  2. Stop AI — return to chat prompt",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  3. Cancel — quit session",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  Choice (1-3): ",
			{'end':'','flush':True,'color':True,'colorValue':'blue','debugOnly':False})
		ans = user_input({'quit_with_ctrlx':True}).strip()
		ans = re.sub(r'[^0-9]', '', ans)
		if ans == '2':
			return 2
		if ans == '3':
			return 3
		return 1

	#

	def AI(self,opts=None):
		if opts is None:
			opts = {}
		#
		self.hLG.echo("Handle.AI() STARTING, opts: {}".format(opts),{'color':False})
		#
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		opt_stream_cb     = opts.get('stream_callback')
		#
		# Manage context window — summarize or clear if we're over the limit
		self._manage_context()
		self._show_context_usage()
		#
		# Loop to handle multiple rounds of tool calls
		max_iterations = self.Options.get('AI_MAX_ITERATIONS', 10)
		iteration = 0
		_tools_were_called = False
		_tools_last_error = False
		_alt_model_index = 0  # index into ALTERNATIVE_MODELS list

		while iteration < max_iterations:
			iteration += 1

			# Check for Ctrl+D interrupt at iteration boundary
			out = self._ai_apply_status(self._ai_interrupt_boundary(_tools_were_called))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Check for timer injection at iteration boundary
			self._ai_timer_inject()

			# Short-circuit: ≥3 consecutive tool errors → break loop with recovery
			out = self._ai_apply_status(self._ai_tool_error_short_circuit())
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Re-check context before each model call — tool results may have
			# added large data (e.g., base64 images) since the last check
			self._manage_context()
			self._show_context_usage("iter {}".format(iteration))

			result        = ""
			res           = {}
			msgs = copy.deepcopy(self.hHM.msgs)
			# Strip malformed entries (no `role` key) that slipped into history
			msgs = [m for m in msgs if isinstance(m, dict) and m.get('role')]

			# Auto-inject tip availability into last user message
			self._inject_tip_summary(msgs)

			# Nothing to send to AIIA, continue to user input!
			if len(msgs)<=0:
				print("WARNING: msgs len is 0, Repeating user_input!")
				return 2 # as continue

			# Chat without tools, normal chat (XML tools handle themselves)
			self.hLG.echo("DEBUG preparing chat (iteration {})".format(iteration),{'color':False})

			# Resolve lightweight image refs → base64 for the API call
			self._resolve_image_refs(msgs)

			# Build chat parameters and try the model call with retries
			chat_params = self._build_chat_params(msgs)
			_out = self._chat_with_retries(chat_params, iteration, opt_stream_cb)
			if _out['context_cleared']:
				continue
			if _out['model_failed']:
				continue
			result = _out['result']
			res = _out['res']

			# Ctrl+D interrupt during streaming — show menu
			out = self._ai_apply_status(self._ai_handle_stream_interrupt(result, _tools_were_called))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Show post-response context usage
			self._show_context_usage("after +{}".format(
				result.get('response_tokens', 0) or self.Options.get('NUM_LAST_RESPONSE_TOKENS', 0)))

			# Stop loop on persistent stream errors (429/rate-limit) — let user decide
			# On stream stall — try cascading alternative models before giving up
			status = self._ai_handle_stream_error(result, _tools_were_called, _alt_model_index)
			if status and 'alt_model_index' in status:
				_alt_model_index = status['alt_model_index']
			out = self._ai_apply_status(status)
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Used if CTRL+C to save last/draft content to chat history
			self.Options['DRAFT_RESPONSE'] = res

			# Track whether the model made tool calls this turn
			if result.get('invocations'):
				_tools_were_called, _tools_last_error = self._ai_track_tool_calls(result)

			# Blocked tool in plan mode — stop and alert user
			out = self._ai_apply_status(self._ai_handle_plan_blocked(result))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Request body too large — auto-clear context and retry
			out = self._ai_apply_status(self._ai_handle_stream_too_large(result))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Track planDone tool call — stop AI loop and wait for user input
			out = self._ai_apply_status(self._ai_handle_plan_done(result))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Track iterations without <nextTask> and remind model
			out = self._ai_apply_status(self._ai_nexttask_reminder(result, _tools_were_called))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Stop if model response is empty (no content, no tools)
			out = self._ai_apply_status(self._ai_handle_empty_response(result, _tools_were_called))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Stop if jobDone was called
			out = self._ai_apply_status(self._ai_handle_job_done(result))
			if out is _AI_LOOP_CONTINUE:
				continue
			if out is not None:
				return out

			# Check if tools were executed by looking for tool invocations in result
			status = self._ai_handle_no_invocations(result, _tools_were_called,
				_tools_last_error, opt_return_object)
			if status:
				if status['action'] == 'continue':
					_tools_were_called = status['tools_were_called']
					_tools_last_error = status['tools_last_error']
					continue
				return status['value']
		self._last_ai_had_tools = _tools_were_called

	#

	def _ai_apply_status(self, status):
		if not status:
			return None
		if status['action'] == 'continue':
			return _AI_LOOP_CONTINUE
		return status['value']

	def _ai_interrupt_boundary(self, tools_were_called):
		if self._check_ai_interrupt():
			self.hLG.echo("\n[Ctrl+D detected]",
				{'color':True, 'colorValue':'blue','debugOnly':False})
			choice = self._show_ai_interrupt_menu()
			if choice == 2:
				self._last_ai_had_tools = tools_were_called
				return {'action':'return', 'value':True}
			if choice == 3:
				return {'action':'return', 'value':3}
		return None

	def _ai_timer_inject(self):
		if self.hTMR.check_interrupt():
			self.hLG.echo("\n[Timer message injected]",
				{'color':True, 'colorValue':'cyan','debugOnly':False})
			# choice 1: continue loop
		return None

	def _ai_tool_error_short_circuit(self):
		if self.tool_errors >= 3:
			self.bg_log("{} consecutive tool errors, last tool: {}".format(
				self.tool_errors, self._last_failed_tool), "WARN")
			self.hLG.echo(
				"AI loop: {} consecutive tool errors — breaking loop".format(self.tool_errors),
				{'color':True, 'colorValue':'orange','debugOnly':False})
			recovery_msg = (
				"[System: Tool execution failed {} times consecutively. "
				"The last failed tool was `{}`. "
				"Use the correct XML format shown in the tool error messages above. "
				"Do not repeat the same malformed tool call.]"
			).format(self.tool_errors, self._last_failed_tool)
			self.Response('user', {'content': recovery_msg})
			self.tool_errors = 0
			self._last_failed_tool = None
			self._last_failed_tool_count = 0
			return {'action':'continue'}
		return None

	def _ai_handle_stream_interrupt(self, result, tools_were_called):
		if result.get('ctrl_d_interrupt'):
			choice = self._show_ai_interrupt_menu()
			if choice == 2:
				self.Options['AUTO_CONTINUE_TASKS'] = False
				self.Options['AUTO_CONTINUE_ALL_TASKS'] = False
				self._last_ai_had_tools = tools_were_called
				return {'action':'return', 'value':True}
			if choice == 3:
				return {'action':'return', 'value':3}
			return {'action':'continue'}
		return None

	def _ai_handle_stream_error(self, result, tools_were_called, alt_model_index):
		if result.get('stream_error'):
			err = result['stream_error'].lower()
			if '429' in err or 'usage limit' in err or 'rate limit' in err:
				self.hLG.echo("Stream rate-limited — stopping AI loop.",
					{'color':True, 'colorValue':'red','debugOnly':False})
				self._last_ai_had_tools = tools_were_called
				return {'action':'return', 'value':True, 'alt_model_index':alt_model_index}
			if 'stream stalled' in err or 'timeout' in err:
				alt_models = self.Options.get('ALTERNATIVE_MODELS', [])
				switched = False
				while alt_model_index < len(alt_models):
					alt_model = alt_models[alt_model_index]
					alt_model_index += 1
					if self.Options['AI_MODEL'] != alt_model:
						prev_model = self.Options['AI_MODEL']
						self.hLG.echo("Stream stalled — switching to {}...".format(alt_model),
							{'color':True, 'colorValue':'cyan','debugOnly':False})
						self.bg_log("Stream stall fallback: {} → {} (attempt {}/{})".format(
							prev_model, alt_model, alt_model_index, len(alt_models)), "WARN")
						self.Options['AI_MODEL'] = alt_model
						self.Response('user', {'content':
							"[System: The previous model ({}) timed out. "
							"Switched to '{}'. "
							"Please continue from where you left off.]".format(prev_model, alt_model)})
						switched = True
						break
				if switched:
					return {'action':'continue', 'alt_model_index':alt_model_index}
				# No more alternatives — stop
				self.hLG.echo("Stream stalled — no more fallback models, stopping AI loop.",
					{'color':True, 'colorValue':'red','debugOnly':False})
				self.bg_log("Stream stall — all fallback models exhausted, stopping.", "WARN")
				self._last_ai_had_tools = tools_were_called
				return {'action':'return', 'value':True, 'alt_model_index':alt_model_index}
		return None

	def _ai_track_tool_calls(self, result):
		tools_were_called = True
		tools_last_error = False
		if self.hHM.msgs and self.hHM.msgs[-1].get('role') == 'tool':
			tools_last_error = self.hHM.msgs[-1].get('content', '').startswith('Error:')
		return tools_were_called, tools_last_error

	def _ai_handle_plan_blocked(self, result):
		if result.get('plan_blocked'):
			self._plan_blocked_tool_alert = result['plan_blocked']
			self._last_ai_had_tools = True
			return {'action':'return', 'value':True}
		return None

	def _ai_handle_stream_too_large(self, result):
		if result.get('stream_too_large'):
			self.hLG.echo("Request body too large — auto-clearing context and retrying...",
				{'color':True, 'colorValue':'orange','debugOnly':False})
			self._auto_clear()
			self.Response('user', {
				'content': "[System: The conversation was too large for the model. "
				"Context has been cleared to free memory. Continue with the task.]"
			})
			return {'action':'continue'}
		return None

	def _ai_handle_plan_done(self, result):
		if result.get('plan_done'):
			self.bg_log("AI() exit: plan_done called")
			self._plan_done_called = True
			self._last_ai_had_tools = False
			self._plan_just_done = True
			return {'action':'return', 'value':True}
		return None

	def _ai_nexttask_reminder(self, result, tools_were_called):
		if result.get('invocations'):
			has_nextTask = any(inv.get('name') == 'nextTask' for inv in result['invocations'])
			if has_nextTask:
				self._iterations_since_nextTask = 0
			elif tools_were_called:
				self._iterations_since_nextTask += 1
		elif tools_were_called and not result.get('job_done'):
			self._iterations_since_nextTask += 1
		remind_after = self.Options.get('AUTO_CONTINUE_REMIND_AFTER', 20)
		if (tools_were_called and not result.get('job_done') and
			self._iterations_since_nextTask >= remind_after):
			self._iterations_since_nextTask = 0
			self.Response('user', {'content':
				"[System: You've gone {} iterations without calling `<nextTask>completed</nextTask>`. "
				"If the current task is done, call `<nextTask>completed</nextTask>` to advance. "
				"If blocked, call `<nextTask>blocked</nextTask>`.]".format(remind_after)})
			return {'action':'continue'}
		return None

	def _ai_handle_empty_response(self, result, tools_were_called):
		if not result.get('response', '').strip() and not result.get('invocations'):
			self.bg_log("AI() exit: empty response (tools_were_called={})".format(tools_were_called))
			self._last_ai_had_tools = tools_were_called
			return {'action':'return', 'value':True}
		return None

	def _ai_handle_job_done(self, result):
		if result.get('job_done'):
			self.bg_log("AI() exit: job_done called")
			self._last_ai_had_tools = False
			return {'action':'return', 'value':True}
		return None

	def _ai_handle_no_invocations(self, result, tools_were_called, tools_last_error, opt_return_object):
		if not result['invocations']:
			# No more tool calls
			# Auto-continue to next task if model made tool calls and no errors
			self.bg_log("AI() exit: no invocations, tools_were_called={}, last_error={}".format(
				tools_were_called, tools_last_error))
			if tools_were_called and not tools_last_error and self._try_auto_continue():
				return {'action':'continue', 'tools_were_called':False, 'tools_last_error':False}
			self._last_ai_had_tools = tools_were_called
			if opt_return_object:
				return {'action':'return', 'value':result['response']}
			return {'action':'return', 'value':True}
		return None

	def _inject_tip_summary(self, msgs):
		"""Append the tip availability notice to the last user message."""
		tip_summary = self._get_tip_summary()
		if tip_summary:
			for i in range(len(msgs) - 1, -1, -1):
				if msgs[i].get('role') == 'user':
					msgs[i]['content'] = msgs[i]['content'] + "\n\n" + tip_summary
					break

	#

	def _resolve_image_refs(self, msgs):
		"""Resolve lightweight image refs → base64 for the API call."""
		if not self.Options.get('AI_VISION_ENABLED', True):
			return
		try:
			from src.MediaHelper import ImageCache
			ImageCache.resolve_all(msgs)
		except Exception as e:
			self.hLG.echo("Warning: failed to resolve image refs: {}".format(e),
				{'color':True, 'colorValue':'yellow','debugOnly':False})

	#

	def _build_chat_params(self, msgs):
		"""Build chat request parameters from Options (num_predict, think)."""
		chat_opts = dict(self.Options['AI_OPTIONS'])
		num_predict = self.Options.get('NUM_PREDICT')
		if num_predict is not None:
			chat_opts['num_predict'] = num_predict
		chat_params = {
			'model': self.Options['AI_MODEL'],
			'messages': msgs,
			'stream': True,
			'options': chat_opts,
		}
		# Optional: pass think=True for models that support the reasoning
		# API (e.g. DeepSeek R1). Set AI_THINK=true in config to enable.
		if self.Options.get('AI_THINK', False):
			chat_params['think'] = True
		return chat_params

	#

	def _chat_with_retries(self, chat_params, iteration, opt_stream_cb):
		"""Call the backend with retries, handling too-large requests and
		guiding the model to switch after repeated failures.
		Returns {'result', 'res', 'context_cleared', 'model_failed'} — the
		caller decides whether to continue the AI loop."""
		self.bg_log("AI request (iteration {}, msgs={})".format(
			iteration, len(chat_params['messages'])))
		model_retries = 0
		max_retries = self.Options.get('AI_MODEL_RETRIES', 3)
		model_timeout = self.Options.get('AI_MODEL_TIMEOUT', 120)
		while True:
			try:
				backend = self._get_backend()
				res = backend.chat(**chat_params, timeout=model_timeout if model_timeout else None)
				result = self.Parse(res,{'return_object':True,'stream_callback':opt_stream_cb})
				return {'result': result, 'res': res,
						'context_cleared': False, 'model_failed': False}
			except Exception as e:
				if self._retry_too_large(e):
					return {'result': None, 'res': None,
							'context_cleared': True, 'model_failed': False}
				model_retries += 1
				if model_retries > max_retries:
					return self._retry_exhausted(max_retries, e)
				self.bg_log(
					"Model call failed (attempt {}/{}): {}".format(
						model_retries, max_retries, e))
				self.hLG.echo(
					"AI connection error (attempt {}/{}): {} — retrying...".format(
						model_retries, max_retries, str(e)),
					{'color':True, 'colorValue':'red','debugOnly':False})
				time.sleep(1)

	def _retry_too_large(self, e):
		"""True when the request was rejected for being too large — clear
		context and let the caller retry with fewer messages."""
		err_str = str(e).lower()
		if not ('too large' in err_str or '400' in err_str or '413' in err_str or 'request body' in err_str):
			return False
		self.hLG.echo("AI request too large — auto-clearing context and retrying...",
			{'color':True, 'colorValue':'orange','debugOnly':False})
		self._auto_clear()
		return True

	def _retry_exhausted(self, max_retries, e):
		"""Final failure — inject a recovery message guiding the model to
		switch models/backends. Returns the model_failed result dict."""
		self.bg_log(
			"Model call failed after {} attempts: {}".format(max_retries, e),
			"ERROR")
		self.hLG.echo(
			"AI model unavailable after {} attempts — guiding model to switch".format(max_retries),
			{'color':True, 'colorValue':'red','debugOnly':False})
		self.Response('user', {'content': self._recovery_message(max_retries)})
		self.tool_errors = 0
		self._last_failed_tool = None
		self._last_failed_tool_count = 0
		return {'result': None, 'res': None,
				'context_cleared': False, 'model_failed': True}

	def _recovery_message(self, max_retries):
		"""System guidance for the model after repeated API failures."""
		if self._get_backend().is_vllm:
			return (
				"[System: The model API call failed {} times consecutively. "
				"The vLLM server at {} may be down or the model name is wrong. "
				"Check the server, use `!MODELS` to list available models, "
				"or switch backends with `!BACKEND ollama`.]"
			).format(max_retries, self.Options.get('VLLM_HOST', ''))
		return (
			"[System: The model API call failed {} times consecutively. "
			"This is likely a cloud-model connectivity issue. "
			"Switch to a local model with `!MODEL gemma3:12b` or another available local model.]"
		).format(max_retries)

	#

	def _replace_system_prompt(self, text):
		"""Replace the last system message in history with `text`.
		If no system message exists, append a new one."""
		for i in range(len(self.hHM.msgs) - 1, -1, -1):
			if self.hHM.msgs[i].get('role') == 'system':
				self.hHM.msgs[i]['content'] = text
				return
		self.Response('system', {'content': text})

	#

	def StartBuild(self, plan_id=None):
		if not self._ensure_plan_loaded(plan_id):
			return
		first_task = self._find_first_task()
		if first_task:
			PlanBase.draft.save(self.Options.get('plans_path', 'plans'))
			PlanBase.LogProgress(first_task.id, "Build started", self.Options.get('plans_path', 'plans'))
			task_number = sum(1 for t in PlanBase.draft.tasks.values() if t.status in ["completed", "in_progress"])
			total_tasks = len(PlanBase.draft.tasks)
			self.Response('user', {'content': "Mode changed to BUILD. You can now make changes.\n\nTask {}/{} - {}".format(task_number, total_tasks, first_task.instruction)})
			self.hLG.echo("Started build: Task {}/{}".format(task_number, total_tasks), {'color':True, 'colorValue':'green'})
			self._write_current_task()
		else:
			self.hLG.echo("No pending tasks in plan!", {'color':True, 'colorValue':'orange'})
			self.Response('user', {'content': "Mode changed to BUILD. All tasks in the plan are completed. Waiting for your instruction."})

	def _ensure_plan_loaded(self, plan_id=None):
		# Make sure PlanBase.draft is set, loading by id or latest from disk.
		# Returns True if a draft is available, False if none could be loaded.
		if PlanBase.draft:
			return True
		if plan_id:
			plan = Plan.load(plan_id, self.Options.get('plans_path', 'plans'))
			if plan:
				PlanBase.draft = plan
				return True
			self.hLG.echo("Plan {} not found".format(plan_id), {'color':True, 'colorValue':'red'})
			return False
		# Try to load the latest plan from disk
		plans_dir = self.Options.get('plans_path', 'plans')
		if os.path.isdir(plans_dir):
			json_files = sorted(
				[f for f in os.listdir(plans_dir) if f.endswith('.json')],
				key=lambda f: os.path.getmtime(os.path.join(plans_dir, f)),
				reverse=True)
			if json_files:
				latest_id = json_files[0].replace('.json', '')
				plan = Plan.load(latest_id, plans_dir)
				if plan:
					PlanBase.draft = plan
					self.hLG.echo("Loaded latest plan from disk: {}".format(plan.title),
						{'color':True, 'colorValue':'cyan'})
					return True
		self.hLG.echo("No active plan. Use createPlan first.", {'color':True, 'colorValue':'red'})
		return False

	def _find_first_task(self):
		# Pick the first actionable task: an in_progress one, else the next pending.
		first_task = None
		for t in PlanBase.draft.tasks.values():
			if t.status == "in_progress":
				first_task = t
				break
		if not first_task:
			for tid, task in PlanBase.draft.tasks.items():
				if task.status == "pending":
					first_task = task
					task.status = "in_progress"
					task.startTimestamp = time.time()
					break
		return first_task

	#

	def _chat_tool_training(self):
		"""Tool training: on fresh sessions, let the AI demonstrate tool usage once."""
		if (self.Options.get('TOOL_TRAINING', True) and
			not self.Options.get('CONTINUE', False) and
			len(self.hHM.msgs) <= 2):
			self.hLG.echo("Tool training — warming up model on available tools...",
				{'color':True, 'colorValue':'cyan','debugOnly':False})
			self.Response('user', {'content':
				"[Tool Training Session]\n"
				"List all tools you have available and demonstrate at least 3 of them "
				"with complete XML examples showing the required parameters. "
				"Do NOT use GetTip — use TreeView, ReadFile, and WriteFile instead."})
			self.AI()
			self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1

	#

	def _handle_plan_just_done(self):
		"""After planDone — switch to BUILD mode and auto-continue.
		Returns True if the plan-just-done transition was triggered."""
		if not getattr(self, '_plan_just_done', False):
			return False
		del self._plan_just_done
		# Actually switch to build mode
		if self.Options.get('MODE') != 'build':
			self.Options['MODE'] = 'build'
			self._write_state({'mode': 'build'})
			self._replace_system_prompt(self.hPP._get_mode_instructions('build'))
		self.hLG.echo("Plan complete — switched to BUILD mode. Starting first task.",
			{'color':True, 'colorValue':'green','debugOnly':False})
		self.bg_log("Chat: _plan_just_done — switching to build, triggering StartBuild")
		# Trigger StartBuild to inject first task
		self.StartBuild()
		return True

	#

	def _handle_plan_blocked_alert(self):
		"""Handle a plan-blocked tool alert — show the 1-4 user menu.
		Returns the new _skip_you value to apply (caller always continues)."""
		tool_name = self._plan_blocked_tool_alert
		del self._plan_blocked_tool_alert
		# Safety net: if MODE is already build, auto-dismiss — the alert
		# is stale (shouldn't happen but prevents confusing menu in build).
		if self.Options.get('MODE') == 'build':
			self.hLG.echo("⚠ Plan-blocked alert for '{}' dismissed — already in BUILD mode.".format(tool_name),
				{'color':True, 'colorValue':'orange','debugOnly':False})
			self.Response('user', {'content': "[System: Tool '{}' was blocked but you are already in BUILD mode. Continue with the task.]".format(tool_name)})
			return True
		self.hLG.echo("Model tried to use '{}' in PLAN mode.".format(tool_name),
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  1. Switch to BUILD mode (allow the tool)",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  2. Stay in PLAN mode (block the tool, continue planning)",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  3. Cancel AI (return to user prompt)",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("  4. Continue (dismiss, let the model proceed)",
			{'color':True, 'colorValue':'blue','debugOnly':False})
		self.hLG.echo("Choice (1-4): ", {'end':'','flush':True,'color':True,'colorValue':'blue','debugOnly':False})
		ans = user_input({'quit_with_ctrlx':True}).strip()
		ans = re.sub(r'[^0-9]', '', ans)
		if ans == '1':
			self.Options['MODE'] = 'build'
			self._write_state({'mode': 'build'})
			self._replace_system_prompt(self.hPP._get_mode_instructions('build'))
			self.StartBuild()
			return True
		if ans == '3':
			# Persist plan state so the on-disk file matches memory
			from src.PlanManager import PlanBase
			if PlanBase.draft:
				PlanBase.draft.save(self.Options.get('plans_path', 'plans'))
			mode = self.Options.get('MODE', 'plan').upper()
			self.Response('user', {'content': "[Cancelled. Mode: {}. Waiting for your instruction.]".format(mode)})
			return False
		if ans == '4':
			return True
		# Default: option 2 or invalid — stay in plan mode
		self.Response('user', {'content': "Understood. Staying in PLAN mode — write tools remain blocked."})
		return True

	#

	def _handle_auto_continue(self, auto_continue_count):
		"""Auto-re-enter AI() when plan tasks remain and ALL_TASKS mode is on.
		Returns (new_count, reenter) — caller sets _skip_you=True and continues
		when reenter is True."""
		if not self.Options.get('AUTO_CONTINUE_ALL_TASKS', True):
			return auto_continue_count, False
		mode = self.Options.get('MODE', 'plan')
		should_reenter = False
		if mode == 'build' and self.Options.get('AUTO_CONTINUE_TASKS', True):
			if PlanBase.draft:
				task_statuses = [(tid, t.status) for tid, t in PlanBase.draft.tasks.items()]
				has_remaining = any(
					t.status in ('pending', 'in_progress')
					for t in PlanBase.draft.tasks.values())
				self.bg_log("Auto-continue check: tasks={}, remaining={}".format(task_statuses, has_remaining))
				if has_remaining:
					should_reenter = True
			else:
				self.bg_log("Auto-continue check: no draft")
		elif mode == 'plan' and self._last_ai_had_tools:
			if not self._is_plan_complete():
				should_reenter = True
			else:
				self.bg_log("Auto-continue check: plan complete (text_scan={}, flag={})".format(
					self.Options.get('PLAN_COMPLETE_TEXT_SCAN', True),
					getattr(self, '_plan_done_called', False)))
		else:
			self.bg_log("Auto-continue check: mode={}, last_ai_had_tools={}".format(mode, self._last_ai_had_tools))
		if not should_reenter:
			self.bg_log("Auto-continue: NOT re-entering AI() — waiting for user")
		if should_reenter:
			auto_continue_count += 1
			if auto_continue_count >= 50:
				self.hLG.echo(
					"Auto-continue: reached 50 rounds — stopping.",
					{'color':True, 'colorValue':'orange','debugOnly':False})
			elif mode == 'plan':
				self.hLG.echo(
					"Auto-continue: AI round {}/50 — continuing plan creation".format(auto_continue_count),
					{'color':True, 'colorValue':'cyan','debugOnly':False})
				self.Response('user', {'content': 'Continue creating plan tasks.'})
				return auto_continue_count, True
			else:
				total = len(PlanBase.draft.tasks)
				completed = sum(1 for t in PlanBase.draft.tasks.values() if t.status == 'completed')
				current_task = next((t for t in PlanBase.draft.tasks.values() if t.status == 'in_progress'), None)
				task_num = completed + 1
				task_inst = current_task.instruction if current_task else '(waiting)'
				task_label = task_inst[:60] + '...' if len(task_inst) > 60 else task_inst
				self.hLG.echo(
					"Auto-continue: AI round {}/50 — task {}/{}: {}".format(
						auto_continue_count, task_num, total, task_label),
					{'color':True, 'colorValue':'green','debugOnly':False})
				self.Response('user', {'content': 'Continue task {}/{}...\n{}'.format(task_num, total, task_inst)})
				return auto_continue_count, True
		return auto_continue_count, False
