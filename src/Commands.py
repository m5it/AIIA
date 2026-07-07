#--
# class Commands
import os, json
import ollama
from src.functions import fread, fwrite, pmatch
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
				"description":"Reset everything and start fresh with Prepare().",
				"regex"      :r"^!NEW_SESSION$",
				"usage"      :"!NEW SESSION",
				"func"       :self.CMD_NEW_SESSION,
			},
			"CLEAR":{
				"name"       :"Clear History",
				"description":"Clear chat history but keep system prompt and persona.",
				"regex"      :r"^!CLEAR$",
				"usage"      :"!CLEAR",
				"func"       :self.CMD_CLEAR,
			},
			"REMOVE":{
				"name"       :"Remove Row",
				"description":"Remove a specific row from chat history by number (use !PH to see row numbers).",
				"regex"      :r"^!RM\s+\d+$",
				"usage"      :"!RM <row_num>",
				"func"       :self.CMD_REMOVE,
			},
			"STATS":{
				"name"       :"Stats",
				"description":"Display statistics for program",
				"regex"      :r"^!STATS$",
				"usage"      :"!STATS",
				"func"       :self.CMD_STATS,
			},

			"PREVIEW_HISTORY":{
				"name"       :"Preview History",
				"description":"Preview current chat history",
				"regex"      :r"^!PH$",
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
		"OLLAMA_LIST":{
			"name"       :"Models",
			"description":"List available Ollama models, with previously used ones at top.",
			"regex"      :r"^!MODELS$",
			"usage"      :"!MODELS",
			"func"       :self.CMD_OLLAMA_LIST,
		},
		"MODEL":{
			"name"       :"Model",
			"description":"Switch AI model. Shows current model if no argument.",
			"regex"      :r"^!MODEL(\s+\S+)?$",
			"usage"      :"!MODEL [model_name]",
			"func"       :self.CMD_MODEL,
		},
		"PLAN":{
			"name"       :"Plan",
			"description":"View or modify plan status. Use CLEAR/DELETE/RESET to remove plans.",
			"regex"      :r"^!PLAN(\s+[A-Za-z]+)?(\s+[\d\.]+)?$",
			"usage"      :"!PLAN [PREVIEW|VIEW|TASKS|STATUS|CLEAR|DELETE|RESET] [task_id]",
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
				"regex"      :r"^!UPDATE_HANDLE$",
				"usage"      :"!UPDATE HANDLE",
				"func"       :self.CMD_UPDATE_HANDLE,
			},
"QUIT":{
				"name"       :"Quit",
				"description":"Quit the program.",
				"regex"      :r"^!QUIT$",
				"usage"      :"!QUIT",
				"func"       :self.CMD_QUIT,
			},
		"INSTRUCT_LIST":{
			"name"       :"Instruct List",
			"description":"List available instruct personas.",
			"regex"      :r"^!INSTRUCT_LIST$",
			"usage"      :"!INSTRUCT_LIST",
			"func"       :self.CMD_INSTRUCT_LIST,
		},
		"INSTRUCT_SWITCH":{
			"name"       :"Instruct Switch",
			"description":"Switch to a different instruct persona without clearing history.",
			"regex"      :r"^!INSTRUCT_SWITCH\s+\S+$",
			"usage"      :"!INSTRUCT_SWITCH <persona_name>",
			"func"       :self.CMD_INSTRUCT_SWITCH,
		},
		"WORKERS":{
			"name"       :"Workers",
			"description":"List connected orchestra workers and their status.",
			"regex"      :r"^!WORKERS$",
			"usage"      :"!WORKERS",
			"func"       :self.CMD_WORKERS,
		},
		"DISPATCH":{
			"name"       :"Dispatch",
			"description":"Dispatch pending tasks to orchestra workers.",
			"regex"      :r"^!DISPATCH$",
			"usage"      :"!DISPATCH",
			"func"       :self.CMD_DISPATCH,
		},
		"PLAN_WORKER":{
			"name"       :"Plan Worker",
			"description":"Set or show which worker handles planning. Use 'off' to plan locally.",
			"regex"      :r"^!PLAN_WORKER(\s+\S+)?$",
			"usage"      :"!PLAN_WORKER <name|off>",
			"func"       :self.CMD_PLAN_WORKER,
		},
		"BUILD_THINK":{
			"name"       :"Build Think",
			"description":"Enable or disable thinking in build mode.",
			"regex"      :r"^!BUILD_THINK(\s+(true|false))?$",
			"usage"      :"!BUILD_THINK [true|false]",
			"func"       :self.CMD_BUILD_THINK,
		},
		"CACHE_CLEAR":{
			"name"       :"Cache Clear",
			"description":"Clear all cached tool results.",
			"regex"      :r"^!CACHE_CLEAR$",
			"usage"      :"!CACHE_CLEAR",
			"func"       :self.CMD_CACHE_CLEAR,
		},
		"PROJECT":{
			"name"       :"Project",
			"description":"View or modify project path approvals (directories/files the model can access).",
			"regex"      :r"^!PROJECT(\s+(ADD|DENY|REMOVE|RESET)(\s+(DIR|FILE))?\s*.+)?$",
			"usage"      :"!PROJECT [ADD DIR|FILE <path>] [DENY <path>] [REMOVE DIR|FILE <path>] [RESET]",
			"func"       :self.CMD_PROJECT,
		},
		"HELP":{
				"name"       :"Help",
				"description":"Display help and available commands.",
				"regex"      :r"^!HELP$",
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
		# Clear in-memory history
		self.handle.hHM.msgs = []
		# Clear main history file on disk
		history_path = "{}/history/{}".format(self.handle.Options.get('path', ''), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(history_path)
		except Exception:
			pass
		# Clear project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			try:
				os.remove(proj_history)
			except Exception:
				pass
		# Reset counters
		self.handle.Options['AI_ROW_ID'] = 0
		self.handle.Options['NUM_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_RESPONSE_TOKENS'] = 0
		self.handle.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		# Reset tools
		self.handle.Options['current_tools'] = []
		self.handle.Options['handle_tools'] = {}
		self.handle.hTC.selected = []
		self.handle.hTC.prepared = []
		# Clear plan state
		from src.PlanManager import PlanBase
		PlanBase.draft = None
		PlanBase.done = {}
		# Reset draft response
		self.handle.Options['DRAFT_CONTENT'] = None
		self.handle.Options['DRAFT_RESPONSE'] = None
		# Reset continuation flags
		self.handle.Options['CONTINUING'] = False
		self.handle.Options['AI_FILE_LOAD_HISTORY'] = False
		# Clear caches and consumed tips
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		return 6
	#
	def CMD_CLEAR(self, inp):
		from src.PlanSaver import PlanSaver
		# Archive raw history before clearing — preserves training data
		msg_count = len(self.handle.hHM.msgs)
		archive_name = self.handle._archive_history('cleared')
		if archive_name:
			self.handle._save_clear_tip(archive_name, msg_count)
		# Keep system message(s), clear everything else
		system_msgs = [m for m in self.handle.hHM.msgs if m['role'] == 'system']
		self.handle.hHM.msgs = system_msgs[:]
		# Clear main history file on disk and rewrite system msgs
		main_path = "{}/history/{}".format(self.handle.Options.get('path', ''), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in system_msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rewrite project HISTORY.md with system msgs only
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, system_msgs)
		# Reset row ID and tokens
		self.handle.Options['AI_ROW_ID'] = 0
		self.handle.Options['NUM_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_RESPONSE_TOKENS'] = 0
		self.handle.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		print("Chat history cleared. System prompt preserved.")
		return 2
	#
	def CMD_REMOVE(self, inp):
		from src.PlanSaver import PlanSaver
		a = inp.strip().split()
		if len(a) < 2:
			print("Usage: !RM <row_num>")
			return 2
		try:
			num = int(a[1])
		except ValueError:
			print("Row number must be an integer.")
			return 2
		if num < 0 or num >= len(self.handle.hHM.msgs):
			print("Row {} does not exist. History has {} rows.".format(num, len(self.handle.hHM.msgs)))
			return 2
		removed = self.handle.hHM.msgs.pop(num)
		print("Removed row {}: [{}] {}".format(num, removed.get('role','?'), removed.get('content','')[:80]))
		# Rebuild main history file on disk
		main_path = "{}/history/{}".format(self.handle.Options.get('path', ''), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in self.handle.hHM.msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rebuild project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, self.handle.hHM.msgs)
		return 2
	#
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
	def CMD_PROJECT(self, inp=""):
		"""!PROJECT — view or modify project path approvals"""
		pa = self.handle.Options.get('path_approver')
		if not pa:
			print("No path approver configured.")
			return 2
		parts = inp.strip().split()
		if len(parts) < 2:
			print("Project Path Approvals:")
			print("  Working dir:", pa.working_dir)
			print("  Approved dirs: {}".format(sorted(pa.approved_dirs) if pa.approved_dirs else "(none - defaults to .)"))
			print("  Approved files: {}".format(sorted(pa.approved_files) if pa.approved_files else "(none)"))
			print("  Denied paths: {}".format(sorted(pa.denied_paths) if pa.denied_paths else "(none)"))
			return 2
		action = parts[1].upper()
		if action == 'ADD' and len(parts) >= 4:
			kind = parts[2].upper()
			path = ' '.join(parts[3:])
			if kind == 'DIR':
				pa.add_dir(path)
				pa.save()
				print("Approved directory '{}'".format(path))
			elif kind == 'FILE':
				pa.add_file(path)
				pa.save()
				print("Approved file '{}'".format(path))
			else:
				print("Usage: !PROJECT ADD DIR <path> or !PROJECT ADD FILE <path>")
		elif action == 'DENY' and len(parts) >= 3:
			path = ' '.join(parts[2:])
			pa.deny(path)
			pa.save()
			print("Denied path '{}'".format(path))
		elif action == 'REMOVE' and len(parts) >= 4:
			kind = parts[2].upper()
			path = ' '.join(parts[3:])
			if kind == 'DIR':
				pa.approved_dirs.discard(path)
				pa.save()
				print("Removed approved directory '{}'".format(path))
			elif kind == 'FILE':
				pa.approved_files.discard(path)
				pa.save()
				print("Removed approved file '{}'".format(path))
			else:
				print("Usage: !PROJECT REMOVE DIR <path> or !PROJECT REMOVE FILE <path>")
		elif action == 'RESET':
			pa.approved_dirs = {'.'}
			pa.approved_files = set()
			pa.denied_paths = set()
			pa.save()
			print("Path approvals reset to default (only working directory).")
		else:
			print("Unknown command. Usage:")
			print("  !PROJECT — show current approvals")
			print("  !PROJECT ADD DIR <path> — approve a directory")
			print("  !PROJECT ADD FILE <path> — approve a file")
			print("  !PROJECT DENY <path> — block a path")
			print("  !PROJECT REMOVE DIR|FILE <path> — remove an approval")
			print("  !PROJECT RESET — reset to defaults")
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
		if title in self.handle._consumed_tips:
			print("Tip '{}' was already reinserted this session.".format(title))
			return 2
		count = self.handle.hTM.reinsert(title)
		if count > 0:
			self.handle.hLG.echo("Reinserted {} message(s) from tip '{}'".format(count, title),{'color':True,'colorValue':'green'})
		else:
			print("No entries found for tip title '{}'.".format(title))
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
	def CMD_CACHE_CLEAR(self, inp=""):
		count = self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		self.handle.hLG.echo("Cleared {} cached tool result(s) and reset consumed tips.".format(count),{'color':True,'colorValue':'orange'})
		return 2
	#
	def CMD_UPDATE_HANDLE(self, inp):
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		return 4 # update class Handle()
	#
	def CMD_QUIT(self, inp):
		self.handle.Options['AI_LIVE']=False
		return 3 # as break
	#
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
			
		# Persist mode to file
		mode_file = self.handle.Options.get('AI_FILE_MODE')
		if mode_file:
			fwrite(mode_file, new_mode, True)
			
		#--
		# Update System message with new mode!
		# Check if last history msgs is role:system then replace it.
		#       else append as new msg. Ollama support multiple system prompts in one chat history!
		# Prepare()._get_mode_instructions( 'build' )
		#--
		# Replace current system prompt because is last in chat history
		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			self.handle.hHM.msgs[-1]['content'] = "{}".format( self.handle.hPP._get_mode_instructions( self.handle.Options['MODE'] ) )
		# Append new system prompt
		else:
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

	def CMD_INSTRUCT_LIST(self, inp=""):
		print("Available personas:")
		self.handle.hIM.Available()
		return 2

	def CMD_INSTRUCT_SWITCH(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 2:
			print("Usage: !INSTRUCT_SWITCH <persona_name>")
			return 2
		name = parts[1]
		if not self.handle.hIM.Exists(name):
			print("Persona '{}' not found. Use !INSTRUCT_LIST to see available personas.".format(name))
			return 2
		self.handle.Options['INSTRUCT_CLASS'] = name
		self.handle.hIM.ApplyPersonaModel(name)
		mode = self.handle.Options.get('MODE', 'build')
		system_content = self.handle.hPP._get_mode_instructions(mode)
		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			self.handle.hHM.msgs[-1]['content'] = system_content
		else:
			self.handle.Response('system', {'content': system_content})
		self.handle.hLG.echo("Switched persona to '{}'".format(name), {'color':True, 'colorValue':'green'})
		return 2

	def CMD_WORKERS(self, inp=""):
		if hasattr(self.handle, 'hOD') and self.handle.hOD:
			print(self.handle.hOD.get_status_str())
		else:
			print("Orchestra not available in this mode.")
		return 2

	def CMD_DISPATCH(self, inp=""):
		if not hasattr(self.handle, 'hOD') or not self.handle.hOD:
			print("Orchestra not available in this mode.")
			return 2
		self.handle.hOD.enter_dispatch_mode()
		return 2

	def CMD_PLAN_WORKER(self, inp=""):
		if not hasattr(self.handle, 'hOD') or not self.handle.hOD:
			print("Orchestra not available in this mode.")
			return 2
		parts = inp.strip().split()
		if len(parts) < 2:
			current = self.handle.Options.get('PLAN_WORKER', None)
			if current:
				print("Plan worker: {} (use !PLAN_WORKER off to disable)".format(current))
			else:
				print("No plan worker set. Director plans locally.")
			return 2
		name = parts[1].strip().lower()
		if name == 'off':
			self.handle.hOD.set_plan_worker(None)
			return 2
		ok = self.handle.hOD.set_plan_worker(name)
		if not ok:
			print("Worker '{}' not found. Use !WORKERS to see connected workers.".format(name))
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

		elif action == 'CLEAR':
			if PlanBase.draft:
				count = len(PlanBase.draft.tasks)
				PlanBase.draft.tasks = {}
				PlanBase.draft.save(plans_path)
				print("Cleared {} tasks from current plan.".format(count))
			else:
				print("No active plan.")

		elif action == 'DELETE' or action == 'RESET':
			if PlanBase.draft:
				plan_id = PlanBase.draft.id
				PlanBase.draft = None
				PlanBase.Delete(plan_id, plans_path)
				print("Plan {} deleted.".format(plan_id))
			else:
				print("No active plan.")

		else:
			print("\nUsage: !PLAN [PREVIEW|VIEW|TASKS|STATUS|CLEAR|DELETE|RESET]")
			print("  PREVIEW  - Show plan overview (default)")
			print("  VIEW     - Show all tasks with details")
			print("  TASKS    - Same as VIEW")
			print("  STATUS   - Show quick status")
			print("  CLEAR    - Remove all tasks from current plan")
			print("  DELETE   - Delete current plan entirely")
			print("  RESET    - Same as DELETE")

		return 2

	def CMD_OLLAMA_LIST(self, inp=""):
		"""List available Ollama models, with previously used ones at top."""
		try:
			used = self.handle.Options.get('used_models', [])
			res = ollama.list()

			if used:
				print("Previously used models:")
				for m in used:
					print("  ★ {}".format(m))
				print("")

			print("All available Ollama models:")
			all_names = [m.model for m in res.models]
			for name in all_names:
				if name not in used:
					print("  {}".format(name))
		except Exception as e:
			print("Error listing models: {}".format(e))
		return 2

	def CMD_MODEL(self, inp=""):
		"""Switch AI model mid-session."""
		a = inp.strip().split()
		if len(a) < 2:
			print("Current model: {}".format(self.handle.Options.get('AI_MODEL', '(not set)')))
			print("Usage: !MODEL <model_name>")
			print("Tip: use !MODELS to see available models")
			return 2
		new_model = a[1].strip()
		old = self.handle.Options.get('AI_MODEL', '')
		if new_model == old:
			print("Already using '{}'".format(old))
			return 2
		self.handle.Options['AI_MODEL'] = new_model
		# Track in used_models
		models = self.handle.Options.get('used_models', [])
		if new_model not in models:
			models.append(new_model)
			self.handle._save_used_models(models)
		print("Model changed: '{}' -> '{}'".format(old, new_model))
		# Apply model registry
		from src.ModelRegistry import apply as apply_registry
		reg_changes = apply_registry(self.handle.Options, new_model)
		if reg_changes:
			for c in reg_changes:
				print("  {}".format(c))
		# Stop any loaded model that differs from the new one (free GPU memory)
		try:
			import subprocess
			r = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
			if r.returncode == 0:
				for line in r.stdout.strip().split('\n')[1:]:
					parts = line.split()
					if parts and parts[0] and parts[0] != new_model:
						subprocess.run(['ollama', 'stop', parts[0]], capture_output=True, timeout=10)
						print("  Freed memory: stopped {}".format(parts[0]))
		except Exception:
			pass
		return 2
