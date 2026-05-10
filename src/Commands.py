#--
# class Commands
class Commands():
	#
	def __init__(self, opts={}):
		#print("Handle.Commands.__init__() START")
		#
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
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
		"PLAN":{
			"name"       :"Plan",
			"description":"View current plan status, tasks, and progress.",
			"regex"      :r"^!PLAN(\s+[A-Z]+)?(\s+[\d]+)?$",
			"usage"      :"!PLAN [PREVIEW|VIEW|TASKS|STATUS] [task_id]",
			"func"       :self.CMD_PLAN,
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
		print("history.msgs.len : {}".format( len(self.handle.hHM.msgs) ))
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
	
	#
	def CMD_MODE(self, inp=""):
		print("CMD_MODE() START, inp: {}".format(inp))
		#
		ret = 2 # 2=repeat You(), 5=Start Build
		a = inp.split(" ")
		if len(a) < 2:
			# Show current mode
			mode = self.handle.Options.get('MODE', 'build')
			print("Current mode: {} (0=plan, 1=build)".format(mode))
			return ret
		#
		new_mode = a[1].strip()
		if new_mode not in ['0', '1']:
			print("Invalid mode: {}. Use 0 (plan) or 1 (build)".format(new_mode))
			return ret
		#
		if new_mode == '0':
			if self.handle.Options['MODE']=='plan':
				print("ERROR: Already in plan mode. Skip.")
				return ret
			self.handle.Options['MODE'] = 'plan'
			print("Mode changed to PLAN. You are now in read-only mode.")
		else:
			if self.handle.Options['MODE']=='build':
				print("ERROR: Already in build mode. Skip.")
				return ret
			self.handle.Options['MODE'] = 'build'
			print("Mode changed to BUILD. You can now make changes.")
			# Check if plan has tasks - if yes, return 5 to trigger startBuild
			from src.PlanManager import PlanBase
			if PlanBase.draft and len(PlanBase.draft.tasks) > 0:
				ret = 5  # startBuild signal
				print("Plan has {} tasks. Starting build...".format(len(PlanBase.draft.tasks)))
			
		#--
		# Update System message with new mode!
		# Check if last history msgs is role:system then replace it.
		#       else append as new msg. Ollama support multiple system prompts in one chat history!
		# Prepare()._get_mode_instructions( 'build' )
		#--
		# Replace current system prompt because is last in chat history
		if self.handle.hHM.msgs[-1]['role'] == 'system':
			print("DEBUG Commands.CMD_MODE( {} ) replacing system prompt".format( self.handle.Options['MODE'] ))
			self.handle.hHM.msgs[-1]['content'] = "{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) )
		# Append new system prompt
		else:
			print("DEBUG Commands.CMD_MODE( {} ) appending new system prompt".format( self.handle.Options['MODE'] ))
			self.handle.Response('system',{ 'content':"{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) ), })
		#--
		# Depend if plan contain tasks then StartBuild() || <startBuild/> and auto continue to AI
		return ret

	def CMD_PLAN(self, inp=""):
		import re
		from src.PlanManager import PlanBase, Plan, PlanTask

		plans_path = self.handle.Options.get('plans_path', 'plans')

		# Parse command
		parts = inp.strip().split()
		action = parts[0] if len(parts) > 0 else 'PREVIEW'
		task_id = parts[1] if len(parts) > 1 else None

		action = action.upper()

		if action == 'PREVIEW' or action == '':
			# Show current plan overview
			if PlanBase.draft:
				plan = PlanBase.draft
				print("\n=== CURRENT PLAN ===")
				print("Plan ID: {}".format(plan.id))
				print("Title: {}".format(plan.title))
				print("Status: {}".format("DRAFT (in progress)" if plan.endTimestamp is None else "COMPLETED"))
				print("\n--- TASKS ---")
				pending = completed = blocked = 0
				for tid, task in plan.tasks.items():
					status = task.status
					if status == 'pending': pending += 1
					elif status == 'completed': completed += 1
					elif status == 'blocked': blocked += 1
				print("Pending: {} | Completed: {} | Blocked: {}".format(pending, completed, blocked))
				if pending > 0:
					for tid, task in plan.tasks.items():
						if task.status == 'pending':
							print("\nNEXT TASK:")
							print("  ID: {}".format(tid))
							print("  Instruction: {}".format(task.instruction[:100] + "..." if len(task.instruction) > 100 else task.instruction))
							break
			else:
				print("\nNo active plan.")
				print("Plans in history: {}".format(len(PlanBase.done)))

		elif action == 'VIEW' or action == 'TASKS':
			if PlanBase.draft:
				plan = PlanBase.draft
				print("\n=== PLAN TASKS ===")
				for tid, task in plan.tasks.items():
					status_icon = {'pending': '⏳', 'completed': '✓', 'blocked': '✗'}.get(task.status, '?')
					print("\n{} Task ID: {}".format(status_icon, tid))
					print("   Status: {}".format(task.status))
					print("   Instruction: {}".format(task.instruction[:80] + "..." if len(task.instruction) > 80 else task.instruction))
					if task.log:
						print("   Log entries: {}".format(len(task.log)))
			else:
				print("\nNo active plan.")

		elif action == 'STATUS':
			if PlanBase.draft:
				plan = PlanBase.draft
				print("\n=== PLAN STATUS ===")
				print("MODE: {}".format(self.handle.Options.get('MODE', 'build')))
				print("Plan ID: {}".format(plan.id))
				print("Tasks: {} total".format(len(plan.tasks)))
				for tid, task in plan.tasks.items():
					if task.status == 'pending':
						print("- [PENDING] {}".format(tid))
					elif task.status == 'completed':
						print("- [DONE] {}".format(tid))
					elif task.status == 'blocked':
						print("- [BLOCKED] {}".format(tid))
			else:
				print("\nNo active plan.")

		else:
			print("\nUsage: !PLAN [PREVIEW|VIEW|TASKS|STATUS]")
			print("  PREVIEW  - Show plan overview (default)")
			print("  VIEW     - Show all tasks with details")
			print("  TASKS    - Same as VIEW")
			print("  STATUS   - Show quick status")

		return 2
