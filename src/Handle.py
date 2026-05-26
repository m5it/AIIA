import json, sys, time, os, copy
from datetime import date
from ollama import ChatResponse, chat
from src.functions import *
from src.ToolChooser import ToolChooser
from src.HistoryManager import HistoryManager
from src.Log import Log
from src.PlanManager import PlanBase, Plan, PlanTask
from src.PlanSaver import PlanSaver
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
		#
		#self.cmds    = self.Commands(self)
		self.cmds    = initmodule(importmodule("Commands",True,{'path':'src'}),"Commands",{'handle':self,})
		#
		self.hLG     = initmodule(importmodule("Log",True,{'path':'src'}),"Log",{'handle':self,'debug':self.Options['DEBUG']})
		self.hAC     = initmodule(importmodule("Actions",True,{'path':'src'}),"Actions",{'handle':self,})
		self.hTC     = initmodule(importmodule("ToolChooser",True,{'path':'src'}),"ToolChooser",{'handle':self,})
		self.hTP     = initmodule(importmodule("ToolParser",True,{'path':'src'}),"ToolParser",{'logger':None,'handle':self,})
		self.hPP     = initmodule(importmodule("Prepare",True,{'path':'src'}),"Prepare",{'handle':self,})
		self.hHM     = initmodule(importmodule("HistoryManager",True,{'path':'src'}),"HistoryManager",{'handle':self,'quiet':self.Options['QUIET'],'path':self.Options['path']})
		self.hIM     = initmodule(importmodule("InstructManager",True,{'path':'src'}),"InstructManager",{'handle':self,})
		self.hTM     = initmodule(importmodule("TipManager",True,{'path':'src'}),"TipManager",{'handle':self,})
		self.hPM     = PlanBase
		self.tool_iteration = 0
		self.tool_errors    = 0
		self._consumed_tips = set()
	
	#
	def Init(self):
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
	
	#
	def _load_continue_session(self):
		working_dir = self.Options.get('working_dir')
		framework_dir = self.Options.get('path', '').rstrip('/')
		
		if not working_dir or working_dir == framework_dir:
			working_dir = None
		
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
		
		# Print response
		#if role!='user':
		#	#print("{} => {}".format( role, opt_content ))
		#	self.hLG.echo("{} => {}".format(role.upper(),opt_content), log_options)
		
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
		
		#
		if opt_return_object:
			return obj
		
		# Write history here. (similar to save memory just here we save all chat history)
		# Used messages are saved with SaveMemory()
		if opt_skip_history==False:
			history_path = "{}/history/{}".format(self.Options.get('path', ''), self.Options['AI_FILE_HISTORY'])
			fwrite(history_path,"{}\n".format(json.dumps(obj)),False)
		
		# Save to HISTORY.md (working dir only)
		working_dir = self.Options.get('working_dir')
		PlanSaver.save_history(obj, working_dir)
		
		# Append to chat history. (All data of session)
		self.hHM.msgs.append( obj )
		# Track token counts (only for 'assistant' responses)
		if role == 'assistant':
			prompt_tokens = opts.get('prompt_tokens', 0)
			response_tokens = opts.get('response_tokens', 0)
			self.Options['NUM_LAST_PROMPT_TOKENS'] = prompt_tokens
			self.Options['NUM_LAST_RESPONSE_TOKENS'] = response_tokens
			self.Options['NUM_PROMPT_TOKENS'] = self.Options.get('NUM_PROMPT_TOKENS', 0) + prompt_tokens
			self.Options['NUM_RESPONSE_TOKENS'] = self.Options.get('NUM_RESPONSE_TOKENS', 0) + response_tokens
		return True
	
	#
	def One(self,data, opts=None):
		if opts is None:
			opts = {}
		#self.hLG.echo("Handle.One() START, data.len: {}, opts: {}, hHM.msgs.len: {}".format( len(data), opts, len(hHM.msgs) ))
		opt_history_num    = opts.get('history_num')
		self.Init()
		#
		if opt_history_num!=None:
			# load specific history
			self.hHM.Update()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
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
		while True:
			#
			x = self.You() # return: 0, 1, 2=continue, 3=break, 5=start build, 6=new session
			self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False})
			if x==5:
				self.StartBuild()
			elif x==6:
				return 6
			elif x>=3:
				return x # return 2=continue or 3=break, 4=update handle
			elif x==2:
				continue
			
			#
			# AI()
			x = self.AI()
			self.hLG.echo("Handle.Chat() AI() response: {}".format(x),{'color':False})
			#
			self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1
	
	#
	def Parse(self, res, opts=None):
		if opts is None:
			opts = {}
		print("Handle.Parse() START, opts: {}".format( opts ))
		#
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color    = opts['skip_color'] if 'skip_color' in opts else False
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		color             = True
		if opt_skip_color:
			color=False
		#
		response = self.Stream( res, color )
		print("Debug response.len: ",len(response['content']))
		#
		self.Response('assistant',{
			'content':response['content'],
			'thinking':response['thinking'],
			'skip_history':opt_skip_history,
			'prompt_tokens':response.get('prompt_tokens', 0),
			'response_tokens':response.get('response_tokens', 0),
		})
		#
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		#
		# Check for XML tool invocations
		tool_invocations = self.hTP.ParseTextToolInvocation( response['content'] )
		#
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			job_done = any(inv['name'] == 'jobDone' for inv in tool_invocations)
			#
			result = self.hTP.FireToolInvocation(tool_invocations)
			#
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
							self.Response('system', {'content': 'Mode changed to BUILD. You can now make changes.'})
							self.Response('user', {'content': "{} - {}".format(task_info, instruction)})
			#
			# Return the original response so caller knows tools were executed
			return {'invocations': tool_invocations, 'response': response['content'], 'job_done': job_done }
		#
		if opt_return_object:
			return {'invocations': tool_invocations, 'response': response['content'] }
		return True
	
	#
	def Stream(self, res, color):
		response         = "" # speaking data
		thinking         = "" # thinking data
		if_thinking      = False
		if_speaking      = False
		last_chunk       = None
		#
		for chunk in res:
			last_chunk = chunk
			# thinking
			if chunk.message.thinking:
				#
				if not if_thinking:
					if_thinking = True
					print('Thinking:\n', end='')
				#
				part = chunk.message.thinking
				thinking += part
				print(part, end='', flush=True)
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
				self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True,'speak':True})
		# Extract token counts from final chunk (done=True)
		prompt_tokens = 0
		response_tokens = 0
		if last_chunk and hasattr(last_chunk, 'done') and last_chunk.done:
			prompt_tokens = last_chunk.prompt_eval_count or 0
			response_tokens = last_chunk.eval_count or 0
		return {'content':response, 'thinking':thinking, 'prompt_tokens':prompt_tokens, 'response_tokens':response_tokens}
	
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
				print("Handle.You() Failed! E: ",E)
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
			self.Response('user',{'content':inp})
		
		# Handle model tool calls
		tool_invocations = self.hTP.ParseTextToolInvocation(inp)
		print("DEBUG You() tool_invocations: {}".format(tool_invocations))
		if tool_invocations:
			self.hLG.echo("Handle.You() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self.hTP.FireToolInvocation(tool_invocations)
			#
			return 2 # just to debug tool calls with user input
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
	def AI(self,opts=None):
		if opts is None:
			opts = {}
		#
		self.hLG.echo("Handle.AI() STARTING, opts: {}".format(opts),{'color':False})
		#
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		#
		# Loop to handle multiple rounds of tool calls
		max_iterations = 10
		iteration = 0

		while iteration < max_iterations:
			print("DEBUG AI Iteration {}".format( iteration ))
			iteration += 1

			result        = ""
			res           = {}
			msgs = copy.deepcopy(self.hHM.msgs)

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
			print("DEBUG before chat() num msgs.len: {}, mode: {}".format( len(msgs), self.Options.get('MODE') ))
			try:
				res: ChatResponse = chat(
					self.Options['AI_MODEL'],
					messages=msgs,
					stream=True,
					think=self.Options.get('MODE') == 'plan' or not self.Options.get('BUILD_THINKING_DISABLED', True),
					options=self.Options['AI_OPTIONS'],
				)
			except Exception as e:
				self.hLG.echo("AI connection error: {}".format(str(e)), {'color':True, 'colorValue':'red'})
				return 2
			# Used if CTRL+C to save last/draft content to chat history
			self.Options['DRAFT_RESPONSE'] = res
			# Parse result (handles XML tool calls)
			result = self.Parse(res,{'return_object':True})

			# Stop if model response is empty (no content, no tools)
			if not result.get('response', '').strip() and not result.get('invocations'):
				print("DEBUG AI empty response, stopping iteration")
				return True

			# Stop if jobDone was called
			if result.get('job_done'):
				print("DEBUG AI jobDone detected, stopping iteration")
				return True

			# Check if tools were executed by looking for tool invocations in result
			if not result['invocations']:
				# No more tool calls - return final response
				if opt_return_object:
					return result['response']
				return True
	
	#
	def StartBuild(self, plan_id=None):
		print("Handle.StartBuild() START, plan_id: {}".format(plan_id))
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
			self.Response('system', {'content': 'Mode changed to BUILD. You can now make changes.'})
			self.Response('user', {'content': "Task {}/{} - {}".format(task_number, total_tasks, first_task.instruction)})
			self.hLG.echo("Started build: Task {}/{}".format(task_number, total_tasks), {'color':True, 'colorValue':'green'})
		else:
			self.hLG.echo("No pending tasks in plan!", {'color':True, 'colorValue':'orange'})
