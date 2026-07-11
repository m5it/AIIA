import json, sys, time, os, copy, threading, hashlib, re
from datetime import date
from ollama import ChatResponse, Client, chat
from src.functions import *
from src.ToolChooser import ToolChooser
from src.HistoryManager import HistoryManager
from src.Log import Log
from src.PlanManager import PlanBase, Plan, PlanTask
from src.PlanSaver import PlanSaver
from src.PathApprover import PathApprover
#
class Handle():
	#
	def __init__(self, Options):
		#
		self.opt_response_with = None # (optional) Defined function/method that is fired instead of print(...)
		self.opt_response_done = None # (optional) To know that response is finished and can be used as print(..) as well
		#
		self.Options  = Options
		# Normalize working_dir — if same as framework path, treat as None
		# so PLAN.md / HISTORY.md don't get saved in the framework directory
		framework_dir = self.Options.get('path', '').rstrip('/')
		wd = self.Options.get('working_dir')
		if wd and wd == framework_dir:
			self.Options['working_dir'] = None
		# Defensive fallback: if working_dir is still None and CWD differs
		# from framework_dir, set it to CWD. Catches edge cases where
		# run.py's setup didn't set it (malformed aiia.json, stale Options
		# on !UPDATE HANDLE / !NEW SESSION, override files, etc.).
		if not self.Options.get('working_dir'):
			_cwd = os.getcwd()
			if _cwd != framework_dir:
				self.Options['working_dir'] = _cwd
		#
		#self.cmds    = self.Commands(self)
		self.cmds    = initmodule(importmodule("Commands",True,{'path':'src'}),"Commands",{'handle':self,})
		#
		self.hLG     = initmodule(importmodule("Log",True,{'path':'src'}),"Log",{'handle':self,'debug':self.Options['DEBUG']})
		self.hTC     = initmodule(importmodule("ToolChooser",True,{'path':'src'}),"ToolChooser",{'handle':self,})
		self.hTP     = initmodule(importmodule("ToolParser",True,{'path':'src'}),"ToolParser",{'logger':None,'handle':self,})
		self.hPP     = initmodule(importmodule("Prepare",True,{'path':'src'}),"Prepare",{'handle':self,})
		self.hHM     = initmodule(importmodule("HistoryManager",True,{'path':'src'}),"HistoryManager",{'handle':self,'quiet':self.Options['QUIET'],'path':self.Options['path']})
		self.hIM     = initmodule(importmodule("InstructManager",True,{'path':'src'}),"InstructManager",{'handle':self,})
		self.hTM     = initmodule(importmodule("TipManager",True,{'path':'src'}),"TipManager",{'handle':self,})
		# Add tools directory to sys.path for dynamic tool loading
		tools_path = self.Options.get('tools_path', '')
		if tools_path and tools_path not in sys.path:
			sys.path.append(tools_path.rstrip('/'))
		
		# Initialize path approver for project sandboxing
		self.hPA = PathApprover(working_dir=self.Options.get('working_dir'))
		self.Options['path_approver'] = self.hPA
		
		self.hPM     = PlanBase
		self.tool_iteration = 0
		self.tool_errors                = 0
		self._last_failed_tool          = None
		self._last_failed_tool_count    = 0
		self._last_ai_had_tools        = False
		self._iterations_since_nextTask = 0
		self._consumed_tips = set()
		self._last_response_hash = None
		self._direct_tool_results = [] # results from direct user tool calls (no AI)

		# Eager-import _koslenium_server so its module is cached in sys.modules.
		# Without this, the dynamic tool reloader may re-execute it, resetting
		# _server_state and orphaning the background server process.
		import tools._koslenium_server

		# Eager start koslenium server in background (daemon thread, non-blocking)
		self._start_koslenium_server_async()
	
	#
	def Init(self):
		#
		# Per-project state: when working_dir differs from framework,
		# store state.aiia in the project dir for isolated state.
		working_dir = self.Options.get('working_dir')
		framework_dir = self.Options.get('path', '').rstrip('/')
		if working_dir and working_dir != framework_dir:
			fname = os.path.basename(self.Options.get('AI_FILE_STATE', ''))
			self.Options['AI_FILE_STATE'] = "{}/{}".format(working_dir, fname)
		#
		# Compute a stable hash for history filenames
		# so different projects never collide in the shared root history dir.
		hp = "{}/history".format(self.Options.get('path', ''))
		self.Options['AI_SESS_PREFIX'] = crc32b(os.path.abspath(hp))[:8]
		# Per-project background.log
		_project_dir = working_dir if working_dir and working_dir != framework_dir else framework_dir
		self.Options['BACKGROUND_LOG'] = "{}/background.log".format(_project_dir)
		#
		self.hPP.GetSessionId()
		self.hPP.UpdateFileNames()
		#
		self.Options['handle_tools']  = {}
		self.Options['current_tools'] = []
		self.Options['AI_ROW_ID']     = 0
		self._consumed_tips = set()
		
		# Clear caches on fresh session (not continue)
		if not self.Options.get('CONTINUE'):
			self.hTM.clear_all_caches()
		
		# Handle -c / --continue flag
		if self.Options.get('CONTINUE'):
			self._load_continue_session()
		self.bg_log("Session started, sess_id={}, mode={}, model={}".format(
			self.Options.get('AI_SESS_ID', '?'),
			self.Options.get('MODE', '?'),
			self.Options.get('AI_MODEL', '?')))
	
	#
	def _start_koslenium_server_async(self):
		"""Eager-start the koslenium server in a background daemon thread."""
		def _start():
			try:
				from tools._koslenium_server import start_background
				start_background(browser=False, wait=True)
			except Exception as e:
				self.hLG.echo("koslenium server background start: {}".format(e), {'color':True, 'colorValue':'yellow'})
		t = threading.Thread(target=_start, daemon=True)
		t.start()
		self.bg_log("Koslenium server thread started")
	#
	def _load_continue_session(self):
		working_dir = self.Options.get('working_dir')
		framework_dir = self.Options.get('path', '').rstrip('/')
		
		if not working_dir or working_dir == framework_dir:
			working_dir = None

		# Load all persisted state from state.aiia
		state = self._read_state()

		# Restore MODE
		saved_mode = state.get('mode', '')
		if saved_mode in ('plan', 'build'):
			self.Options['MODE'] = saved_mode
			self.hLG.echo("Restored MODE: {}".format(saved_mode),
				{'color': True, 'colorValue': 'green'})

		# Restore persona
		saved_persona = state.get('persona', '')
		if saved_persona:
			self.Options['INSTRUCT_CLASS'] = saved_persona
			self.Options['INSTRUCT_CLASS_OVERRIDE'] = True
			self.hLG.echo("Restored persona: {}".format(saved_persona),
				{'color': True, 'colorValue': 'green'})

		# Restore model
		saved_model = state.get('model', '')
		if saved_model:
			old = self.Options.get('AI_MODEL', '')
			self.Options['AI_MODEL'] = saved_model
			if saved_model != old:
				self.hLG.echo("Restored model: {}".format(saved_model),
					{'color': True, 'colorValue': 'green'})
				from src.ModelRegistry import apply as apply_registry
				_changes = apply_registry(self.Options, saved_model)
				if _changes:
					for _c in _changes:
						self.hLG.echo("  Model config: {}".format(_c),
							{'color': True, 'colorValue': 'cyan'})

		# Restore used models list
		used_models = state.get('used_models', [])
		current = self.Options.get('AI_MODEL', '')
		if current and current not in used_models:
			used_models.append(current)
			self._write_state({'used_models': used_models})
		self.Options['used_models'] = used_models

		# Load plan from PLAN.md
		plan_data = PlanSaver.load_plan(working_dir, framework_dir)
		if plan_data and plan_data.get('id'):
			# Load the plan from JSON
			loaded_plan = Plan.load(plan_data['id'], self.Options.get('plans_path', 'plans'))
			if loaded_plan:
				PlanBase.draft = loaded_plan
				PlanBase.LoadAll(self.Options.get('plans_path', 'plans'))
				self.hLG.echo("Loaded plan: {} ({} tasks)".format(loaded_plan.title, len(loaded_plan.tasks)), {'color':True, 'colorValue':'green'})
		# Load history from HISTORY.md
		if working_dir is not None:
			history_md = os.path.join(working_dir, 'HISTORY.md')
			if os.path.exists(history_md):
				self.hHM.Get(path=history_md)
				self.Options['CONTINUING'] = True
				self.Options['AI_FILE_LOAD_HISTORY'] = True
				self.hLG.echo("Loaded session history from {}".format(history_md), {'color':True, 'colorValue':'green'})
				# Sync AI_ROW_ID to last loaded row + 1
				if self.hHM.msgs:
					last_row = max((m.get('rowId', 0) for m in self.hHM.msgs), default=0)
					self.Options['AI_ROW_ID'] = last_row + 1
				# Recalculate token counts from loaded history
				total_prompt = total_response = 0
				last_prompt = last_response = 0
				for m in self.hHM.msgs:
					if m.get('role') == 'assistant':
						pt = m.get('prompt_tokens', 0)
						rt = m.get('response_tokens', 0)
						total_prompt += pt
						total_response += rt
						if pt or rt:
							last_prompt = pt
							last_response = rt
				self.Options['NUM_PROMPT_TOKENS'] = total_prompt
				self.Options['NUM_RESPONSE_TOKENS'] = total_response
				self.Options['NUM_LAST_PROMPT_TOKENS'] = last_prompt
				self.Options['NUM_LAST_RESPONSE_TOKENS'] = last_response
			# Fallback: if per-message scan found nothing, load from state
			if total_prompt == 0 and total_response == 0:
				state = self._read_state()
				for key in ('NUM_PROMPT_TOKENS', 'NUM_RESPONSE_TOKENS',
							'NUM_LAST_PROMPT_TOKENS', 'NUM_LAST_RESPONSE_TOKENS'):
					if key in state:
						self.Options[key] = state[key]
				
				# Check if loaded system messages match current mode instructions.
				# If mode changed (different persona or plan↔build), inject fresh
				# instructions so the model gets the correct behavior.
				current_mode = self.Options.get('MODE', 'plan')
				current_text = self.hPP._get_mode_instructions(current_mode)
				header = current_text.strip()[:80]
				mode_matches = any(
					header in m.get('content', '')
					for m in self.hHM.msgs if m.get('role') == 'system'
				)
				if not mode_matches:
					self.hLG.echo(
						"Mode mismatch detected — injecting fresh {} persona instructions".format(current_mode),
						{'color': True, 'colorValue': 'yellow'})
					self.Response('system', {'content': current_text})
	
	#
	def Response(self,role='user',opts=None):
		if opts is None:
			opts = {}
		#
		opt_content       = opts.get('content', '')
		opt_thinking      = opts.get('thinking')
		opt_name          = opts.get('name')
		opt_parse         = opts.get('parse', False)
		opt_return_object = opts.get('return_object', False)
		opt_log_options   = opts.get('log_options', {'color':True})
		opt_skip_history  = opts.get('skip_history', False)
		opt_images        = opts.get('images')

		# Print response
		# Generate response object
		obj = {
			'role'     :role,
			'content'  :opt_content,
			#
			'sessionId':self.Options['AI_SESS_ID'],
			'rowId'    :self.Options['AI_ROW_ID'],
			'timestamp':time.time(),
			'date'     :"{}".format(date.today()),
		}
		# append thinking
		if opt_thinking != None:
			obj['thinking'] = opt_thinking
		#
		if opt_name != None:
			obj["name"] = opt_name

		# Append images (base64 strings for vision models)
		if opt_images and self.Options.get('AI_VISION_ENABLED', True):
			obj['images'] = opt_images

		# Embed token counts in the message (before writing to disk)
		if role == 'assistant':
			prompt_tokens = opts.get('prompt_tokens', 0)
			response_tokens = opts.get('response_tokens', 0)
			obj['prompt_tokens'] = prompt_tokens
			obj['response_tokens'] = response_tokens
			self.Options['NUM_LAST_PROMPT_TOKENS'] = prompt_tokens
			self.Options['NUM_LAST_RESPONSE_TOKENS'] = response_tokens
			self.Options['NUM_PROMPT_TOKENS'] = self.Options.get('NUM_PROMPT_TOKENS', 0) + prompt_tokens
			self.Options['NUM_RESPONSE_TOKENS'] = self.Options.get('NUM_RESPONSE_TOKENS', 0) + response_tokens
			self._write_state({
				'NUM_PROMPT_TOKENS': self.Options['NUM_PROMPT_TOKENS'],
				'NUM_RESPONSE_TOKENS': self.Options['NUM_RESPONSE_TOKENS'],
				'NUM_LAST_PROMPT_TOKENS': self.Options['NUM_LAST_PROMPT_TOKENS'],
				'NUM_LAST_RESPONSE_TOKENS': self.Options['NUM_LAST_RESPONSE_TOKENS'],
			})
			self.bg_log("AI response: {} prompt + {} response tokens (total: {} / {})".format(
				prompt_tokens, response_tokens,
				self.Options['NUM_PROMPT_TOKENS'], self.Options['NUM_RESPONSE_TOKENS']))

		#
		if opt_return_object:
			return obj
		
		# Write history here. (similar to save memory just here we save all chat history)
		# Used messages are saved with SaveMemory()
		if opt_skip_history==False:
			history_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
			fwrite(history_path,"{}\n".format(json.dumps(obj)),False)
		
		# Save to HISTORY.md (working dir only)
		working_dir = self.Options.get('working_dir')
		PlanSaver.save_history(obj, working_dir)
		
		# Append to chat history. (All data of session)
		self.hHM.msgs.append( obj )
		return True
	
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
	def Chat(self):
		self.hLG.echo("Handle.Chat() STARTING! MODE: {}".format(self.Options.get('MODE', 'build')),{'color':True})
		#
		# Load all existing plans on start
		from src.PlanManager import PlanBase
		PlanBase.LoadAll(self.Options.get('plans_path', 'plans'))
		#
		# Tool training: on fresh sessions, let the AI demonstrate tool usage once
		if (self.Options.get('TOOL_TRAINING', True) and
			not self.Options.get('CONTINUE', False) and
			len(self.hHM.msgs) <= 2):
			self.hLG.echo("Tool training — warming up model on available tools...",
				{'color':True, 'colorValue':'cyan','debugOnly':False})
			self.Response('user', {'content':
				"[Tool Training Session]\n"
				"List all tools you have available and demonstrate at least 3 of them "
				"with complete XML examples showing the required parameters."})
			self.AI()
			self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1
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

			# Blocked tool in plan mode — prompt user
			if getattr(self, '_plan_blocked_tool_alert', None):
				tool_name = self._plan_blocked_tool_alert
				del self._plan_blocked_tool_alert
				self.hLG.echo("Model tried to use '{}' in PLAN mode.".format(tool_name),
					{'color':True, 'colorValue':'yellow','debugOnly':False})
				self.hLG.echo("  1. Switch to BUILD mode (allow the tool)",
					{'color':True, 'colorValue':'yellow','debugOnly':False})
				self.hLG.echo("  2. Stay in PLAN mode (block the tool, continue planning)",
					{'color':True, 'colorValue':'yellow','debugOnly':False})
				self.hLG.echo("  3. Cancel AI (return to user prompt)",
					{'color':True, 'colorValue':'yellow','debugOnly':False})
				self.hLG.echo("  4. Continue (dismiss, let the model proceed)",
					{'color':True, 'colorValue':'yellow','debugOnly':False})
				self.hLG.echo("Choice (1-4): ", {'end':'','flush':True,'color':True,'colorValue':'yellow','debugOnly':False})
				ans = user_input({'quit_with_ctrlx':True}).strip()
				ans = re.sub(r'[^0-9]', '', ans)
				if ans == '1':
					self.Options['MODE'] = 'build'
					if self.hHM.msgs and self.hHM.msgs[-1]['role'] == 'system':
						self.hHM.msgs[-1]['content'] = self.hPP._get_mode_instructions('build')
					self.StartBuild()
					_skip_you = True
					continue
				if ans == '3':
					self.Response('user', {'content': "AI loop cancelled. Write tools remain blocked in PLAN mode."})
					_skip_you = False
					continue
				if ans == '4':
					_skip_you = True
					continue
				# Default: option 2 or invalid — stay in plan mode
				self.Response('user', {'content': "Understood. Staying in PLAN mode — write tools remain blocked."})
				_skip_you = True
				continue

			# Auto-re-enter AI() when plan tasks remain and ALL_TASKS mode is on
			if self.Options.get('AUTO_CONTINUE_ALL_TASKS', True):
				mode = self.Options.get('MODE', 'plan')
				should_reenter = False
				if mode == 'build' and self.Options.get('AUTO_CONTINUE_TASKS', True):
					if PlanBase.draft:
						has_remaining = any(
							t.status in ('pending', 'in_progress')
							for t in PlanBase.draft.tasks.values())
						if has_remaining:
							should_reenter = True
				elif mode == 'plan' and self._last_ai_had_tools:
					if not self._is_plan_complete():
						should_reenter = True
				if should_reenter:
					_auto_continue_count += 1
					if _auto_continue_count >= 50:
						self.hLG.echo(
							"Auto-continue: reached 50 rounds — stopping.",
							{'color':True, 'colorValue':'orange','debugOnly':False})
					elif mode == 'plan':
						self.hLG.echo(
							"Auto-continue: AI round {}/50 — continuing plan creation".format(_auto_continue_count),
							{'color':True, 'colorValue':'cyan','debugOnly':False})
						self.Response('user', {'content': 'Continue creating plan tasks.'})
						_skip_you = True
						continue
					else:
						total = len(PlanBase.draft.tasks)
						completed = sum(1 for t in PlanBase.draft.tasks.values() if t.status == 'completed')
						current_task = next((t for t in PlanBase.draft.tasks.values() if t.status == 'in_progress'), None)
						task_num = completed + 1
						task_inst = current_task.instruction if current_task else '(waiting)'
						task_label = task_inst[:60] + '...' if len(task_inst) > 60 else task_inst
						self.hLG.echo(
							"Auto-continue: AI round {}/50 — task {}/{}: {}".format(
								_auto_continue_count, task_num, total, task_label),
							{'color':True, 'colorValue':'green','debugOnly':False})
						self.Response('user', {'content': 'Continue task {}/{}...\n{}'.format(task_num, total, task_inst)})
						_skip_you = True
						continue
	
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
		if 'error' in response:
			stream_error = response['error']
			if stream_error:
				self.hLG.echo("Stream error: {}".format(stream_error), {'color':True, 'colorValue':'red','debugOnly':False,})
				# Signal auto-clear for request-too-large errors
				err_lower = stream_error.lower()
				if ('too large' in err_lower or '400' in err_lower or '413' in err_lower or 'request body' in err_lower):
					if opt_return_object:
						return {'invocations': [], 'response': response.get('content', ''),
								'stream_error': stream_error, 'stream_too_large': True}
					return True

		# Early abort from Stream() — skip tool invocation detection
		early_abort = response.get('early_abort')
		if early_abort:
			self.hLG.echo("Stream aborted: {}".format(early_abort),
				{'color':True, 'colorValue':'red','debugOnly':False})
			self.Response('assistant',{
				'content': response.get('content', ''),
				'thinking': response.get('thinking', ''),
				'skip_history': opt_skip_history,
				'prompt_tokens': response.get('prompt_tokens', 0),
				'response_tokens': response.get('response_tokens', 0),
			})
			self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
			# Extract blocked tool name from early_abort message for user prompt
			plan_blocked = None
			if self.Options.get('MODE') == 'plan':
				m = re.search(r"'(\w+)'", early_abort)
				if m:
					plan_blocked = m.group(1)
			if opt_return_object:
				return {'invocations': [], 'response': response.get('content', ''),
						'stream_error': stream_error, 'plan_blocked': plan_blocked}
			return True

		# Strip <think>...</think> from content — the model may include these
		# in its content field (separate from native thinking API).  Stripping
		# early prevents spurious tool detection, hash mismatches, and history
		# pollution.
		response['content'] = re.sub(r'<think>.*?</think>', '', response.get('content', ''), flags=re.DOTALL)
		response['content'] = re.sub(r'</think>', '', response.get('content', ''))
		
		# Detect repeated responses (model looping)
		# _last_response_hash persists across AI() calls — only reset by new user input in You()
		# Skip check for thinking-only responses (empty content) — they all hash to the same
		# empty-string MD5 and flood false positives.
		current_content = response.get('content', '').strip()
		if current_content:
			current_hash = hashlib.md5(current_content.encode()).hexdigest()
			if self._last_response_hash is not None and current_hash == self._last_response_hash:
				self.hLG.echo("⚠ Model repeated itself — auto-cancelled", {'color':True, 'colorValue':'red','debugOnly':False,})
				if opt_return_object:
					return {'invocations': [], 'response': current_content, 'stream_error': stream_error }
				return True
			self._last_response_hash = current_hash
		else:
			# Reset hash on thinking-only — avoids false collisions from empty content
			self._last_response_hash = None

		#
		# Detect tool invocations before adding assistant response
		# (needs to be first so we can clean XML from assistant content if needed)
		tool_invocations = []
		native_tool_calls = response.get('native_tool_calls', [])
		
		if native_tool_calls:
			self.hLG.echo("Parse() detected {} native Ollama tool call(s)".format(len(native_tool_calls)), {'color':True, 'colorValue':'cyan'})
			tool_invocations = self._convert_native_tool_calls(native_tool_calls)
		
		if not tool_invocations:
			tool_invocations = self.hTP.ParseTextToolInvocation( response['content'] )
			if tool_invocations:
				self.hLG.echo("Parse() detected {} XML tool invocation(s)".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
		
		if tool_invocations and opt_stream_cb:
			for inv in tool_invocations:
				opt_stream_cb({'type':'tool','name':inv['name'],'params':inv.get('parameters',{})})
		
		# Clean assistant content: strip XML tags when using system-role results
		# so the model doesn't see stale tool calls in its own history
		assistant_content = response['content']
		if tool_invocations and (self.Options.get('TOOL_RESULT_AS_SYSTEM', False) or self.Options.get('TOOL_RESULT_AS_USER', False)):
			assistant_content = self.hTP.ExtractToolResult(response['content'])
		#
		# Strip thinking from history when tool calls were made —
		# the reasoning describes planned actions and confuses the
		# model into re-issuing them on the next iteration.
		thinking_for_history = response['thinking'] if not tool_invocations else ''
		self.Response('assistant',{
			'content':assistant_content,
			'thinking':thinking_for_history,
			'skip_history':opt_skip_history,
			'prompt_tokens':response.get('prompt_tokens', 0),
			'response_tokens':response.get('response_tokens', 0),
		})
		#
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		#
		if tool_invocations:
			#
			job_done = any(inv['name'] == 'jobDone' for inv in tool_invocations)
			#
			result = self.hTP.FireToolInvocation(tool_invocations)
			#
			plan_blocked = getattr(self, '_plan_blocked_tool', None)
			if plan_blocked:
				self._plan_blocked_tool = None
				return {'invocations': tool_invocations, 'response': response['content'],
						'job_done': job_done, 'stream_error': stream_error,
						'plan_blocked': plan_blocked}
			# Handle nextTask response in build mode - auto-add next task to history
			if self.Options.get('MODE') == 'build':
				for inv in tool_invocations:
					if inv['name'] == 'nextTask':
						result_str = str(result) if result else ""
						if result_str.startswith("NEXT_TASK:"):
							next_instruction = result_str[10:]
							self.Response('user', {'content': "<nextTask>\n\nYour task:\n{}".format(next_instruction)})
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
							self.Response('user', {'content': "Mode changed to BUILD. You can now make changes.\n\n{} - {}".format(task_info, instruction)})
			# Handle planDone in any mode — inject user message and signal completion
			plan_done = any(inv['name'] == 'planDone' for inv in tool_invocations)
			if plan_done:
				result_str = str(result) if result else ""
				if result_str.startswith("PLAN_DONE|"):
					parts = result_str.split("|", 2)
					task_info = parts[1]
					instruction = parts[2]
					self.Response('user', {'content': "Plan is ready! Starting first task.\n\n{} - {}".format(task_info, instruction)})
			#
			# Return the original response so caller knows tools were executed
			return {'invocations': tool_invocations, 'response': response['content'],
					'job_done': job_done, 'stream_error': stream_error,
					'plan_done': plan_done}
		#
		if opt_return_object:
			return {'invocations': tool_invocations, 'response': response['content'], 'stream_error': stream_error }
		return True
	
	#
	def _convert_native_tool_calls(self, native_tool_calls):
		"""
		Convert native Ollama tool calls to internal XML-like tool invocation format
		Native format: tool_calls = [{'function': {'name': 'tool_name', 'arguments': {...}}}]
		Internal format: [{'name': 'ToolName', 'params': {...}}]
		"""
		converted = []
		for tool_call in native_tool_calls:
			try:
				# Extract function info from native tool call
				if hasattr(tool_call, 'function'):
					func = tool_call.function
					tool_name = func.name if hasattr(func, 'name') else str(func.get('name', ''))
					
					# Get arguments - might be dict or JSON string
					args = {}
					if hasattr(func, 'arguments'):
						args = func.arguments if isinstance(func.arguments, dict) else json.loads(func.arguments)
					
					# Convert to internal format (ToolParser expects 'parameters')
					converted.append({
						'name': tool_name,
						'parameters': args
					})
					self.hLG.echo("Converted native tool call: {} with params: {}".format(tool_name, args), {'color':True, 'colorValue':'cyan'})
				elif isinstance(tool_call, dict):
					# Handle dict format
					func = tool_call.get('function', {})
					tool_name = func.get('name', '')
					args = func.get('arguments', {})
					if isinstance(args, str):
						args = json.loads(args)
					
					converted.append({
						'name': tool_name,
						'parameters': args
					})
					self.hLG.echo("Converted native tool call (dict): {} with params: {}".format(tool_name, args), {'color':True, 'colorValue':'cyan'})
			except Exception as e:
				self.hLG.echo("Error converting native tool call: {}".format(str(e)), {'color':True, 'colorValue':'red','debugOnly':False,})
				continue
		
		return converted
	
	#
	def Stream(self, res, color, stream_callback=None):
		response         = "" # speaking data
		thinking         = "" # thinking data
		native_tool_calls = []  # native Ollama tool calls
		if_thinking      = False
		if_speaking      = False
		last_chunk       = None
		abort_reason     = None
		#
		try:
			for chunk in res:
				last_chunk = chunk
				# thinking
				if chunk.message.thinking:
					#
					if not if_thinking:
						if_thinking = True
						if not self.Options.get('BUILD_THINKING_DISABLED', False):
							print('Thinking:\n', end='')
					#
					part = chunk.message.thinking
					thinking += part
					if not self.Options.get('BUILD_THINKING_DISABLED', False):
						print(part, end='', flush=True)
				# Check for native tool calls
				elif hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
					# Collect native Ollama tool calls
					for tool_call in chunk.message.tool_calls:
						if tool_call not in native_tool_calls:
							native_tool_calls.append(tool_call)
					# Don't print tool calls, just collect them
				# speaking
				elif chunk.message.content:
					#
					if not if_speaking:
						print('\n\nAnswer:\n', end='')
						if_thinking = False
						if_speaking = True
					#
					part = chunk.message.content
					response += part
					# Early abort: detect misguided tool calls mid-stream
					abort_reason = self._check_stream_abort(response)
					if abort_reason:
						self.hLG.echo("\n[Aborted: {}]".format(abort_reason),
							{'color':True, 'colorValue':'red','debugOnly':False})
						if stream_callback:
							stream_callback({'type':'abort','reason':abort_reason})
						break
					if stream_callback:
						stream_callback({'type':'token','text':part})
					self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True,'speak':True})
			# Extract token counts from final chunk (done=True)
			prompt_tokens = 0
			response_tokens = 0
			if last_chunk and hasattr(last_chunk, 'done') and last_chunk.done:
				prompt_tokens = last_chunk.prompt_eval_count or 0
				response_tokens = last_chunk.eval_count or 0
		except Exception as e:
			self.hLG.echo("Stream error: {}".format(str(e)), {'color':True, 'colorValue':'red','debugOnly':False,})
			return {'content':response, 'thinking':thinking, 'native_tool_calls':native_tool_calls, 'prompt_tokens':0, 'response_tokens':0, 'error':str(e), 'early_abort':abort_reason}
		return {'content':response, 'thinking':thinking, 'native_tool_calls':native_tool_calls, 'prompt_tokens':prompt_tokens, 'response_tokens':response_tokens, 'early_abort':abort_reason}

	def _check_stream_abort(self, partial_response):
		"""Check if the partial response contains a tool invocation that should
		be aborted early. Returns a reason string or None."""
		mode = self.Options.get('MODE', '')

		# In PLAN mode, abort on opening tag of blocked execution tools
		if mode == 'plan':
			for m in re.finditer(r'<(\w+)[\s>]', partial_response):
				name = m.group(1)
				if name in self.hTP._plan_blocked:
					return "'{}' cannot be used in PLAN mode".format(name)

		return None

	#
	def _is_plan_complete(self):
		"""Check if the model has signaled plan completion in its last response.
		Scans last assistant message for text patterns and planDone tool calls."""
		# Scan history in reverse for the most recent assistant message
		for msg in reversed(self.hHM.msgs):
			if msg.get('role') != 'assistant':
				continue
			content = msg.get('content', '')
			if not content.strip():
				continue
			# Text patterns indicating plan completion
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
					return True
			# No patterns matched — stop scanning
			break
		# Check if planDone tool was called recently (look for plan_done flag)
		if getattr(self, '_plan_done_called', False):
			return True
		return False

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
				inp = user_input({'quit_with_ctrlx':True})
			except Exception as E:
				sys.exit(1)
		
		# Handle user commands
		if rmatch(inp,"^!.*"):
			print("handle debug!!!")
			cmds = self.cmds.cmds
			for k in cmds:
				if rmatch(inp,cmds[k]['regex']):
					print("match command! {}".format( cmds[k]['name'] ))
					return cmds[k]['func'](inp)
			print("no match, repeat..., debug({}): {}".format(len(inp),inp))
			return 2 # as continue
		# Repeat user input. Content too large
		if len(inp)>self.Options['AI_MAX_CONTENT_LEN']:
			print("FAILED: content length too large. ( {} / {} )".format( len(inp), self.Options['AI_MAX_CONTENT_LEN'] ))
			return 2 # as continue / repeat
		
		# Append user content
		if inp != None:
			self._last_response_hash = None
			# Reset consecutive error tracking on new user input
			self.tool_errors = 0
			self._last_failed_tool = None
			self._last_failed_tool_count = 0
			self.Response('user',{'content':inp})
		
		# Handle model tool calls
		tool_invocations = self.hTP.ParseTextToolInvocation(inp)
		
		if tool_invocations:
			self.hLG.echo("Handle.You() detected {} tool invocation(s) in text — executing directly, skipping AI".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self._direct_tool_results = []
			self.hTP.FireToolInvocation(tool_invocations)
			#
			# Collect results from history for SSE / caller use
			for msg in reversed(self.hHM.msgs):
				if msg.get('role') == 'tool' and msg.get('name'):
					self._direct_tool_results.append({
						'name': msg['name'],
						'content': msg.get('content', '')
					})
				if len(self._direct_tool_results) >= len(tool_invocations):
					break
			return 1 # tool was executed — skip AI
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
	#
	# -- context management --------------------------------------------------
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def _estimate_tokens(self, msgs):
		"""Rough token estimate: ~4 chars per token on average, images count as
		their base64 size (~1.37 bytes per char * num chars / 4)."""
		total = 0
		for m in msgs:
			content = m.get('content', '')
			thinking = m.get('thinking', '')
			total += len(content) // 4
			total += len(thinking) // 4
			total += 8  # overhead per message (role label, newlines)
			# Account for base64 images: ~1.37 bytes per base64 char → /4 for tokens
			for img_b64 in m.get('images', []):
				total += len(img_b64) // 3  # rough: 4 base64 chars ≈ 3 bytes ≈ 0.75 tokens
		return total

	def _rewrite_history(self, msgs):
		"""Rewrite the on-disk history files to match in-memory state."""
		main_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)

		framework_dir = self.Options.get('path', '').rstrip('/')
		proj_dir = self.Options.get('working_dir')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, msgs)

	def _archive_history(self, suffix):
		"""Copy current .dbk to an archive file before destructive operations.
		Archive is saved as {prefix}_{sid}.{suffix}.{timestamp}.dbk in the history dir.
		Returns the archive filename (or None if nothing was archived)."""
		main_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
		if not os.path.exists(main_path):
			return None
		try:
			with open(main_path) as f:
				lines = f.readlines()
			# Only archive if there's more than just a few messages
			if len(lines) <= 3:
				return None
		except Exception:
			return None

		ts = int(time.time())
		_prefix = self.Options.get('AI_SESS_PREFIX', '')
		sid = self.Options['AI_SESS_ID']
		archive_name = "{}_{}.{}.{}.dbk".format(_prefix, sid, suffix, ts)
		archive_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), archive_name)
		try:
			fwrite(archive_path, "".join(lines), True)
			self.hLG.echo("Archived history to {}".format(archive_name),
				{'color': True, 'colorValue': 'cyan'})
			return archive_name
		except Exception as e:
			self.hLG.echo("Failed to archive history: {}".format(e),
				{'color': True, 'colorValue': 'red'})
			return None

	def _save_clear_tip(self, archive_name, msg_count):
		"""Save a tip recording that the session was cleared, with archive info."""
		try:
			sid = self.Options['AI_SESS_ID']
			summary = ("Session {} was cleared to free context. "
				"{} messages archived to {}. "
				"Use <GetTip title='session_{}_cleared'> to retrieve this note.".format(
					sid, msg_count, archive_name, sid))
			self.hTM.save("session_{}_cleared".format(sid), "model", [
				{'role': 'system', 'content': "[Session {} archive: {} — {} messages]".format(
					sid, archive_name, msg_count)}
			])
			self.hLG.echo("Saved clear tip: session_{}_cleared".format(sid),
				{'color': True, 'colorValue': 'cyan'})
		except Exception as e:
			self.hLG.echo("Failed to save clear tip: {}".format(e),
				{'color': True, 'colorValue': 'red'})

	def bg_log(self, msg, level="INFO"):
		"""Write a timestamped line to background.log."""
		log_path = self.Options.get('BACKGROUND_LOG')
		if not log_path:
			return
		try:
			import datetime
			ts = datetime.datetime.now().strftime('%H:%M:%S')
			with open(log_path, 'a') as f:
				f.write("[{}] {}: {}\n".format(ts, level, msg))
		except Exception:
			pass

	def _read_state(self):
		"""Load full state dict from state.aiia, with migration from legacy files."""
		path = self.Options.get('AI_FILE_STATE')
		if path and os.path.exists(path):
			try:
				raw = fread(path)
				return json.loads(raw)
			except Exception as e:
				self.hLG.echo("Failed to read state: {} (will migrate)".format(e),
					{'color': True, 'colorValue': 'yellow'})
		# No state.aiia yet — migrate from legacy per-file .aiia files
		migrated = self._migrate_old_state()
		if migrated:
			self._write_state(migrated)
		return migrated

	def _write_state(self, updates=None):
		"""Atomically write state.aiia, merging `updates` into existing state."""
		path = self.Options.get('AI_FILE_STATE')
		if not path:
			return
		state = {}
		if os.path.exists(path):
			try:
				raw = fread(path)
				state = json.loads(raw)
			except Exception:
				pass
		if updates:
			state.update(updates)
		try:
			tmp = path + '.tmp'
			fwrite(tmp, json.dumps(state), True)
			os.replace(tmp, path)
		except Exception as e:
			self.hLG.echo("Failed to write state: {}".format(e),
				{'color': True, 'colorValue': 'red'})

	def _migrate_old_state(self):
		"""Import values from legacy per-file .aiia files into a single dict."""
		fw_dir = self.Options.get('path', '').rstrip('/')
		state = {}
		legacy = [
			('sess_id', '{}/sessid.aiia', lambda r: int(r.strip())),
			('mode', '{}/mode.aiia', lambda r: r.strip() if r.strip() in ('plan','build') else None),
			('model', '{}/model.aiia', lambda r: r.strip() or None),
			('persona', '{}/persona.aiia', lambda r: r.strip() or None),
			('used_models', '{}/used_models.aiia', lambda r: json.loads(r)),
		]
		token_keys = ['NUM_PROMPT_TOKENS', 'NUM_RESPONSE_TOKENS',
					  'NUM_LAST_PROMPT_TOKENS', 'NUM_LAST_RESPONSE_TOKENS']
		found = False
		for key, tmpl, parse in legacy:
			p = tmpl.format(fw_dir)
			if os.path.exists(p):
				try:
					raw = fread(p)
					val = parse(raw)
					if val is not None:
						state[key] = val
						found = True
				except Exception:
					pass
		# Migrate tokens.aiia (JSON file with separate keys)
		tokens_path = '{}/tokens.aiia'.format(fw_dir)
		if os.path.exists(tokens_path):
			try:
				tdata = json.loads(fread(tokens_path))
				for k in token_keys:
					if k in tdata:
						state[k] = tdata[k]
						found = True
			except Exception:
				pass
		if found:
			self.hLG.echo("Migrated legacy .aiia files to state.aiia",
				{'color': True, 'colorValue': 'cyan'})
		return state

	def _save_used_models(self, models):
		"""Persist the used-models list to state.aiia."""
		self._write_state({'used_models': models})

	def _summarize_context(self, msgs, limit, threshold):
		"""Summarize older messages, keeping last 5 exchanges + all system prompts.
		Returns True if summarization was performed."""
		# Strip malformed entries (no `role` key) that slipped into history
		msgs = [m for m in msgs if isinstance(m, dict) and m.get('role')]
		if not msgs:
			return False
		# Collect indices to keep
		keep = set()
		exchange_count = 0
		for i in range(len(msgs) - 1, -1, -1):
			role = msgs[i]['role']
			if role == 'system':
				keep.add(i)
			elif exchange_count < 5 and role in ('user', 'assistant'):
				keep.add(i)
				if role == 'user':
					exchange_count += 1

		idx = sorted(i for i in range(len(msgs)) if i not in keep)
		if not idx:
			return False

		build = []
		for i in idx:
			role = msgs[i]['role']
			content = msgs[i].get('content', '')
			build.append("[{}]: {}".format(role, content[:600]))
		to_summarize = "\n\n".join(build)

		prompt = (
			"Summarize the key facts, decisions, file states, and progress "
			"from this conversation concisely. Focus on:\n"
			"- What has been built or changed\n"
			"- What decisions were made\n"
			"- Current state of files and code\n"
			"- What remains to be done\n\n"
			"Keep the summary under 500 words.\n\n"
			"---\n" + to_summarize
		)

		try:
			res = chat(
				model=self.Options['AI_MODEL'],
				messages=[{'role': 'user', 'content': prompt}],
				options={'num_predict': 1024},
				stream=False,
				think=False,
			)
			summary = res.message.content.strip()
			if len(summary) > 3000:
				summary = summary[:3000] + "…"
		except Exception as e:
			self.hLG.echo("Context summarization failed: {}".format(e),
				{'color': True, 'colorValue': 'red'})
			return False

		new_msgs = [msgs[i] for i in sorted(keep)]
		# Insert summary right after the last system prompt in new_msgs
		last_sys = sum(1 for m in new_msgs if m['role'] == 'system') - 1
		summary_msg = {
			'role': 'system',
			'content': "[Context summary: {}]".format(summary),
			'sessionId': self.Options['AI_SESS_ID'],
			'rowId': self.Options['AI_ROW_ID'] + 1,
			'timestamp': time.time(),
			'date': str(date.today()),
		}
		new_msgs.insert(last_sys + 1, summary_msg)

		# Archive raw history before rewriting
		self._archive_history('summarized')
		self.hHM.msgs = new_msgs
		self._rewrite_history(new_msgs)
		self.hLG.echo(
			"Context summarized: {} messages replaced with summary ({} chars)".format(
				len(idx), len(summary)),
			{'color': True, 'colorValue': 'green'})
		return True

	def _auto_clear(self):
		"""Keep only system messages, clear everything else.  Resets counters."""
		msg_count = len(self.hHM.msgs)
		archive_name = self._archive_history('cleared')
		if archive_name:
			self._save_clear_tip(archive_name, msg_count)
		system_msgs = [m for m in self.hHM.msgs if isinstance(m, dict) and m.get('role') == 'system']
		self.hHM.msgs = system_msgs[:]
		self._rewrite_history(system_msgs)
		self.Options['AI_ROW_ID'] = 0
		self.Options['NUM_PROMPT_TOKENS'] = 0
		self.Options['NUM_RESPONSE_TOKENS'] = 0
		self.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		self.hLG.echo("Context limit reached — auto-cleared chat history",
			{'color': True, 'colorValue': 'orange', 'debugOnly': False})

	def _manage_context(self):
		"""Check estimated token count against limit.  Summarize first, clear as
		fallback.  Called at the start of AI() before any model request."""
		limit = self.Options.get('AI_CONTEXT_LIMIT', 262144)
		threshold = self.Options.get('AI_CLEAR_THRESHOLD', 0.8)
		max_allowed = int(limit * threshold)

		msgs = self.hHM.msgs
		if not msgs:
			return

		estimate = self._estimate_tokens(msgs)
		if estimate <= max_allowed:
			return

		self.hLG.echo(
			"Context estimate {} exceeds limit {} (threshold {}), managing…".format(
				estimate, limit, threshold),
			{'color': True, 'colorValue': 'yellow'})

		if self._summarize_context(msgs, limit, threshold):
			# Re-check after summarization
			if self._estimate_tokens(self.hHM.msgs) <= max_allowed:
				return

		self._auto_clear()

	def _try_auto_continue(self):
		"""If in BUILD mode with pending tasks and auto-continue enabled,
		advance to next task and inject a continuation user message.
		Returns True if a message was injected."""
		if self.Options.get('MODE') != 'build':
			return False
		if not self.Options.get('AUTO_CONTINUE_TASKS', True):
			return False

		from src.PlanManager import PlanBase
		if not PlanBase.draft:
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
		return True

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
		#
		# Loop to handle multiple rounds of tool calls
		max_iterations = self.Options.get('AI_MAX_ITERATIONS', 10)
		iteration = 0
		_tools_were_called = False
		_tools_last_error = False

		while iteration < max_iterations:
			iteration += 1

			# Short-circuit: ≥3 consecutive tool errors → break loop with recovery
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
				continue

			# Re-check context before each model call — tool results may have
			# added large data (e.g., base64 images) since the last check
			self._manage_context()

			result        = ""
			res           = {}
			msgs = copy.deepcopy(self.hHM.msgs)
			# Strip malformed entries (no `role` key) that slipped into history
			msgs = [m for m in msgs if isinstance(m, dict) and m.get('role')]

			# Auto-inject tip availability into last user message
			tip_summary = self._get_tip_summary()
			if tip_summary:
				for i in range(len(msgs) - 1, -1, -1):
					if msgs[i].get('role') == 'user':
						msgs[i]['content'] = msgs[i]['content'] + "\n\n" + tip_summary
						break

			# Nothing to send to AIIA, continue to user input!
			if len(msgs)<=0:
				print("WARNING: msgs len is 0, Repeating user_input!")
				return 2 # as continue
			
			# Chat without tools, normal chat (XML tools handle themselves)
			self.hLG.echo("DEBUG preparing chat (iteration {})".format(iteration),{'color':False})
			
			# Build chat parameters
			chat_params = {
				'model': self.Options['AI_MODEL'],
				'messages': msgs,
				'stream': True,
				'options': self.Options['AI_OPTIONS'],
			}
			
			# Optional: pass think=True for models that support the reasoning
			# API (e.g. DeepSeek R1). Set AI_THINK=true in config to enable.
			if self.Options.get('AI_THINK', False):
				chat_params['think'] = True
			
			# Try the model call with retries
			self.bg_log("AI request (iteration {}, msgs={})".format(
				iteration, len(msgs)))
			model_retries = 0
			max_retries = self.Options.get('AI_MODEL_RETRIES', 3)
			model_timeout = self.Options.get('AI_MODEL_TIMEOUT', 120)
			model_failed = False
			context_cleared = False
			while True:
				try:
					client = Client(timeout=model_timeout if model_timeout else None)
					res: ChatResponse = client.chat(**chat_params)
					result = self.Parse(res,{'return_object':True,'stream_callback':opt_stream_cb})
					break
				except Exception as e:
					err_str = str(e).lower()
					if 'too large' in err_str or '400' in err_str or '413' in err_str or 'request body' in err_str:
						self.hLG.echo("AI request too large — auto-clearing context and retrying...",
							{'color':True, 'colorValue':'orange','debugOnly':False})
						self._auto_clear()
						context_cleared = True
						break
					model_retries += 1
					if model_retries > max_retries:
						model_failed = True
						self.bg_log(
							"Model call failed after {} attempts: {}".format(max_retries, e),
							"ERROR")
						self.hLG.echo(
							"AI model unavailable after {} attempts — guiding model to switch".format(max_retries),
							{'color':True, 'colorValue':'red','debugOnly':False})
						recovery_msg = (
							"[System: The model API call failed {} times consecutively. "
							"This is likely a cloud-model connectivity issue. "
							"Switch to a local model with `!MODEL gemma3:12b` or another available local model.]"
						).format(max_retries)
						self.Response('user', {'content': recovery_msg})
						self.tool_errors = 0
						self._last_failed_tool = None
						self._last_failed_tool_count = 0
						break
					self.bg_log(
						"Model call failed (attempt {}/{}): {}".format(
							model_retries, max_retries, e))
					self.hLG.echo(
						"AI connection error (attempt {}/{}): {} — retrying...".format(
							model_retries, max_retries, str(e)),
						{'color':True, 'colorValue':'red','debugOnly':False})
					time.sleep(1)
			if context_cleared:
				continue
			if model_failed:
				continue
			
			# Used if CTRL+C to save last/draft content to chat history
			self.Options['DRAFT_RESPONSE'] = res

			# Track whether the model made tool calls this turn
			if result.get('invocations'):
				_tools_were_called = True
				_tools_last_error = False
				if self.hHM.msgs and self.hHM.msgs[-1].get('role') == 'tool':
					_tools_last_error = self.hHM.msgs[-1].get('content', '').startswith('Error:')

			# Blocked tool in plan mode — stop and alert user
			if result.get('plan_blocked'):
				self._plan_blocked_tool_alert = result['plan_blocked']
				self._last_ai_had_tools = True
				return True

			# Request body too large — auto-clear context and retry
			if result.get('stream_too_large'):
				self.hLG.echo("Request body too large — auto-clearing context and retrying...",
					{'color':True, 'colorValue':'orange','debugOnly':False})
				self._auto_clear()
				self.Response('user', {
					'content': "[System: The conversation was too large for the model. "
					"Context has been cleared to free memory. Continue with the task.]"
				})
				continue

			# Track planDone tool call — auto-continue should stop after this
			if result.get('plan_done'):
				self._plan_done_called = True

			# Track iterations without <nextTask> and remind model
			if result.get('invocations'):
				has_nextTask = any(inv.get('name') == 'nextTask' for inv in result['invocations'])
				if has_nextTask:
					self._iterations_since_nextTask = 0
				elif _tools_were_called:
					self._iterations_since_nextTask += 1
			elif _tools_were_called and not result.get('job_done'):
				self._iterations_since_nextTask += 1
			remind_after = self.Options.get('AUTO_CONTINUE_REMIND_AFTER', 20)
			if (_tools_were_called and not result.get('job_done') and
				self._iterations_since_nextTask >= remind_after):
				self._iterations_since_nextTask = 0
				self.Response('user', {'content':
					"[System: You've gone {} iterations without calling `<nextTask>completed</nextTask>`. "
					"If the current task is done, call `<nextTask>completed</nextTask>` to advance. "
					"If blocked, call `<nextTask>blocked</nextTask>`.]".format(remind_after)})
				continue

			# Stop if model response is empty (no content, no tools)
			if not result.get('response', '').strip() and not result.get('invocations'):
				self._last_ai_had_tools = _tools_were_called
				return True
			
			# Stop if jobDone was called
			if result.get('job_done'):
				self._last_ai_had_tools = False
				return True
			
			# Check if tools were executed by looking for tool invocations in result
			if not result['invocations']:
				# No more tool calls
				# Auto-continue to next task if model made tool calls and no errors
				if _tools_were_called and not _tools_last_error and self._try_auto_continue():
					_tools_were_called = False
					_tools_last_error = False
					continue
				self._last_ai_had_tools = _tools_were_called
				if opt_return_object:
					return result['response']
				return True
		self._last_ai_had_tools = _tools_were_called
	
	#
	def StartBuild(self, plan_id=None):
		if not PlanBase.draft:
			if plan_id:
				plan = Plan.load(plan_id, self.Options.get('plans_path', 'plans'))
				if plan:
					PlanBase.draft = plan
				else:
					self.hLG.echo("Plan {} not found".format(plan_id), {'color':True, 'colorValue':'red'})
					return
			else:
				self.hLG.echo("No active plan. Use createPlan first.", {'color':True, 'colorValue':'red'})
				return
		first_task = None
		# Don't double-start — if a task is already in_progress, do nothing
		for t in PlanBase.draft.tasks.values():
			if t.status == "in_progress":
				self.hLG.echo("Build already started — task already in progress.", {'color':True, 'colorValue':'yellow'})
				return
		for tid, task in PlanBase.draft.tasks.items():
			if task.status == "pending":
				first_task = task
				task.status = "in_progress"
				task.startTimestamp = time.time()
				break
		if first_task:
			PlanBase.draft.save(self.Options.get('plans_path', 'plans'))
			PlanBase.LogProgress(first_task.id, "Build started", self.Options.get('plans_path', 'plans'))
			task_number = sum(1 for t in PlanBase.draft.tasks.values() if t.status in ["completed", "in_progress"])
			total_tasks = len(PlanBase.draft.tasks)
			self.Response('user', {'content': "Mode changed to BUILD. You can now make changes.\n\nTask {}/{} - {}".format(task_number, total_tasks, first_task.instruction)})
			self.hLG.echo("Started build: Task {}/{}".format(task_number, total_tasks), {'color':True, 'colorValue':'green'})
		else:
			self.hLG.echo("No pending tasks in plan!", {'color':True, 'colorValue':'orange'})
