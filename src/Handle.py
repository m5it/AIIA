import json, sys, time, os
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
		self.hPM     = PlanBase
	#
	def Init(self):
		#
		self.hPP.GetSessionId()
		self.hPP.UpdateFileNames()
		#
		self.Options['handle_tools']  = {}
		self.Options['current_tools'] = []
		self.Options['AI_ROW_ID']     = 0
		
		# Handle -c / --continue flag
		if self.Options.get('CONTINUE'):
			self._load_continue_session()
	
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
		
		# TODO: Load history from HISTORY.md if needed
		# This would require parsing HISTORY.md back to msg objects
	
	#
	def Response(self,role='user',opts=[]):
		global AI_FILE_HISTORY
		#
		opt_content       = opts['content']
		opt_thinking      = opts['thinking'] if 'thinking' in opts else None
		opt_name          = opts['name'] if 'name' in opts else None
		opt_parse         = opts['parse'] if 'parse' in opts else False # True | False (default)
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		opt_log_options   = opts['log_options'] if 'log_options' in opts else {'color':True,}
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		
		# (Deprecated) was used as test when content was json object
		if opt_parse and rmatch(opt_content,r"^\{.*"):
			print("Handle.Response() PARSING JSON STARTED")
			try:
				opt_content  = opt_content.replace("\\\\\\","\\")
				content = json.loads( opt_content )
				if 'text' in content:
					opt_content = content['text']
			except Exception as E:
				print("Handle.Response() PARSING ERROR: {} on content: {}".format(E,opt_content))
		
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
		return True
	
	#
	def One(self,data, opts={}):
		#self.hLG.echo("Handle.One() START, data.len: {}, opts: {}, hHM.msgs.len: {}".format( len(data), opts, len(hHM.msgs) ))
		opt_history_num    = opts['history_num'] if 'history_num' in opts else None
		opts['skip_color'] = True
		self.Init()
		#
		if opt_history_num!=None:
			# load specific history
			self.hHM.Update()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
		#
		self.cmds.CMD_MEMORY_DEL_ALL()
		self.cmds.CMD_MEMORY_ALL_HISTORY()
		#
		# Add system message if not already present (for -Y flag mode)
		system_exists = False
		for msg in self.hHM.msgs:
			if msg['role'] == 'system':
				system_exists = True
				break
		if not system_exists:
			# Add default system message without prompting user
			system_msg = """You are code agent and my best friend.

CRITICAL INSTRUCTION: When user asks you to do something, you MUST USE XML TOOLS to do it.

NEVER write bash scripts that mention tools as strings. ALWAYS USE XML TOOLS DIRECTLY.

EXAMPLES OF XML TOOL USAGE:
- <ReadFile><fileName>test.txt</fileName></ReadFile>
- <WriteFile><fileName>output.txt</fileName><contentOfFile>Hello</contentOfFile></WriteFile>
- <List></List>
- <Grep><pattern>TODO</pattern></Grep>

AVAILABLE TOOLS (use exact names):
- ReadFile: Read file from work/. Params: <fileName>
- WriteFile: Write file to work/. Params: <fileName>, <contentOfFile>
- AppendFile: Append to file in work/. Params: <fileName>, <contentOfFile>
- CreateFile: Create new file in work/ (fails if exists). Params: <fileName>, <contentOfFile>
- List: List files in a path. Params: [<path>] (optional)
- listTools: Show all available tools. No params.
- ExecuteScript: Run script (.py, .sh, .js, etc). Params: <fileName>, [<args>]
- Grep: Search files by regex pattern. Params: <pattern>, [<fileName>], [<recursive>]
- Diff: Compare two files. Params: <file1>, <file2>, [<unified>]
- Sed: Find/replace in files. Params: <pattern>, <replacement>, <fileName>, [<inplace>]
- Find: Find files by name pattern. Params: <pattern>, [<path>]
- Head: Show first N lines of file. Params: <fileName>, [<lines>]
- Tail: Show last N lines of file. Params: <fileName>, [<lines>]
- Sort: Sort lines in file. Params: <fileName>, [<numeric>  [<reverse>], [<unique>]
"""
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
		PlanBase.LoadAll(self.Options.get('plans_path', 'plans'))
		#
		while True:
			#
			x = self.You() # return: 0, 1, 2=continue, 3=break, 5=start build
			self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False})
			if x==5:
				self.StartBuild()
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
	def Parse(self, res, opts={}):
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
		self.Response('assistant',{'content':response['content'],'thinking':response['thinking'],'skip_history':opt_skip_history,})
		#
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		#
		# Check for XML tool invocations
		tool_invocations = self.hTP.ParseTextToolInvocation( response['content'] )
		#
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
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
			return {'invocations': tool_invocations, 'response': response['content'] }
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
		#
		for chunk in res:
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
				part = chunk['message']['content']
				response += part
				self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True,'speak':True})
		return {'content':response, 'thinking':thinking}
	
	#
	def You(self, data=None, opts={}):
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
	def AI(self,opts={}):
		#
		self.hLG.echo("Handle.AI() STARTING, opts: {}".format(opts),{'color':False})
		#
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		#
		# Loop to handle multiple rounds of tool calls
		max_iterations = 5  # Prevent infinite loops
		iteration = 0
		#
		while iteration < max_iterations:
			print("DEBUG AI Iteration {}".format( iteration ))
			iteration += 1
			#
			result        = ""
			res           = {}
			msgs          = [] # temporary array of messages to send to AIIA
			#
			for msg in self.hHM.msgs: # loop trough array of current history messages that you wish to include for AIIA
				msgs.append( msg )
			#
			# Nothing to send to AIIA, continue to user input!
			if len(msgs)<=0:
				print("WARNING: msgs len is 0, Repeating user_input!")
				return 2 # as continue
			#
			# Chat without tools, normal chat (XML tools handle themselves)
			self.hLG.echo("DEBUG preparing chat (iteration {})".format(iteration),{'color':False})
			print("DEBUG before chat() num msgs.len: {}, mode: {}".format( len(msgs), self.Options.get('MODE') ))
			res: ChatResponse = chat(
				self.Options['AI_MODEL'],
				messages=msgs,
				stream=True,
				think=self.Options.get('MODE') == 'plan', # thinking enabled only in plan mode
				# Available options keys:
				# mirostat, mirostat_eta, mirostat_tau, num_ctx, repeat_last_n, repeat_penalty, temperature, seed, stop, num_predict, top_k, top_p, min_p
				#options={'temperature':self.Options['AI_TEMPERATURE']}
				options=self.Options['AI_OPTIONS'],
			)
			# Used if CTRL+C to save last/draft content to chat history
			self.Options['DRAFT_RESPONSE'] = res
			# Parse result (handles XML tool calls)
			result = self.Parse(res,{'return_object':True})
			# Check if tools were executed by looking for tool invocations in result
			if not result['invocations']:
				# No more tool calls - return final response
				if opt_return_object:
					return result['response']
				return True

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
