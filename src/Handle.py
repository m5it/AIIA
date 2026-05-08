import json, sys, time, os
from datetime import date
from ollama import ChatResponse, chat
from src.functions import *
from src.ToolChooser import ToolChooser
from src.HistoryManager import HistoryManager
from src.Log import Log
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
		self.msgs     = [] # (MEMORY) Integers from history. Ex: 5, 13, 22. Later is appended last user msg tempolary!
		self.lastMsgs = [] # user,assistant | sys,user,assistant | userTool,assistantTool,
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
	#
	def Init(self):
		#
		self.hPP.GetSessionId()
		self.hPP.UpdateFileNames()
		#
		self.Options['handle_tools']  = {}
		self.Options['current_tools'] = []
		self.Options['AI_ROW_ID']     = 0
	
	#
	def Response(self,role='user',opts=[]):
		global AI_FILE_HISTORY
		#
		opt_content       = opts['content']
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
		
		#
		if opt_name != None:
			obj["name"] = opt_name
		
		#
		if opt_return_object:
			return obj
		
		# Write history here. (similar to save memory just here we save all chat history)
		# Used messages are saved with SaveMemory()
		if opt_skip_history==False:
			fwrite("history/{}".format(self.Options['AI_FILE_HISTORY']),"{}\n".format(json.dumps(obj)),False)
		
		# Append to chat history. (All data of session)
		self.hHM.msgs.append( obj )
		# Current user request and responses only
		self.lastMsgs.append( obj )
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
			self.hHM.Available()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
		#
		self.cmds.CMD_MEMORY_DEL_ALL()
		self.cmds.CMD_MEMORY_ALL_HISTORY()
		#
		# Add system message if not already present (for -Y flag mode)
		system_exists = False
		for msg in self.msgs:
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
- CreateFile: Create new file in work/ (fails if exists). Params: <fileName>, <content>
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
			self.msgs.append( self.Response('system',{'content':system_msg, 'return_object':True}) )
		#
		self.You( data, opts )
		#
		return self.AI( opts )
	
	#
	def Chat(self):
		self.hLG.echo("Handle.Chat() STARTING!",{'color':True})
		#
		while True:
			#
			x = self.You() # return: 0, 1, 2=continue, 3=break
			self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False})
			#
			if x>=3:
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
		print("Handle.Parse() START, lastMsgs.len: {}, opts: {}".format( len(self.lastMsgs), opts ))
		#
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color    = opts['skip_color'] if 'skip_color' in opts else False
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		color             = True
		if opt_skip_color:
			color=False
		response         = ""
		#
		for chunk in res:
			part = chunk['message']['content']
			#tmp  = self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
			self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True,'speak':True})
			response = response+part
		#
		self.Response('assistant',{'content':response,'skip_history':opt_skip_history,})
		#
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True,'speak':True})
		#
		# Check for XML tool invocations
		tool_invocations = self.hTP.ParseTextToolInvocation(response)
		#
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self.hTP.FireToolInvocation(tool_invocations)
			#
			# Return the original response so caller knows tools were executed
			#return response
			return {'invocations': tool_invocations, 'response': response }
		#
		if opt_return_object:
			#return response
			return {'invocations': tool_invocations, 'response': response }
		return True
	
	#
	def You(self, data=None, opts={}):
		#print("DEBUG You() START, data(): {}".format( data ))
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
		if len(inp)>self.Options['AI_MAX_CONTENT_LEN']:
			print("FAILED: content length {} / {}".format( len(inp), self.Options['AI_MAX_CONTENT_LEN'] ))
			return 2 # as continue
		
		# Handle model tool calls
		tool_invocations = self.hTP.ParseTextToolInvocation(inp)
		print("DEBUG You() tool_invocations: {}".format(tool_invocations))
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self.hTP.FireToolInvocation(tool_invocations)
		
		# Append user content
		if inp != None:
			self.Response('user',{'content':inp})
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
			self.lastMsgs = [] # clear lastMsgs
			#
			for msg in self.msgs: # loop trough array of history messages that you wish to include for AIIA
				msgs.append( msg )
				self.lastMsgs.append( msg )
			# append last user message
			if len(self.hHM.msgs)>0:
				msgs.append( self.hHM.msgs[ len(self.hHM.msgs)-1 ] )
				self.lastMsgs.append( self.hHM.msgs[ len(self.hHM.msgs)-1 ] )
			#
			# Nothing to send to AIIA, continue to repeat input!
			if len(msgs)<=0:
				print("WARNING: msgs len is 0, Repeating user_input!")
				return 2 # as continue
			#
			# Chat without tools, normal chat (XML tools handle themselves)
			self.hLG.echo("DEBUG preparing chat (iteration {})".format(iteration),{'color':False})
			res: ChatResponse = chat(
				self.Options['AI_MODEL'],
				messages=msgs,
				stream=True,
				#temperature=self.Options['AI_TEMPERATURE'],
				options={'temperature':self.Options['AI_TEMPERATURE']}
			)
			#
			# Parse result (handles XML tool calls)
			result = self.Parse(res,{'return_object':True, 'skip_history':True})
			#
			# Check if tools were executed by looking for tool invocations in result
			if not result['invocations']:
				# No more tool calls - return final response
				if opt_return_object:
					return result['response']
				return True
			#
			self.hLG.echo("Iteration {}: Found {} more tool call(s), continuing...".format(iteration, len(result['invocations'])), {'color':True, 'colorValue':'orange'})
			# Continue loop - don't return to user yet
		#
		# Max iterations reached
		self.hLG.echo("WARNING: Max tool iterations ({}) reached".format(max_iterations), {'color':True, 'colorValue':'red'})
		return True
