import hashlib, re
#
# Sentinel returned by _parse_* helpers when parsing should continue (no early return)
_PARSE_CONTINUE = object()
#
class HandleParse():

	#

	def One(self,data, opts=None):
		if opts is None:
			opts = {}
		
		opt_history_num    = opts.get('history_num')
		self.Init()
		#
		if opt_history_num!=None:
			# load specific history
			self.hHM.Update()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
		#
		# Apply persona settings (model override, max_iterations, thinking)
		# so -Y mode behaves the same as interactive mode
		if self.Options.get('INSTRUCT_CLASS_OVERRIDE', False):
			self.hIM.ApplyPersonaModel(self.Options['INSTRUCT_CLASS'])
		# Apply model registry for -Y mode (covers -m flag without persona)
		from src.ModelRegistry import apply as apply_registry
		_model = self.Options.get('AI_MODEL', '')
		if _model:
			_changes = apply_registry(self.Options, _model)
			if _changes:
				for _c in _changes:
					self.hLG.echo("  Model config: {}".format(_c),
						{'color':True, 'colorValue':'cyan'})
		#
		# Add system message if not already present (for -Y flag mode)
		system_exists = False
		for msg in self.hHM.msgs:
			if msg['role'] == 'system':
				system_exists = True
				break
		if not system_exists:
			# Add mode instructions from config
			mode = self.Options.get('MODE', 'build')
			system_msg = self.hPP._get_mode_instructions(mode)
			self.Response('system',{'content':system_msg})
		#
		self.You( data, opts )
		#
		return self.AI( opts )
	

	#

	def Parse(self, res, opts=None):
		if opts is None:
			opts = {}
		
		#
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color    = opts['skip_color'] if 'skip_color' in opts else False
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		opt_stream_cb     = opts.get('stream_callback')
		color             = True
		if opt_skip_color:
			color=False
		#
		stream_error = None
		response = self.Stream( res, color, opt_stream_cb )
		#
		# Strip <think>...</think> from content — the model may include these
		# in its content field (separate from native thinking API).  Stripping
		# early (before any early-return path) prevents spurious tool detection,
		# hash mismatches, and history pollution from interrupted streams.
		self._strip_think_tags(response)
		#
		# Stream error — signal auto-clear for request-too-large errors
		if 'error' in response:
			stream_error = response['error']
			_done = self._parse_stream_error(stream_error, response, opt_return_object)
			if _done is not _PARSE_CONTINUE:
				return _done

		# Ctrl+D interrupt — save partial response and signal caller
		if response.get('ctrl_d_interrupt'):
			_done = self._parse_ctrl_d(response, opt_skip_history, opt_return_object, color, stream_error)
			if _done is not _PARSE_CONTINUE:
				return _done

		# Early abort from Stream() — skip tool invocation detection
		early_abort = response.get('early_abort')
		if early_abort:
			_done = self._parse_early_abort(response, opt_skip_history, opt_return_object, color, stream_error, early_abort)
			if _done is not _PARSE_CONTINUE:
				return _done

		# Detect repeated responses (model looping)
		# _last_response_hash persists across AI() calls — only reset by new user input in You()
		# Skip check for thinking-only responses (empty content) — they all hash to the same
		# empty-string MD5 and flood false positives.
		if self._detect_repeated_response(response):
			_done = self._parse_repeated(response, opt_return_object, stream_error)
			if _done is not _PARSE_CONTINUE:
				return _done

		#
		# Detect tool invocations before adding assistant response
		# (needs to be first so we can clean XML from assistant content if needed)
		tool_invocations = self._detect_tool_invocations(response)
		
		if tool_invocations and opt_stream_cb:
			for inv in tool_invocations:
				opt_stream_cb({'type':'tool_start','tool':inv['name'],'params':inv.get('parameters',{})})
		
		# Record assistant message in history (strip XML/thinking when needed)
		self._parse_assistant_history(response, tool_invocations, opt_skip_history, color)
		#
		if tool_invocations:
			return self._fire_tool_invocations(tool_invocations, response, opt_stream_cb, stream_error)
		#
		if opt_return_object:
			return {'invocations': tool_invocations, 'response': response['content'], 'stream_error': stream_error }
		return True

	#

	def _parse_stream_error(self, stream_error, response, opt_return_object):
		"""Stream error handling — signal auto-clear for request-too-large errors.
		Returns the caller's return value, or _PARSE_CONTINUE to keep parsing."""
		if not stream_error:
			return _PARSE_CONTINUE
		self.hLG.echo("Stream error: {}".format(stream_error), {'color':True, 'colorValue':'red','debugOnly':False,})
		# Signal auto-clear for request-too-large errors
		err_lower = stream_error.lower()
		if ('too large' in err_lower or '400' in err_lower or '413' in err_lower or 'request body' in err_lower):
			if opt_return_object:
				return {'invocations': [], 'response': response.get('content', ''),
						'stream_error': stream_error, 'stream_too_large': True}
			return True
		return _PARSE_CONTINUE

	#

	def _parse_ctrl_d(self, response, opt_skip_history, opt_return_object, color, stream_error):
		"""Ctrl+D interrupt — save partial response and signal caller."""
		self.Response('assistant', {
			'content': response.get('content', ''),
			'thinking': response.get('thinking', ''),
			'skip_history': opt_skip_history,
			'prompt_tokens': response.get('prompt_tokens', 0),
			'response_tokens': response.get('response_tokens', 0),
		})
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		if opt_return_object:
			return {'invocations': [], 'response': response.get('content', ''),
					'stream_error': stream_error, 'ctrl_d_interrupt': True}
		return True

	#

	def _parse_early_abort(self, response, opt_skip_history, opt_return_object, color, stream_error, early_abort):
		"""Early abort from Stream(). Fire any complete tool invocations already
		present in the partial response (e.g. <GetTip> emitted before a blocked
		<WriteFile>), then surface the blocked-tool alert."""
		# Length-limit aborts get their own warning injection path
		if early_abort in ('think_limit', 'content_limit'):
			return self._parse_limit_abort(response, opt_skip_history, opt_return_object, color, stream_error, early_abort)
		self.hLG.echo("Stream aborted: {}".format(early_abort),
			{'color':True, 'colorValue':'red','debugOnly':False})
		# Extract blocked tool name from early_abort message for user prompt
		plan_blocked = None
		if self.Options.get('MODE') == 'plan':
			m = re.search(r"'(\w+)'", early_abort)
			if m:
				plan_blocked = m.group(1)
		# Detect complete tool invocations in the partial response. The blocked
		# tool itself is truncated (no closing tag) so it is not detected here —
		# only fully-formed calls like <GetTip> are fired, so the model still
		# retrieves its tips before the blocked-tool menu shows.
		tool_invocations = self._detect_tool_invocations(response)
		if tool_invocations:
			self._parse_assistant_history(response, tool_invocations, opt_skip_history, color)
			result = self._fire_tool_invocations(tool_invocations, response, None, stream_error)
			result['plan_blocked'] = result.get('plan_blocked') or plan_blocked
			if opt_return_object:
				return result
			return True
		self.Response('assistant',{
			'content': response.get('content', ''),
			'thinking': response.get('thinking', ''),
			'skip_history': opt_skip_history,
			'prompt_tokens': response.get('prompt_tokens', 0),
			'response_tokens': response.get('response_tokens', 0),
		})
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		if opt_return_object:
			return {'invocations': [], 'response': response.get('content', ''),
					'stream_error': stream_error, 'plan_blocked': plan_blocked}
		return True

	def _parse_limit_abort(self, response, opt_skip_history, opt_return_object, color, stream_error, reason):
		"""Handle think_limit or content_limit aborts: record the partial assistant
		response, then inject a user warning so the model is forced to be concise."""
		if reason == 'think_limit':
			limit = self.Options.get('AI_THINK_LIMIT', 0)
			label = 'thinking/reasoning'
		else:
			limit = self.Options.get('AI_MAX_CONTENT_LEN', 0)
			label = 'response'
		self.hLG.echo("\n[{} output exceeded limit of {} chars — aborting stream]".format(label.capitalize(), limit),
			{'color': True, 'colorValue': 'red', 'debugOnly': False})
		self.Response('assistant', {
			'content': response.get('content', ''),
			'thinking': response.get('thinking', ''),
			'skip_history': opt_skip_history,
			'prompt_tokens': response.get('prompt_tokens', 0),
			'response_tokens': response.get('response_tokens', 0),
		})
		self.hLG.echo("\n", {'end': '', 'flush': True, 'color': color, 'streamDone': True,
						'debugOnly': False, 'echoByNewLine': True, 'speak': True})
		warning = (
			"[System: Your {} output exceeded the {} limit of {} characters. "
			"The stream was aborted. Be concise, avoid long internal reasoning, and proceed with the next action."
		).format(label, 'AI_THINK_LIMIT' if reason == 'think_limit' else 'AI_MAX_CONTENT_LEN', limit)
		self.Response('user', {'content': warning})
		if opt_return_object:
			return {'invocations': [], 'response': response.get('content', ''),
					'stream_error': stream_error, reason: True}
		return True

	#

	def _parse_repeated(self, response, opt_return_object, stream_error):
		"""Model repeated itself — auto-cancelled, skip tool invocation detection."""
		current_content = response.get('content', '').strip()
		if opt_return_object:
			return {'invocations': [], 'response': current_content, 'stream_error': stream_error }
		return True

	#

	def _parse_assistant_history(self, response, tool_invocations, opt_skip_history, color):
		"""Record the assistant message in history.
		Clean assistant content: strip XML tags when using system-role results
		so the model doesn't see stale tool calls in its own history. Strip
		thinking from history when tool calls were made — the reasoning
		describes planned actions and confuses the model into re-issuing them."""
		assistant_content = response['content']
		if tool_invocations and (self.Options.get('TOOL_RESULT_AS_SYSTEM', False) or self.Options.get('TOOL_RESULT_AS_USER', False)):
			assistant_content = self.hTP.ExtractToolResult(response['content'])
		thinking_for_history = response['thinking'] if not tool_invocations else ''
		self.Response('assistant',{
			'content':assistant_content,
			'thinking':thinking_for_history,
			'skip_history':opt_skip_history,
			'prompt_tokens':response.get('prompt_tokens', 0),
			'response_tokens':response.get('response_tokens', 0),
		})
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		# AI_PLANBUILD_AUTOCLEAN: turns that fire planDone/startBuild/nextTask
		# register a fresh task anchor in _fire_tool_invocations. A nextTask
		# turn arms the wait counter (a task just completed); planDone/startBuild
		# turns disarm it (no cleaning on the planning phase).
		if any(inv.get('name') in ('planDone', 'startBuild') for inv in (tool_invocations or [])):
			self._pb_clean_counter = 0
			self._pb_clean_pending = False
			if self.Options.get('AI_PLANBUILD_AUTOCLEAN', 0):
				fired = ', '.join(inv.get('name') or '' for inv in (tool_invocations or []) if inv.get('name') in ('planDone', 'startBuild'))
				self._pb_log("AUTOCLEAN: {} fired — clean disarmed (pending=False)".format(fired))
		elif any(inv.get('name') == 'nextTask' for inv in (tool_invocations or [])):
			self._pb_clean_counter = 0
			self._pb_clean_pending = True
			if self.Options.get('AI_PLANBUILD_AUTOCLEAN', 0):
				self._pb_log("AUTOCLEAN: nextTask fired — clean armed (pending=True, counter=0)")
		else:
			self._pb_after_assistant()

	#

	def _pb_after_assistant(self):
		"""AI_PLANBUILD_AUTOCLEAN: count each recorded assistant response after a
		'<nextTask>' transition (armed by _parse_assistant_history); once
		AI_PLANBUILD_WAIT responses have accumulated, prune the just-completed
		task's work from the model context via _pb_autoclean(). Cleaning only
		happens in build mode after a nextTask — never on planDone/startBuild."""
		if not self.Options.get('AI_PLANBUILD_AUTOCLEAN', 0):
			return
		if self.Options.get('AI_FREEZE_HISTORY', 0):
			return
		if self.Options.get('MODE', 'plan') != 'build':
			return
		if not getattr(self, '_pb_clean_pending', False):
			return
		msgs = getattr(getattr(self, 'hHM', None), 'msgs', None)
		if not msgs:
			return
		# Stop cleaning once the plan is fully completed (after jobDone)
		try:
			from src.PlanManager import PlanBase
			draft = getattr(PlanBase, 'draft', None)
			if draft is not None and draft.tasks and all(t.status == 'completed' for t in draft.tasks.values()):
				return
		except Exception:
			pass
		if len(self._pb_anchor_indices(msgs)) < 2:
			return
		wait = int(self.Options.get('AI_PLANBUILD_WAIT', 5) or 1)
		wait = max(wait, 1)
		self._pb_clean_counter = getattr(self, '_pb_clean_counter', 0) + 1
		self._pb_log("AUTOCLEAN: assistant response {} after nextTask (wait={})".format(
			self._pb_clean_counter, wait))
		if self._pb_clean_counter >= wait:
			self._pb_clean_counter = 0
			did_clean = self._pb_autoclean()
			self._pb_log("AUTOCLEAN: reached wait={} — clean fired, pruned={}".format(wait, did_clean))

	#

	def _strip_think_tags(self, response):
		"""Strip <think>...</think> from content — the model may include these
		in its content field (separate from native thinking API).  Stripping
		early prevents spurious tool detection, hash mismatches, and history
		pollution.  Handles case variants, tags with attributes, orphan
		closers, and unclosed blocks at the end of the content."""
		content = response.get('content', '')
		# Complete blocks (case-insensitive, optional attributes)
		content = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', content, flags=re.I | re.DOTALL)
		# Orphan closing tags without an opener
		content = re.sub(r'</think\s*>', '', content, flags=re.I)
		# Unclosed opening tag — treat the remainder as thinking
		content = re.sub(r'<think\b[^>]*>.*', '', content, flags=re.I | re.DOTALL)
		response['content'] = content

	#

	def _detect_repeated_response(self, response):
		"""Detect model looping via repeated-response hashing.
		Updates _last_response_hash (persists across AI() calls, reset by new
		user input in You()). Returns True if this response is a repeat.
		Thinking-only responses (empty content) are skipped — they all hash to
		the same empty-string MD5 and would flood false positives."""
		current_content = response.get('content', '').strip()
		if current_content:
			current_hash = hashlib.md5(current_content.encode()).hexdigest()
			if self._last_response_hash is not None and current_hash == self._last_response_hash:
				self.hLG.echo("⚠ Model repeated itself — auto-cancelled", {'color':True, 'colorValue':'red','debugOnly':False,})
				return True
			self._last_response_hash = current_hash
		else:
			# Reset hash on thinking-only — avoids false collisions from empty content
			self._last_response_hash = None
		return False

	#

	def _detect_tool_invocations(self, response):
		"""Detect tool invocations before adding the assistant response
		(needs to be first so we can clean XML from assistant content if
		needed). Native tool calls are merged with any XML invocations in
		the content, deduped by tool name so a tool invoked natively is
		not fired twice from its XML form."""
		tool_invocations = []
		native_tool_calls = response.get('native_tool_calls', [])
		if native_tool_calls:
			self.hLG.echo("Parse() detected {} native Ollama tool call(s)".format(len(native_tool_calls)), {'color':True, 'colorValue':'cyan'})
			tool_invocations = self._convert_native_tool_calls(native_tool_calls)
		xml_invocations = self.hTP.ParseTextToolInvocation( response['content'] )
		if xml_invocations:
			native_names = set(inv['name'] for inv in tool_invocations)
			for inv in xml_invocations:
				if inv['name'] not in native_names:
					tool_invocations.append(inv)
			if tool_invocations:
				self.hLG.echo("Parse() detected {} XML tool invocation(s) merged with native".format(len(xml_invocations)), {'color':True, 'colorValue':'orange'})
		return tool_invocations

	#

	def _fire_tool_invocations(self, tool_invocations, response, opt_stream_cb, stream_error):
		"""Execute detected tool invocations and handle plan/build bookkeeping
		(nextTask / startBuild / planDone). Returns the result dict for the
		tool path."""
		job_done = any(inv['name'] == 'jobDone' for inv in tool_invocations)
		#
		result = self.hTP.FireToolInvocation(tool_invocations)
		#
		if opt_stream_cb:
			result_str = str(result) if result else ""
			for inv in tool_invocations:
				opt_stream_cb({'type':'tool_result','tool':inv['name'],'success':not result_str.startswith('Error:'),'result':result_str[:2000]})
		#
		plan_blocked = getattr(self, '_plan_blocked_tool', None)
		plan_done = any(inv['name'] == 'planDone' for inv in tool_invocations)
		if plan_blocked:
			self._plan_blocked_tool = None
			if plan_done:
				self._plan_done_called = True
			return {'invocations': tool_invocations, 'response': response['content'],
					'job_done': job_done, 'stream_error': stream_error,
					'plan_blocked': plan_blocked, 'plan_done': plan_done}
		# Handle nextTask response in build mode - auto-add next task to history
		if self.Options.get('MODE') == 'build':
			for inv in tool_invocations:
				if inv['name'] == 'nextTask':
					result_str = str(result) if result else ""
					if result_str.startswith("NEXT_TASK:"):
						next_instruction = result_str[10:]
						self.Response('user', {'content': "<nextTask>\n\nYour task:\n{}".format(next_instruction)})
						self._write_current_task()
					elif result_str.startswith("ALL_COMPLETED:"):
						self.hLG.echo("Plan completed! All tasks finished.", {'color':True, 'colorValue':'green'})
					elif result_str.startswith("DONE_WITH_BLOCKED:"):
						self.hLG.echo("Plan has blocked tasks. Consider switching to PLAN mode to resolve.", {'color':True, 'colorValue':'orange'})
				elif inv['name'] == 'startBuild':
					result_str = str(result) if result else ""
					if result_str.startswith("START_BUILD|"):
						parts = result_str.split("|", 2)
						task_info = parts[1]
						instruction = parts[2]
						self.Response('system', {'content': "Mode changed to BUILD. You can now make changes.\n\n{} - {}".format(task_info, instruction)})
						self._write_current_task()
		# Handle planDone in any mode — inject system message and signal completion
		if plan_done:
			result_str = str(result) if result else ""
			if result_str.startswith("PLAN_DONE|"):
				parts = result_str.split("|", 2)
				task_info = parts[1]
				instruction = parts[2]
				self.Response('system', {'content': "Plan is ready! Starting first task.\n\n{} - {}".format(task_info, instruction)})
				self._write_current_task()
			else:
				# planDone was called but refused (e.g., build already started).
				# Don't signal plan completion to the AI loop so it doesn't exit
				# and doesn't trigger another StartBuild/duplicate anchors.
				plan_done = False
		#
		# Return the original response so caller knows tools were executed
		return {'invocations': tool_invocations, 'response': response['content'],
				'job_done': job_done, 'stream_error': stream_error,
				'plan_done': plan_done}
