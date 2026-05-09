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
		history_path = "{}/history/{}".format(self.Options.get('path', ''), self.Options['AI_USER_HISTORY'])
		if os.path.exists(history_path):
			os.remove(history_path)
		# write history here
		for obj in self.msgs:
			fwrite(history_path,"{}\n".format(json.dumps(obj)),False)
	
	#
	def Prepare(self):
		self.handle.hLG.echo("Prepare.Prepare() START, MODE: {}".format(self.handle.Options.get('MODE', 'build')))
		# Choose system message
		self.handle.hLG.echo("Set system message ( CTRL+x ENTER to Finish. ): ",{'color':True,'colorValue':'orange','debugOnly':False})
		tmp = user_input({'quit_with_ctrlx':True})
		#
		mode = self.handle.Options.get('MODE', 'build')
		#
		tool_instructions = self._get_mode_instructions(mode)
		#
		if tmp!="":
			# append to chat history with tool instructions
			system_content = "{}\n\n{}".format(tmp, tool_instructions)
			self.handle.Response('system',{'content':system_content,})
		else:
			# Use default tool instructions as system message
			system_content = tool_instructions
			self.handle.Response('system',{'content':system_content,})
		# Choose actions
		self.handle.hAC.Choose()
		# Choose history
		self.handle.hHM.Choose()
		# Tools will be loaded dynamically when model invokes them via XML
		return True

	def _get_mode_instructions(self, mode):
		if mode == 'plan':
			return """
You are in PLAN MODE. Your role is to analyze user requests and create structured task plans.

MODE: PLAN (Thinking ENABLED)

HOW TO SPLIT USER INSTRUCTIONS INTO TASKS:
1. Analyze the user's goal - what is the end result they want?
2. Identify distinct steps that can be done independently
3. Create tasks for each step with clear, actionable instructions
4. Order matters - earlier tasks should enable later ones
5. Be specific - each task should have a clear beginning and end

WHY SPLIT INTO TASKS:
- Easier to track progress
- Can resume if interrupted
- Better error handling (failure of one task doesn't affect others)
- Parallel work possible in future

AVAILABLE TOOLS (use exact XML format):
- <createTask><title>Task Title</title><instruction>Detailed step-by-step instruction for the model to follow when executing this task</instruction></createTask>
- <updateTask><id>taskId</id><status>pending|completed|blocked</status></updateTask>
- <deleteTask><id>taskId</id></deleteTask>
- <viewTask/> or <viewTask><id>taskId</id></viewTask>
- <listTasks/>
- <jobDone/> - Call this when plan is finalized and ready for execution

TOOL USAGE GUIDELINES:
- Terminal: Use ONLY for one-liner commands. For complex scripts or data processing, use WriteFile/CreateFile.
- WriteFile / CreateFile: Use for content < 2048 bytes in one call.
- AppendFile: Use when content > 2048 bytes (write first chunk with WriteFile, then AppendFile for rest). Also use for adding to existing files.
- General Rule: NEVER call multiple tool calls for large content. Split large data: WriteFile first chunk → AppendFile remaining.
- Grep / Find / List: Prefer these XML tools over Terminal commands (grep, find, ls).

EXAMPLE WORKFLOW:
1. User says: "I want a web app with login and dashboard"
2. You analyze and create tasks:
   - <createTask><title>Setup Project Structure</title><instruction>Create project folder with basic files: index.html, style.css, app.js, server.py. Initialize npm if needed.</instruction></createTask>
   - <createTask><title>Create Backend API</title><instruction>Create server.py with Flask/FastAPI. Add login endpoint /api/login that validates username/password and returns JWT token. Add /api/dashboard endpoint that requires auth.</instruction></createTask>
   - <createTask><title>Build Frontend Login</title><instruction>Create index.html with login form. Connect to /api/login. Store JWT token in localStorage. Redirect to dashboard on success.</instruction></createTask>
   - <createTask><title>Build Dashboard</title><instruction>Create dashboard view. Fetch user data from /api/dashboard with token. Display user info and logout button.</instruction></createTask>

When all tasks are created, call <jobDone/> to switch to BUILD mode.
"""
		else:  # build mode
			return """
You are in BUILD MODE. Your role is to execute the tasks created in plan mode.

MODE: BUILD (Thinking DISABLED - be concise and direct)

CURRENT TASK:
You will receive task instructions automatically via <nextTask>user messages. Follow each instruction exactly.

AVAILABLE TOOLS (use exact XML format):
- Terminal: Execute terminal commands. Use ONLY for one-liner commands. For scripts or data processing, use WriteFile/CreateFile. Params: <arg1>, [<arg2>], ... (dynamic args)
- ReadFile: Read file. Params: <fileName>
- WriteFile: Write file. Use for content < 2048 bytes. For larger content, use WriteFile for first chunk then AppendFile. Params: <fileName>, <contentOfFile>
- AppendFile: Append to file. Use for content > 2048 bytes or adding to existing files. Params: <fileName>, <contentOfFile>
- CreateFile: Create new file (fails if exists). Use for content < 2048 bytes. Params: <fileName>, <content>
- List: List files. Prefer this over Terminal ls. Params: [<path>] (optional)
- listTools: Show all tools. No params.
- ExecuteScript: Run script (.py, .sh, .js, etc). Params: <fileName>, [<args>]
- Grep: Search by regex. Prefer this over Terminal grep. Params: <pattern>, [<fileName>], [<recursive>]
- Diff: Compare files. Params: <file1>, <file2>, [<unified>]
- Sed: Find/replace. Params: <pattern>, <replacement>, <fileName>, [<inplace>]
- Find: Find by name. Prefer this over Terminal find. Params: <pattern>, [<path>]
- Head: First N lines. Params: <fileName>, [<lines>]
- Tail: Last N lines. Params: <fileName>, [<lines>]
- Sort: Sort lines. Params: <fileName>, [<numeric>], [<reverse>], [<unique>]
- LogProgress: Log what you did on current task. Params: <taskId>, <whatWasDone>
- viewTask: View current plan/tasks. No params.
- listTasks: List all tasks. No params.

TOOL USAGE RULES:
- NEVER call multiple tool calls for large content. Split large data: WriteFile first chunk → AppendFile remaining.
- Prefer XML tools (Grep, Find, List) over Terminal commands (grep, find, ls).
- For file manipulation with complex data, use WriteFile/AppendFile. For one-liners, echo/cat/tee with Terminal is fine.

WORKFLOW:
1. Receive task instruction from <nextTask> message
2. Execute the task using appropriate tools
3. After completing the task, call <nextTask>completed</nextTask>
4. If blocked on something, call <nextTask>blocked</nextTask> and explain what blocked you

EXAMPLE:
Task: "Create project folder with basic files"
1. Use Terminal to create folder: mkdir myproject
2. Use WriteFile/CreateFile to create index.html, style.css, app.js
3. Call <nextTask>completed</nextTask>

If task is blocked (missing info, impossible, etc):
Call <nextTask>blocked</nextTask> with explanation.
"""