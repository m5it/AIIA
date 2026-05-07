from src.functions import fread,fwrite,user_input
#
class Prepare():
	def __init__(self,opts={}):
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
	#
	def GetSessionId(self):
		self.handle.hLG.echo("Prepare.GetSessionId() START")
		# load session id
		tmp = fread( self.handle.Options['AI_FILE_SESSID'] )
		if tmp!=False:
			self.handle.Options['AI_SESS_ID'] = int(tmp)
		self.handle.Options['AI_SESS_ID'] = self.handle.Options['AI_SESS_ID']+1
		self.handle.hLG.echo("DEBUG AI_SESS_ID: {}".format( self.handle.Options['AI_SESS_ID'] ))
		fwrite(self.handle.Options['AI_FILE_SESSID'],self.handle.Options['AI_SESS_ID'],True)
	
	#
	def UpdateFileNames(self):
		self.handle.hLG.echo("Prepare.UpdateFileNames() START")
		# generate history file name depend on session and system message
		if self.handle.Options['AI_FILE_LOAD_HISTORY']==False:
			self.handle.Options['AI_FILE_HISTORY'] = "{}.dbk".format(self.handle.Options['AI_SESS_ID'], self.handle.Options['AI_FILE_HISTORY'])
			self.handle.Options['AI_USER_HISTORY'] = "{}.user.dbk".format(self.handle.Options['AI_SESS_ID'], self.handle.Options['AI_FILE_HISTORY'])
			self.handle.hLG.echo("DEBUG generating new history name: {}".format(self.handle.Options['AI_FILE_HISTORY']),{'color':False})
			#self.handle.hHM.history = self.handle.Options['AI_FILE_HISTORY']
		else:
			print("DEBUG using old history name: {}".format(self.handle.Options['AI_FILE_HISTORY']))
	
	#
	def SaveMemory(self):
		self.hLG.echo("Prepare.SaveMemory() START, length: {}. history.file: {} vs {} vs {}. DEBUG AI_FILE_LOAD_HISTORY: {}".format( len(self.msgs), self.hHM.history, self.Options['AI_FILE_HISTORY'], self.Options['AI_USER_HISTORY'], self.Options['AI_FILE_LOAD_HISTORY'] ),{'color':False})
		#
		if os.path.exists("history/{}".format(self.Options['AI_USER_HISTORY'])):
			os.remove("history/{}".format(self.Options['AI_USER_HISTORY']))
		# write history here
		for obj in self.msgs:
			fwrite("history/{}".format(self.Options['AI_USER_HISTORY']),"{}\n".format(json.dumps(obj)),False)
	
	#
	def Prepare(self):
		self.handle.hLG.echo("Prepare.Prepare() START")
		# Choose system message
		self.handle.hLG.echo("Set system message ( CTRL+x ENTER to Finish. ): ",{'color':True,'colorValue':'orange','debugOnly':False})
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
			system_content = "{}\n\n{}".format(tmp, tool_instructions.format(mode=self.handle.Options.get('MODE', 'build')))
			self.handle.Response('system',{'content':system_content,})
			# append to chat memory
			self.handle.msgs.append( self.handle.Response('system',{'content':system_content, 'return_object':True}) )
		else:
			# Use default tool instructions as system message
			system_content = tool_instructions.format(mode=self.handle.Options.get('MODE', 'build'))
			self.handle.Response('system',{'content':system_content,})
			self.handle.msgs.append( self.handle.Response('system',{'content':system_content, 'return_object':True}) )
		# Choose actions
		self.handle.hAC.Choose()
		# Choose history
		self.handle.hHM.Choose()
		# Tools will be loaded dynamically when model invokes them via XML
		# self.handle.hTC.Choose(auto_load_all=True)  # Disabled - load on-demand
		return True
