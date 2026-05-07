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
		self.cmds    = self.Commands(self)
		#
		self.hLG     = initmodule(importmodule("Log",True,{'path':'src'}),"Log",{'handle':self,'debug':self.Options['DEBUG']})
		self.hAC     = initmodule(importmodule("Actions",True,{'path':'src'}),"Actions",{'handle':self,})
		self.hTC     = initmodule(importmodule("ToolChooser",True,{'path':'src'}),"ToolChooser",{'handle':self,})
		#self.hTP     = initmodule(importmodule("ToolParser",True,{'path':'src'}),"ToolParser",{'handle':self,})
		self.hHM     = initmodule(importmodule("HistoryManager",True,{'path':'src'}),"HistoryManager",{'handle':self,'quiet':self.Options['QUIET'],'path':self.Options['path']})
	#
	def Init(self):
		#
		self.GetSessionId()
		self.UpdateFileNames()
		#
		self.Options['handle_tools']  = {}
		self.Options['current_tools'] = []
		self.Options['AI_ROW_ID']     = 0
	#
	def GetSessionId(self):
		# load session id
		tmp = fread( self.Options['AI_FILE_SESSID'] )
		if tmp!=False:
			self.Options['AI_SESS_ID'] = int(tmp)
		self.Options['AI_SESS_ID'] = self.Options['AI_SESS_ID']+1
		self.hLG.echo("DEBUG AI_SESS_ID: {}".format( self.Options['AI_SESS_ID'] ))
		fwrite(self.Options['AI_FILE_SESSID'],self.Options['AI_SESS_ID'],True)
	
	#
	def UpdateFileNames(self):
		# generate history file name depend on session and system message
		if self.Options['AI_FILE_LOAD_HISTORY']==False:
			self.Options['AI_FILE_HISTORY'] = "{}.dbk".format(self.Options['AI_SESS_ID'], self.Options['AI_FILE_HISTORY'])
			self.Options['AI_USER_HISTORY'] = "{}.user.dbk".format(self.Options['AI_SESS_ID'], self.Options['AI_FILE_HISTORY'])
			self.hLG.echo("DEBUG generating new history name: {}".format(self.Options['AI_FILE_HISTORY']),{'color':False})
			#self.hHM.history = self.Options['AI_FILE_HISTORY']
		else:
			print("DEBUG using old history name: {}".format(self.Options['AI_FILE_HISTORY']))
	
	#
	def SaveMemory(self):
		self.hLG.echo("Handle.SaveMemory() START, length: {}. history.file: {} vs {} vs {}. DEBUG AI_FILE_LOAD_HISTORY: {}".format( len(self.msgs), self.hHM.history, self.Options['AI_FILE_HISTORY'], self.Options['AI_USER_HISTORY'], self.Options['AI_FILE_LOAD_HISTORY'] ),{'color':False})
		#
		if os.path.exists("history/{}".format(self.Options['AI_USER_HISTORY'])):
			os.remove("history/{}".format(self.Options['AI_USER_HISTORY']))
		# write history here
		for obj in self.msgs:
			fwrite("history/{}".format(self.Options['AI_USER_HISTORY']),"{}\n".format(json.dumps(obj)),False)
	
	#
	def Prepare(self):
		self.hLG.echo("Handle.Prepare() START")
		# Choose system message
		self.hLG.echo("Set system message ( CTRL+x ENTER to Finish. ): ",{'color':True,'colorValue':'orange','debugOnly':False})
		tmp = user_input({'quit_with_ctrlx':True})
		#
			# Default system message teaching model about XML tool invocation
		tool_instructions = """
You are code agent and my best friend.

MODE: {mode}

CRITICAL INSTRUCTION: When user asks you to do something, you MUST USE XML TOOLS to do it.

NEVER write bash scripts that mention tools as strings. ALWAYS USE XML TOOLS DIRECTLY.

ALL TERMINAL COMMANDS GO THROUGH Terminal TOOL.

WHEN USER SAYS: "run ls", "execute ls", "use terminal to..."
→ YOU MUST WRITE: <Terminal><arg1>ls</arg1></Terminal>

EXAMPLES OF XML TOOL USAGE:
- <ReadFile><fileName>test.txt</fileName></ReadFile>
- <WriteFile><fileName>output.txt</fileName><contentOfFile>Hello</contentOfFile></WriteFile>
- <Terminal><arg1>ls</arg1><arg2>-la</arg2></Terminal>
- <List></List>
- <Grep><pattern>TODO</pattern></Grep>

AVAILABLE TOOLS (use exact names):
- Terminal: Execute terminal commands (secure, allowlist-based). Params: <arg1>, [<arg2>], ... (dynamic args)
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
		#
		if tmp!="":
			# append to chat history with tool instructions
			system_content = "{}\n\n{}".format(tmp, tool_instructions.format(mode=self.Options.get('MODE', 'build')))
			self.Response('system',{'content':system_content,})
			# append to chat memory
			self.msgs.append( self.Response('system',{'content':system_content, 'return_object':True}) )
		else:
			# Use default tool instructions as system message
			system_content = tool_instructions.format(mode=self.Options.get('MODE', 'build'))
			self.Response('system',{'content':system_content,})
			self.msgs.append( self.Response('system',{'content':system_content, 'return_object':True}) )
		# Choose actions
		self.hAC.Choose()
		# Choose history
		self.hHM.Choose()
		# Tools will be loaded dynamically when model invokes them via XML
		# self.hTC.Choose(auto_load_all=True)  # Disabled - load on-demand
		return True
	
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
		if opt_parse and rmatch(opt_content,"^\{.*"):
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
		#self.lastMsgs = [] # clear lastMsgs
		#
		x = self.You() # return: 0, 1, 2=continue, 3=break
		#self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False,'debugOnly':False})
		self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False})
		#
		if x!=None and x>=2:
			return x # return 2=continue or 3=break, 4=update handle
		
		#
		# AI() now loops internally to handle multiple tool calls
		# Returns True when done (no more tool calls)
		x = self.AI()
		self.hLG.echo("Handle.Chat() AI() response: {}".format(x),{'color':False})
		
		#
		self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1
		return x
	
	#
	def Parse(self, res, opts={}):
		self.hLG.echo("Handle.Parse() START, lastMsgs.len: {}".format( len(self.lastMsgs) ))
		#
		opt_skip_history  = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color    = opts['skip_color'] if 'skip_color' in opts else False
		opt_return_object = opts['return_object'] if 'return_object' in opts else False
		#opt_response_with = opts['response_with'] if 'response_with' in opts else None
		#opt_response_with_opts = opts['response_with_opts'] if 'response_with_opts' in opts else None
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
		tool_invocations = self.ParseTextToolInvocation(response)
		#
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self.FireToolInvocation(tool_invocations)
			#
			# Return the original response so caller knows tools were executed
			return response
		#
		if opt_return_object:
			return response
		return True
	#--
	# ParseTools():
	# 22.7.25 - ( working on, missing `stream` part. )
	def ParseTools(self,res):
		self.hLG.echo("Handle.ParseTools() START, lastMsgs.len: {}".format( len(self.lastMsgs) ))
		# Handle tool response
		if res.message.tool_calls:
			for tool in res.message.tool_calls:
				toolName = "{}".format(tool.function.name)
				toolData = ""
				failed   = False
				tmph     = None
				#
				if toolName in self.hTC.handles:
					#
					try:
						tmpo     = self.handles[toolName]
						tmph     = tmpo['handle']
						toolData = tmph.run( **tool.function.arguments )
					except Exception as E:
						toolData = {'ERROR':'Executing {} - {}'.format(toolName,E)}
						failed   = True
					
					print("DEBUG tool data type: {}, len: {}, data: {}".format( type(toolData), len(toolData), toolData ))
					
					#
					if failed == False:
						print("Handle.ParseTool() DEBUG! Failed==False, res.message: {}".format( res.message ))
						self.hHM.msgs.append( res.message )
						self.lastMsgs.append( res.message )
					#
					if failed:
						self.Response('tool',{'content':json.dumps(toolData),'name':tool.function.name})
					elif tmph.info['parameters']['returnType']=='object':
						self.Response('tool',{'content':json.dumps(toolData),'name':tool.function.name})
					elif tmph.info['parameters']['returnType']=='string':
						self.Response('tool',{'content':toolData,'name':tool.function.name})
					else:
						print("FAILED, unknown return type: {}".format( type(toolData) ))
					#--
					# Final response for tool
					res = chat( self.Options['AI_MODEL'], messages=self.msgs )
					print("DEBUG final response: ")
					self.Response('assistant',{'content':res.message.content})
				else:
					print("DEBUG tool {} don't exists".format(tool.function.name))
					# This normaly don't happen!...->
					if res.message.content:
						print("DEBUG in tool but content...: {}".format( res.message.content ))
						self.Response('assistant',{'content':res.message.content})
					else:
						print("DEBUG content dont exists either... :x")
						self.Response('tool',{'content':"Tool `{}` don't exists.".format( tool.function.name )})
						#--
						# Final response for tool
						res = chat( self.Options['AI_MODEL'], messages=self.msgs )
						print("DEBUG final response: ")
						self.Response('assistant',{'content':res.message.content})
		# Handle normal chat response
		elif res.message.content:
			self.Response('assistant',{'content':res.message.content})
		# Unknown response or none
		else:
			self.Response('assistant',{'content':"Error: no content?"})
	
	#
	def FireToolInvocation(self, tool_invocations):
		print("DEBUG FireToolInvocation() START, tool_invocations: {}".format(tool_invocations))
		#
		for inv in tool_invocations:
			print("DEBUG FireToolInvocation() name: {}".format(inv['name']))
			toolName = inv['name']
			params   = inv['parameters']
			#
			# Show user what tool is being called (preview)
			params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
			self.hLG.echo("🔧 Executing: {} ({})".format(toolName, params_str if params_str else 'no params'), {'color':True, 'colorValue':'cyan'})
			#
			result = self.ExecuteTextTool(toolName, params)
			print("DEBUG FireToolInvocation() result: ",result)
			#
			# Truncate result if too long
			MAX_PREVIEW = 500
			result_str = str(result)
			if len(result_str) > MAX_PREVIEW:
				result_str = result_str[:MAX_PREVIEW] + "... (truncated, {} chars total)".format(len(str(result)))
			#
			self.hLG.echo("✓ Result: {}".format(result_str), {'color':True, 'colorValue':'green'})
			#
			self.Response('tool',{'content':str(result),'name':toolName})
	#
	def ParseTextToolInvocation(self, text):
		print("DEBUG ParseTextToolInvocation START, text: {}".format( text ))
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
		import re
		results = []
		#
		# Find tool invocations - both full tags and self-closing tags
		# Pattern matches: <TagName>...</TagName> or <TagName/>
		i = 0
		while i < len(text):
			# Find next opening or self-closing tag
			# Match <TagName> or <TagName/>
			tag_match = re.search(r'<(\w+)(?:>|/>)', text[i:])
			if not tag_match:
				break
			
			toolName = tag_match.group(1)
			tag_start = i + tag_match.start()
			tag_end = i + tag_match.end()
			
			# Check if it's a self-closing tag
			if text[tag_end-2:tag_end] == '/>':
				# Self-closing tag - no parameters
				results.append({
					'name': toolName,
					'parameters': {}
				})
				i = tag_end
				continue
			
			# Full tag with closing tag
			inner_start = tag_end
			
			# Find matching closing tag </toolName> (case-insensitive)
			close_tag = '</{}>'.format(toolName)
			close_tag_lower = '</{}>'.format(toolName.lower())
			
			text_lower = text.lower()
			pos = text_lower.find(close_tag_lower, inner_start)
			if pos == -1:
				pos = text.find(close_tag, inner_start)
			
			if pos == -1:
				# No closing tag found, skip
				i = inner_start
				continue
			
			# Extract inner content
			inner_content = text[inner_start:pos]
			
			# Parse parameters from inner content
			params = {}
			param_pattern = r'<(\w+)>(.*?)</\1>'
			for pm in re.finditer(param_pattern, inner_content, re.DOTALL):
				key = pm.group(1)
				value = pm.group(2).strip()
				params[key] = value
			
			results.append({
				'name': toolName,
				'parameters': params
			})
			
			# Move past this tool block
			i = pos + len(close_tag)
		
		return results
	
	#
	def ExecuteTextTool(self, toolName, params):
		print("DEBUG ExecuteTextTool START, toolName: {}".format( toolName ))
		# Execute a tool based on XML invocation
		#
		# ROUTING: If ExecuteScript is called with a non-script file, route to Terminal
		if toolName.lower() == 'executescript':
			fileName = params.get('fileName', '')
			script_extensions = ['.py', '.sh', '.js', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1']
			is_script = any(fileName.lower().endswith(ext) for ext in script_extensions)
			#
			if not is_script and fileName:
				# Route to Terminal tool
				print("Routing ExecuteScript({}) to Terminal tool".format(fileName))
				# Build args for Terminal: arg1=fileName, arg2=args, etc.
				terminal_args = {}
				terminal_args['arg1'] = fileName
				#
			# Add additional args if provided
			if 'args' in params:
				args = params['args']
				# Handle if args is a string (could be JSON array, Python list repr, or space-separated)
				if isinstance(args, str):
					import json
					# Try to parse as JSON array first
					try:
						parsed_args = json.loads(args)
						if isinstance(parsed_args, list):
							for i, arg in enumerate(parsed_args, start=2):
								terminal_args['arg{}'.format(i)] = str(arg)
							args = None  # Mark as processed
					except:
						pass
					#
					if args:  # Not JSON, try other formats
						# Check if it looks like a Python list representation: [item1, item2, ...]
						if args.strip().startswith('[') and args.strip().endswith(']'):
							# Strip brackets and split by comma
							inner = args.strip()[1:-1].strip()
							if inner:  # Not empty
								# Split by comma and clean up
								parts = [p.strip().strip('"\'') for p in inner.split(',')]
								for i, arg in enumerate(parts, start=2):
									if arg:  # Skip empty parts
										terminal_args['arg{}'.format(i)] = arg
							args = None
					#
					if args:  # Still not processed, treat as space-separated
						import shlex
						try:
							parsed_args = shlex.split(args)
							for i, arg in enumerate(parsed_args, start=2):
								terminal_args['arg{}'.format(i)] = arg
						except:
							terminal_args['arg2'] = args
				elif isinstance(args, list):
					for i, arg in enumerate(args, start=2):
						terminal_args['arg{}'.format(i)] = str(arg)
				#
				toolName = 'Terminal'
				params = terminal_args
		#
		# Load tool dynamically if not already loaded
		if toolName not in self.hTC.handles:
			self.hLG.echo("Tool {} not loaded, loading dynamically...".format(toolName), {'color':True, 'colorValue':'orange'})
			#
			try:
				# Find tool file by name
				tool_file = None
				for f in os.listdir(self.Options['tools_path']):
					# Check if file matches tool_XXX.py pattern
					if f.startswith("tool_") and f.endswith(".py"):
						file_tool_name = f[5:-3]  # Extract name from tool_XXX.py
						# Try to match with toolName (case-insensitive)
						if file_tool_name.lower() == toolName.lower():
							tool_file = f
							break
				#
				if tool_file is None:
					return "Tool `{}` not found in tools/".format(toolName)
				#
				# Load the tool
				tmp = splitFileNameExtension(tool_file)
				mod = importmodule(tmp['name'], True, {'path':self.Options['tools_path']})
				#
				# Initialize with proper class name (try toolName or file name)
				h = None
				for cls_name in [toolName, tmp['name']]:
					try:
						h = initmodule(mod, cls_name)
						if h:
							break
					except:
						continue
				#
				if h is None:
					return "Failed to initialize tool `{}`".format(toolName)
				#
				# Store in handles
				self.hTC.handles[toolName] = {'handle': h}
				self.hLG.echo("Tool {} loaded successfully".format(toolName), {'color':True, 'colorValue':'green'})
			except Exception as E:
				return "Error loading tool {}: {}".format(toolName, E)
		#
		# Execute the tool
		try:
			h = self.hTC.handles[toolName]['handle']
			result = h.run(**params)
			return result
		except Exception as E:
			return "Error executing {}: {}".format(toolName, E)
	
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
		
		#
		#try:
		if rmatch(inp,"^!.*"):
			print("handle debug!!!")
			cmds = self.cmds.cmds
			for k in cmds:
				if rmatch(inp,cmds[k]['regex']):
					print("match command! {}".format( cmds[k]['name'] ))
					return cmds[k]['func'](inp)
			print("no match, repeat..., debug({}): {}".format(len(inp),inp))
			return 2 # as continue
		#except Exception as E:
		#	print("Handle.You() !cmd Failed, E: ",E)
		#	return 2
		#
		if len(inp)>self.Options['AI_MAX_CONTENT_LEN']:
			print("FAILED: content length {} / {}".format( len(inp), self.Options['AI_MAX_CONTENT_LEN'] ))
			return 2 # as continue
		
		#
		#tool_invocations1 = self.hTP.ParseTextToolInvocation(inp)
		tool_invocations = self.ParseTextToolInvocation(inp)
		#print("DEBUG You() tool_invocations1: {}".format(tool_invocations1))
		print("DEBUG You() tool_invocations: {}".format(tool_invocations))
		if tool_invocations:
			self.hLG.echo("Parse() detected {} tool invocation(s) in text".format(len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			#
			self.FireToolInvocation(tool_invocations)
		
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
		#opt_response_with = opts['response_with'] if 'response_with' in opts else None
		#opt_response_with_opts = opts['response_with_opts'] if 'response_with_opts' in opts else {}
		#
		# Loop to handle multiple rounds of tool calls
		max_iterations = 5  # Prevent infinite loops
		iteration = 0
		#
		while iteration < max_iterations:
			iteration += 1
			#
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
			tool_invocations = self.ParseTextToolInvocation(result)
			#
			if not tool_invocations:
				# No more tool calls - return final response
				self.Response('assistant',{'content':result,'skip_history':False})
				if opt_return_object:
					return result
				return True
			#
			self.hLG.echo("Iteration {}: Found {} more tool call(s), continuing...".format(iteration, len(tool_invocations)), {'color':True, 'colorValue':'orange'})
			# Continue loop - don't return to user yet
		#
		# Max iterations reached
		self.hLG.echo("WARNING: Max tool iterations ({}) reached".format(max_iterations), {'color':True, 'colorValue':'red'})
		return True
	
	#--
	# class Commands
	class Commands():
		#
		def __init__(self, handle):
			#print("Handle.Commands.__init__() START")
			#
			self.handle = handle
			#
			self.cmds    = {
				"NEW_SESSION":{
					"name"       :"New Session",
					"description":"Like restarting program.",
					"regex"      :r"^!NEW.SESSION+$",
					"usage"      :"!NEW SESSION",
					"func"       :self.CMD_NEW_SESSION,
				},
				"BREAK_SESSION":{
					"name"       :"Break Session",
					"description":"Start new history...",
					"regex"      :r"^!BREAK.SESSION+$",
					"usage"      :"!BREAK SESSION",
					"func"       :self.CMD_BREAK_SESSION,
				},
				"STATS":{
					"name"       :"Stats",
					"description":"Display statistics for program",
					"regex"      :r"^!STATS+$",
					"usage"      :"!STATS",
					"func"       :self.CMD_STATS,
				},
				"ACTION_OPTION_SAVE":{
					"name"       :"Save action options",
					"description":"Save specific action options",
					"regex"      :r"^!AOS.[\d+]+$",
					"usage"      :"!AOS [action_option_num]",
					"func"       :self.CMD_ACTION_OPTION_SAVE,
				},
				"ACTION_OPTIONS_LIST":{
					"name"       :"List action options",
					"description":"List saved action options",
					"regex"      :r"^!AOL+$",
					"usage"      :"!AOL",
					"func"       :self.CMD_ACTION_OPTIONS_LIST,
				},
				"ACTION_OPTIONS":{
					"name"       :"Action Options",
					"description":"LIST, SET, GET action options",
					"regex"      :r"^(!AO)|(!AO.[\d+])|(!AO.[\d+].SET.[a-z]\=[\"\/a-zA-Z0-9])|(!AO.[\d+].GET.[a-z])+$",
					"usage"      :"\nLIST Ex.: !AO [action_num]\nGET Ex.: !AO [action_num] GET path\nSET Ex.: AO [action_num] SET path=/Memorize\n",
					"func"       :self.CMD_ACTION_OPTIONS,
				},
				"IMPORT_ACTIONS":{
					"name"       :"Import Actions",
					"description":"Import actions from classes/code",
					"regex"      :r"^!IA+$",
					"usage"      :"!IA",
					"func"       :self.CMD_IMPORT_ACTIONS,
				},
				"PREVIEW_ACTIONS":{
					"name"       :"Preview Imported Actions",
					"description":"Preview imported actions that are ready to get executed.",
					"regex"      :r"^!PA+$",
					"usage"      :"!PA",
					"func"       :self.CMD_PREVIEW_ACTIONS,
				},
				"EXEC_ACTION":{
					"name"       :"Execute Action",
					"description":"Execute specific action...",
					#"regex"      :r"^(!EA.[\d+])|(!EA.[\d+].DATA.[\d+])+$",
					"regex"      :r"^!EA.[\d+]+$",
					"usage"      :"!EA",
					"func"       :self.CMD_EXEC_ACTION,
				},
				"CLEAR_TOOLS":{
					"name"       :"Clear Tools",
					"description":"Clear loaded tools to start fresh chat or load new tools.",
					"regex"      :r"^!CT+$",
					"usage"      :"!CT",
					"func"       :self.CMD_CLEAR_TOOLS,
				},
				"TOOLS":{
					"name"       :"Tools",
					"description":"Choose tools to use with AIIA.",
					"regex"      :r"^!TOOLS+$",
					"usage"      :"!TOOLS",
					"func"       :self.CMD_TOOLS,
				},
				"PREVIEW_HISTORY":{
					"name"       :"Preview History",
					"description":"Preview current chat history",
					"regex"      :r"^!PH+$",
					"usage"      :"!PH",
					"func"       :self.CMD_PREVIEW_HISTORY,
				},
			"PREVIEW_MEMORY":{
				"name"       :"Preview Memory",
				"description":"Preview current chat memorized messages.",
				"regex"      :r"^!PM+$",
				"usage"      :"!PM",
				"func"       :self.CMD_PREVIEW_MEMORY,
			},
			"MODE":{
				"name"       :"Mode",
				"description":"Switch between plan (0) and build (1) mode. Shows current mode if no argument given.",
				"regex"      :r"^!MODE(\s+[01])?$",
				"usage"      :"!MODE [0|1]",
				"func"       :self.CMD_MODE,
			},
				"MEMORY_SPECIFIC":{
					"name"       :"Memory Specific",
					"description":"Memory specific message from history.",
					"regex"      :r"^!MS.[\d+]+$",
					"usage"      :"!MS [history_num]",
					"func"       :self.CMD_MEMORY_SPECIFIC,
				},
				"MEMORY_ALL_HISTORY":{
					"name"       :"Memory all history",
					"description":"Memory all rows from history.",
					"regex"      :r"^!MAH+$",
					"usage"      :"!MAH",
					"func"       :self.CMD_MEMORY_ALL_HISTORY,
				},
				"MEMORY_LAST":{
					"name"       :"Memory Last",
					"description":"Memory last message from assistant.",
					"regex"      :r"^!ML+$",
					"usage"      :"!ML",
					"func"       :self.CMD_MEMORY_LAST,
				},
				"MEMORY_DEL_ROW":{
					"name"       :"Memory Delete Row",
					"description":"Delete specific row from memory in use.",
					"regex"      :r"^!MDR.[\d+]+$",
					"usage"      :"!MDR [memory_num]",
					"func"       :self.CMD_MEMORY_DEL_ROW,
				},
				"MEMORY_DEL_ALL":{
					"name"       :"Memory Delete All",
					"description":"Delete all rows from memory in use.",
					"regex"      :r"^!MDA+$",
					"usage"      :"!MDA",
					"func"       :self.CMD_MEMORY_DEL_ALL,
				},
				"UPDATE_HANDLE":{
					"name"       :"Update Handle",
					"description":"Reinit code of program. Used after program update so there is no need to stop the program.",
					"regex"      :r"^!UPDATE.HANDLE+$",
					"usage"      :"!UPDATE HANDLE",
					"func"       :self.CMD_UPDATE_HANDLE,
				},
				"QUIT":{
					"name"       :"Quit",
					"description":"Stop the program",
					"regex"      :r"^!QUIT+$",
					"usage"      :"!QUIT",
					"func"       :self.CMD_QUIT,
				},
				"LOAD":{
					"name"       :"Load",
					"description":"Load text file as input to send to AIIA.",
					"regex"      :r"^!QUIT+$",
					"usage"      :"!LOAD textfile.txt Text of textfile.txt will be loaded with this text and sent to AIIA. This is example.",
					"func"       :self.CMD_LOAD,
				},
				"HELP":{
					"name"       :"Help",
					"description":"Display of available actions.",
					"regex"      :r"^!HELP+$",
					"usage"      :"!HELP",
					"func"       :self.CMD_HELP,
				},
			}
		#--
		#
		def CMD_HELP(self, inp=""):
			print("\nAvailable user commands (Ex.: !CMD): ")
			#self.handle.hLG.echo("\nAvailable user commands (Ex.: !CMD): \n",{'color':True,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
			for k in self.cmds:
				print("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ))
				#self.handle.hLG.echo("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ),{'color':True,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
			print("\n")
			return 2
		#
		def CMD_NEW_SESSION(self, inp):
			return 3 # as break
		#
		def CMD_BREAK_SESSION(self, inp):
			return 3
		#
		def CMD_CLEAR_TOOLS(self, inp):
			print("Clearing tools...")
			self.handle.hTC.selected             = []
			self.handle.Options['current_tools'] = []
			self.handle.Options['handle_tools']  = {}
			return 2 # as continue / repeat
		#
		def CMD_TOOLS(self, inp):
			print("Loading tools...")
			return 2 # as continue / repeat
		#
		def CMD_STATS(self, inp):
			print("Stats            :")
			print("-----------------")
			print("mem.msgs.len     : {}".format( len(self.handle.msgs) ))
			print("history.msgs.len : {}".format( len(self.handle.hHM.msgs) ))
			print("last.msgs.len    : {}".format( len(self.handle.lastMsgs) ))
			print(self.handle.lastMsgs)
			print("row_id           : {}".format( self.handle.Options['AI_ROW_ID'] ))
			print("sess_id          : {}".format( self.handle.Options['AI_SESS_ID'] ))
			print("history          : {} / {}".format( self.handle.Options['AI_FILE_HISTORY'], self.handle.hHM.history ))
			print("user.history     : {}".format( self.handle.Options['AI_USER_HISTORY'] ))
			#
			print("available actions: {}".format( len(self.handle.hAC.available) ))
			print("imported actions : {}".format( len(self.handle.hAC.imported) ))
			print("available history: {}".format( len(self.handle.hHM.available) ))
			print("available tools  : {}".format( len(self.handle.hTC.available) ))
			print("imported tools   : {}".format( len(self.handle.hTC.prepared) ))
			print("-----------------")
			print("Options         :")
			print("-----------------")
			for k in self.handle.Options:
				print("{} => {}".format( k, self.handle.Options[ k ] ))
			return 2 # as continue
		#
		def CMD_ACTION_OPTION_SAVE(self,inp=""):
			print("CMD_ACTION_OPTION_SAVE() START!")
		#
		def CMD_ACTION_OPTIONS_LIST(self,inp=""):
			print("CMD_ACTION_OPTIONS_LIST() START!")
		#
		def CMD_ACTION_OPTIONS(self,inp):
			self.handle.hLG.echo("CMD_ACTION_OPTIONS START")
			#
			a = inp.split(" ",3)
			# If you are missing knowledge you land on HELP and informations to learn.
			if len(a)<2:
				self.CMD_HELP()
				return 2
			self.handle.hLG.echo("CMD_ACTION_OPTIONS a({}): {}".format( len(a), a))
			p = int(a[1])
			# Check if action is imported and ready to use, if not get back to You: ...
			if p not in self.handle.hAC.imported:
				print("CMD_ACTION_OPTIONS position {} don't exists!".format( p ))
				return 2
			# Get handle of action
			h = self.handle.hAC.imported[p]
			self.handle.hLG.echo("CMD_ACTION_OPTIONS h( {} ): {}".format( h['name'], h['handle'] ))
			#
			if len(a)>=3 and a[2]=="SET":
				print("CMD_ACTION_OPTIONS SET {}".format( a[3] ))
				#
				a1 = a[3].split("=")
				if a1[0] not in h['handle'].options:
					print("CMD_ACTION_OPTIONS SET {} Failed, key dont exists!".format( a1[0] ))
				#
				h['handle'].options[ a1[0] ] = a1[1]
			elif len(a)>=3 and a[2]=="GET":
				print("CMD_ACTION_OPTIONS GET {}".format( a[3] ))
				if a[3] not in h['handle'].options:
					print("CMD_ACTION_OPTIONS GET {} Failed, key dont exists!".format( a[3] ))
				print("CMD_ACTION_OPTIONS GET {} = {}".format( a[3], h['handle'].options[ a[3] ] ))
			else:
				#
				self.handle.hLG.echo( "USAGE: ", { 'color':True, 'colorValue':'orange', 'debugOnly':False} )
				self.handle.hLG.echo("  !AO [action_num] [cmd] [value]",{'debugOnly':False})
				self.handle.hLG.echo("  !AO 0 GET key",{'debugOnly':False})
				self.handle.hLG.echo("  !AO 0 SET key=value",{'debugOnly':False})
				self.handle.hLG.echo("  key = option name ",{'debugOnly':False})
				#
				self.handle.hLG.echo("Options -> Values for {}".format( h['name'] ), { 'color':True, 'colorValue':'orange', 'debugOnly':False})
				for k in h['handle'].options:
					self.handle.hLG.echo("{} -> {}".format( k, h['handle'].options[k] ),{'debugOnly':False})
			return 2
		#
		def CMD_IMPORT_ACTIONS(self,inp):
			print("CMD_IMPORT_ACTIONS START")
			self.handle.hAC.Choose()
		#
		def CMD_PREVIEW_ACTIONS(self,inp):
			#print("CMD_PREVIEW_ACTIONS START")
			if len(self.handle.hAC.imported)<=0:
				print("No actions imported.")
				return 2
			print("Available actions to import: ")
			n=0
			for k in self.handle.hAC.imported:
				obj = self.handle.hAC.imported[k]
				print("{} / {}.) {}".format( n, k, obj['name'] ))
				n+=1
			print("\nTips:")
			print("Continue with command `!AO...` and `!EA...`")
			print()
			print("!EA - Execute action examples: ")
			print("Usage: !EA [num] aka !EA 0           - Used to execute specific action. In this case action at position 0\n")
			print("!AO - Action options examples: ")
			print("Usage: !AO [num]                     - List specific action options\n")
			print("Usage: !AO [num] SET path /Memorize  - Set action option path=/Memorize\n")
			print("Usage: !AO [num] GET path            - Get action option value\n")
			return 2
		#
		def CMD_EXEC_ACTION(self,inp):
			print("CMD_EXEC_ACTION START, inp: {}".format( inp ))
			a = inp.split(" ")
			print("CMD_EXEC_ACTION DEBUG a",a)
			#
			if len(a)<2:
				print("CMD_EXEC_ACTION Failed length: {}. (D1)".format( len(a) ))
				return 2
			#
			if int(a[1]) not in self.handle.hAC.imported:
				print("CMD_EXEC_ACTION Failed position: {}. (D2)".format( a[1] ))
				return 2
			#
			h = self.handle.hAC.imported[ int(a[1]) ]['handle']
			print("CMD_EXEC_ACTION executing {}".format( h ))
			h.Exec()
			return 2
		#
		def CMD_PREVIEW_HISTORY(self, inp=""):
			self.handle.hLG.echo("Handle.Commands.CMD_PREVIEW_HISTORY START!, history.len: {}".format( len(self.handle.hHM.msgs) ))
			i=0
			for msg in self.handle.hHM.msgs:
				self.handle.hLG.echo("{}.) {}".format( i, msg ),{'debugOnly':self.handle.Options['QUIET']})
				i+=1
			return 2
		#
		def CMD_PREVIEW_MEMORY(self, inp=""):
			self.handle.hLG.echo("Handle.Commands.CMD_PREVIEW_MEMORY START!, memory.len: {}".format( len(self.handle.msgs) ))
			i=0
			for msg in self.handle.msgs:
				self.handle.hLG.echo("{}.) {}".format( i, msg ),{'debugOnly':self.handle.Options['QUIET']})
				i+=1
			return 2
		#
		def CMD_MEMORY_ALL_HISTORY(self,inp=""):
			self.handle.hLG.echo("Handle.Commands.CMD_MEMORY_ALL_HISTORY() START")
			#
			for msg in self.handle.hHM.msgs:
				self.handle.msgs.append( msg )
			#
			if self.handle.Options['QUIET']==False:
				self.handle.SaveMemory()
			self.handle.hLG.echo("Handle.Commands().CMD_MEMORY_ALL_HISTORY() DONE, mem.len: {}".format( len(self.handle.msgs) ))
			return 2
		#
		def CMD_MEMORY_SPECIFIC(self, inp):
			self.handle.hLG.echo("Handle.Commands.CMD_MEMORY_SPECIFIC() START, response: {}".format(inp))
			a = inp.split(" ")
			if len(self.handle.hHM.msgs)<int(a[1]):
				self.handle.hLG.echo("This position {} don't exists!".format(int(a[1])),{'color':True,'colorValue':'orange','debugOnly':False})
				return 2
			msg = self.handle.hHM.msgs[ int(a[1]) ]
			self.handle.hLG.echo("Handle.You() act !MC adding msg: {}".format( msg ))
			self.handle.msgs.append( msg )
			self.handle.SaveMemory()
			return 2
		#
		def CMD_MEMORY_LAST(self, inp=""):
			self.handle.hLG.echo("MEMORY_LAST response!")
			if len(self.handle.hHM.msgs)<=0:
				print("No responses yet in history!")
				return 2
			tmp = self.handle.hHM.msgs[ len(self.handle.hHM.msgs)-1 ]
			self.handle.hLG.echo("Handle.You() act !ML adding msg: {}".format( tmp ))
			self.handle.msgs.append( tmp )
			self.handle.SaveMemory()
			return 2
		#
		def CMD_MEMORY_DEL_ROW(self, inp):
			self.handle.hLG.echo("Handle().CMD_MEMORY_DEL_ROW() START, inp: {}".format(inp))
			a = inp.split(" ")
			self.handle.hLG.echo("Handle().CMD_MEMORY_DEL_ROW() DEBUG num: {} vs self.msgs.len: {}".format( a[1], len(self.handle.msgs) ))
			if len(self.handle.msgs)<int(a[1]):
				print("This position dont exists!",int(a[1]))
				return 2
			del( self.handle.msgs[int(a[1])] )
			self.handle.SaveMemory()
			return 2
		#
		def CMD_MEMORY_DEL_ALL(self, inp=""):
			self.handle.hLG.echo("Handle().CMD_MEMORY_DEL_ROW() START!")
			self.handle.msgs     = []
			self.handle.lastMsgs = []
			return 2
		#
		def CMD_UPDATE_HANDLE(self, inp):
			return 4 # update class Handle()
		#
		def CMD_QUIT(self, inp):
			self.handle.Options['AI_LIVE']=False
			return 3 # as break
		#
		def CMD_LOAD(self, inp):
			self.handle.hLG.echo("DEBUG LOAD FILE...")
			a = pmatch(inp,"^!LOAD\x20([a-zA-Z0-9\/\_\-\.]+)[\x20]?(.*)?")
			try:
				filedata = fread(a[0])
				print("DEBUG filedata({}): {}".format(len(filedata),filedata))
				inp = "{}\n\nData: \n\n{}".format(a[1],filedata)
			except Exception as E:
				print("ERROR LOAD File {}".format(E))
				return 2 # as continue
		
		#
		def Test(self):
			print("Handle.Commands.__init__() START")



		def CMD_MODE(self, inp=""):
			print("CMD_MODE() START, inp: {}".format(inp))
			#
			a = inp.split(" ")
			if len(a) < 2:
				# Show current mode
				mode = self.handle.Options.get('MODE', 'build')
				print("Current mode: {} (0=plan, 1=build)".format(mode))
				return 2
			#
			new_mode = a[1].strip()
			if new_mode not in ['0', '1']:
				print("Invalid mode: {}. Use 0 (plan) or 1 (build)".format(new_mode))
				return 2
			#
			if new_mode == '0':
				self.handle.Options['MODE'] = 'plan'
				print("Mode changed to PLAN. You are now in read-only mode.")
			else:
				self.handle.Options['MODE'] = 'build'
				print("Mode changed to BUILD. You can now make changes.")
			#
			# Update system message with new mode
			for i, msg_obj in enumerate(self.handle.msgs):
				if msg_obj.get('role') == 'system':
					# Replace old system message with updated one
					old_content = msg_obj.get('content', '')
					new_content = old_content.replace('MODE: plan', 'MODE: {}'.format(self.handle.Options['MODE']))
					new_content = new_content.replace('MODE: build', 'MODE: {}'.format(self.handle.Options['MODE']))
					self.handle.msgs[i]['content'] = new_content
					break
			#
			return 2
