import json, sys, time, os, threading
from datetime import date
from src.functions import *
from src.ToolChooser import ToolChooser
from src.HistoryManager import HistoryManager
from src.Log import Log
from src.PlanManager import PlanBase
from src.PlanSaver import PlanSaver
from src.PathApprover import PathApprover
from src.TimerManager import TimerManager
from src.HandleStream import HandleStream
from src.HandleParse import HandleParse
from src.HandleContext import HandleContext
from src.HandleState import HandleState
from src.HandleChat import HandleChat
#
class Handle(HandleStream, HandleParse, HandleContext, HandleState, HandleChat):

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
		# LLM backend (ollama / vllm) — lazily resolved on first use
		self.hBackend = None
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

	def _get_backend(self):
		"""Lazily return the LLM backend, re-creating it if AI_BACKEND changed
		(e.g. via !BACKEND or !SET AI_BACKEND at runtime)."""
		from src.LLMBackends import get_backend
		requested = (self.Options.get('AI_BACKEND') or 'ollama').lower()
		if self.hBackend is None or self.hBackend.name != requested:
			self.hBackend = get_backend(self.Options)
		return self.hBackend

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
		self.hTMR = TimerManager(self)
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
		opt_image_refs    = opts.get('image_refs')

		# Print response
		# Generate response object
		obj = self._build_response_obj(role, opt_content, opt_thinking, opt_name, opt_images, opt_image_refs)

		# Embed token counts in the message (before writing to disk)
		if role == 'assistant':
			self._embed_token_counts(obj, opts)

		#
		if opt_return_object:
			return obj
		# Write history here. (similar to save memory just here we save all chat history)
		self._persist_response(obj, opt_skip_history)
		return True

	#

	def _build_response_obj(self, role, opt_content, opt_thinking, opt_name, opt_images, opt_image_refs):
		"""Generate the response message object with session/row/timestamp fields."""
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

		# Lightweight image references (stored in history instead of base64)
		if opt_image_refs and self.Options.get('AI_VISION_ENABLED', True):
			obj['image_refs'] = opt_image_refs
		return obj

	#

	def _embed_token_counts(self, obj, opts):
		"""Embed token counts in an assistant message and update the counters."""
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

	def _persist_response(self, obj, opt_skip_history):
		"""Write history here. (similar to save memory just here we save all chat history)
		Used messages are saved with SaveMemory()"""
		if opt_skip_history==False:
			history_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
			fwrite(history_path,"{}\n".format(json.dumps(obj)),False)
		# Save to HISTORY.md (working dir only)
		working_dir = self.Options.get('working_dir')
		PlanSaver.save_history(obj, working_dir)
		# Append to chat history. (All data of session)
		self.hHM.msgs.append( obj )

	#

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

	#

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
