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
		"TIP_LIST":{
			"name"       :"Tip List",
			"description":"List all saved tip titles with entry counts.",
			"regex"      :r"^!TL(\s+(user|model))?$",
			"usage"      :"!TL [user|model]",
			"func"       :self.CMD_TIP_LIST,
		},
		"TIP_SAVE":{
			"name"       :"Tip Save",
			"description":"Save the last exchange or a specific history row as a tip under a title.",
			"regex"      :r"^!TS(\s+\d+)?\s+\S+$",
			"usage"      :"!TS [history_num] <title>",
			"func"       :self.CMD_TIP_SAVE,
		},
		"TIP_VIEW":{
			"name"       :"Tip View",
			"description":"View saved tip entries under a title.",
			"regex"      :r"^!TV\s+\S+$",
			"usage"      :"!TV <title>",
			"func"       :self.CMD_TIP_VIEW,
		},
		"TIP_REINSERT":{
			"name"       :"Tip Reinsert",
			"description":"Reinsert saved tip entries into current chat history.",
			"regex"      :r"^!TR\s+\S+$",
			"usage"      :"!TR <title>",
			"func"       :self.CMD_TIP_REINSERT,
		},
		"TIP_DELETE":{
			"name"       :"Tip Delete",
			"description":"Delete all entries under a tip title.",
			"regex"      :r"^!TD\s+\S+$",
			"usage"      :"!TD <title>",
			"func"       :self.CMD_TIP_DELETE,
		},
		"TIP_DELETE_ENTRY":{
			"name"       :"Tip Delete Entry",
			"description":"Delete a specific tip entry by number under a title.",
			"regex"      :r"^!TDR\s+\S+\s+\d+$",
			"usage"      :"!TDR <title> <entry_num>",
			"func"       :self.CMD_TIP_DELETE_ENTRY,
		},
		"TIP_DELETE_ALL":{
			"name"       :"Tip Delete All",
			"description":"Delete all saved tips (optionally by source).",
			"regex"      :r"^!TDA(\s+(user|model))?$",
			"usage"      :"!TDA [user|model]",
			"func"       :self.CMD_TIP_DELETE_ALL,
		},
		"MODE":{
			"name"       :"Mode",
			"description":"Switch between plan and build mode. Shows current mode if no argument given.",
			"regex"      :r"^!MODE(\s+(plan|build))?$",
			"usage"      :"!MODE [plan|build]",
			"func"       :self.CMD_MODE,
		},
		"PLAN":{
			"name"       :"Plan",
			"description":"View current plan status, tasks, and progress.",
			"regex"      :r"^!PLAN(\s+[A-Z]+)?(\s+[\d]+)?$",
			"usage"      :"!PLAN [PREVIEW|VIEW|TASKS|STATUS] [task_id]",
			"func"       :self.CMD_PLAN,
		},
		"START_BUILD":{
			"name"       :"Start Build",
			"description":"Start building from current draft or specific plan by ID.",
			"regex"      :r"^!START_BUILD(\s+[\d\.]+)?$",
			"usage"      :"!START_BUILD [planId]",
			"func"       :self.CMD_START_BUILD,
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
			"BUILD_THINK":{
				"name"       :"Build Think",
				"description":"Enable or disable thinking in build mode.",
				"regex"      :r"^!BUILD_THINK(\s+(true|false))?$",
				"usage"      :"!BUILD_THINK [true|false]",
				"func"       :self.CMD_BUILD_THINK,
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
		print("Tokens          :")
		print("  last_prompt    : {}".format( self.handle.Options['NUM_LAST_PROMPT_TOKENS'] ))
		print("  last_response  : {}".format( self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] ))
		print("  total_prompt   : {}".format( self.handle.Options['NUM_PROMPT_TOKENS'] ))
		print("  total_response : {}".format( self.handle.Options['NUM_RESPONSE_TOKENS'] ))
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
	def CMD_TIP_LIST(self, inp=""):
		a = inp.split()
		source = a[1].strip().lower() if len(a) > 1 and a[1].strip().lower() in ('user','model') else None
		tips = self.handle.hTM.list(source)
		if not tips:
			print("No tips saved.")
			return 2
		print("Tips:")
		for key, info in sorted(tips.items()):
			print("  {}/{} -> {} entries".format(info['source'], info['title'], info['count']))
		return 2
	#
	def CMD_TIP_SAVE(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TS [history_num] <title>")
			return 2
		title = a[-1]
		if len(a) == 2:
			entries = self.handle.hTM.get_last_exchange()
			if entries is None:
				print("No exchange found to save.")
				return 2
		else:
			try:
				num = int(a[1])
			except ValueError:
				print("Usage: !TS [history_num] <title>")
				return 2
			entries = self.handle.hTM.get_exchange_at(num)
			if entries is None:
				print("Invalid history row number.")
				return 2
		self.handle.hTM.save(title, 'user', entries)
		self.handle.hLG.echo("Saved {} message(s) as tip '{}'".format(len(entries), title),{'color':True,'colorValue':'green'})
		return 2
	#
	def CMD_TIP_VIEW(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TV <title>")
			return 2
		title = a[1]
		entries = self.handle.hTM.get(title)
		if not entries:
			print("No tips found for title '{}'".format(title))
			return 2
		print("Tips for '{}':".format(title))
		for i, data in enumerate(entries):
			print("\n--- Entry {} ({} source, session {}) ---".format(i, data.get('source','?'), data.get('sessionId','?')))
			for msg in data.get('entries', []):
				role = msg.get('role','?')
				content = msg.get('content','')
				trunc = content[:200].replace('\n',' ') + ('...' if len(content)>200 else '')
				print("  [{}] {}".format(role, trunc))
		return 2
	#
	def CMD_TIP_REINSERT(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TR <title>")
			return 2
		title = a[1]
		count = self.handle.hTM.reinsert(title)
		self.handle.hLG.echo("Reinserted {} message(s) from tip '{}'".format(count, title),{'color':True,'colorValue':'green'})
		return 2
	#
	def CMD_TIP_DELETE(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TD <title>")
			return 2
		title = a[1]
		removed = self.handle.hTM.delete(title)
		if removed:
			self.handle.hLG.echo("Deleted tip '{}'".format(title),{'color':True,'colorValue':'orange'})
		else:
			print("No tip titled '{}' found.".format(title))
		return 2
	#
	def CMD_TIP_DELETE_ENTRY(self, inp):
		a = inp.split()
		if len(a) < 3:
			print("Usage: !TDR <title> <entry_num>")
			return 2
		title = a[1]
		try:
			num = int(a[2])
		except ValueError:
			print("Entry number must be an integer.")
			return 2
		if self.handle.hTM.delete_entry(title, num):
			self.handle.hLG.echo("Deleted entry {} from tip '{}'".format(num, title),{'color':True,'colorValue':'orange'})
		else:
			print("Entry not found.")
		return 2
	#
	def CMD_TIP_DELETE_ALL(self, inp=""):
		a = inp.split()
		source = a[1].strip().lower() if len(a) > 1 and a[1].strip().lower() in ('user','model') else None
		removed = self.handle.hTM.delete_all(source)
		self.handle.hLG.echo("Deleted {} tip title(s)".format(removed),{'color':True,'colorValue':'orange'})
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
			print("Current mode: {}".format(mode))
			return ret
		#
		new_mode = a[1].strip().lower()
		if new_mode not in ['plan', 'build']:
			print("Invalid mode: {}. Use 'plan' or 'build'".format(new_mode))
			return ret
		#
		if new_mode == 'plan':
			if self.handle.Options['MODE']=='plan':
				print("ERROR: Already in plan mode. Skip.")
				return ret
			self.handle.Options['MODE'] = 'plan'
			print("Mode changed to PLAN. You are now in read-only mode.")
		else:  # build
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
		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			print("DEBUG Commands.CMD_MODE( {} ) replacing system prompt".format( self.handle.Options['MODE'] ))
			self.handle.hHM.msgs[-1]['content'] = "{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) )
		# Append new system prompt
		else:
			print("DEBUG Commands.CMD_MODE( {} ) appending new system prompt".format( self.handle.Options['MODE'] ))
			self.handle.Response('system',{ 'content':"{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) ), })
		#--
		# Depend if plan contain tasks then StartBuild() || <startBuild/> and auto continue to AI
		return ret

	def CMD_BUILD_THINK(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 2:
			current = self.handle.Options.get('BUILD_THINKING_DISABLED', True)
			print("Build thinking disabled: {}".format(current))
			print("Usage: !BUILD_THINK true  (disable thinking)")
			print("       !BUILD_THINK false (enable thinking)")
			return 2
		val = parts[1].strip().lower()
		if val == 'true':
			self.handle.Options['BUILD_THINKING_DISABLED'] = True
			print("Build thinking DISABLED. Model will be concise and direct.")
		elif val == 'false':
			self.handle.Options['BUILD_THINKING_DISABLED'] = False
			print("Build thinking ENABLED. Model can reason step by step.")
		else:
			print("Invalid value: {}. Use true or false.".format(val))
			return 2
		# Update system prompt with new thinking setting
		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			self.handle.hHM.msgs[-1]['content'] = "{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) )
		else:
			self.handle.Response('system',{ 'content':"{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) ), })
		return 2

	def CMD_START_BUILD(self, inp=""):
		from src.PlanManager import PlanBase, Plan
		parts = inp.strip().split()
		plan_id = parts[1] if len(parts) > 1 else None
		if plan_id:
			self.handle.hLG.echo("Loading plan {} and starting build...".format(plan_id), {'color':True, 'colorValue':'cyan'})
		self.handle.StartBuild(plan_id)
		return 2

	def CMD_PLAN(self, inp=""):
		import re
		from src.PlanManager import PlanBase, Plan, PlanTask

		plans_path = self.handle.Options.get('plans_path', 'plans')

		# Parse command
		parts = inp.strip().split()
		action = parts[1].upper() if len(parts) > 1 else 'PREVIEW'
		task_id = parts[2] if len(parts) > 2 else None

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
