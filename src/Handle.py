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
		self.Options  = Options
		self.msgs     = [] # (MEMORY) Integers from history. Ex: 5, 13, 22. Later is appended last user msg tempolary!
		self.lastMsgs = [] # user,assistant | sys,user,assistant | userTool,assistantTool,
		#
		self.cmds    = self.Commands(self)
		#
		self.hLG     = initmodule(importmodule("Log",True,{'path':'src'}),"Log",{'debug':self.Options['DEBUG']})
		self.hAC     = initmodule(importmodule("Actions",True,{'path':'src'}),"Actions",{'handle':self,})
		self.hTC     = initmodule(importmodule("ToolChooser",True,{'path':'src'}),"ToolChooser",{'handle':self,})
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
		if tmp!="":
			# append to chat history
			self.Response('system',{'content':tmp,})
			# append to chat memory
			self.msgs.append( self.Response('system',{'content':tmp, 'return_object':True}) )
		# Choose actions
		self.hAC.Choose()
		# Choose history
		self.hHM.Choose()
		# Choose tools
		self.hTC.Choose()
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
	def One(self,data, opts=[]):
		self.hLG.echo("Handle.One() START, data.len: {}, opts: {}".format( len(data), opts ))
		opt_history_num  = opts['history_num'] if 'history_num' in opts else None
		opt_skip_history = opts['skip_history'] if 'skip_history' in opts else True
		msgs            = []
		#
		if opt_history_num!=None:
			# load specific history
			self.hHM.Available()
			self.hHM.history = self.hHM.available[opt_history_num]
			self.hHM.Get()
		#
		self.cmds.CMD_MEMORY_ALL_HISTORY()
		self.cmds.CMD_PREVIEW_MEMORY()
		self.cmds.CMD_PREVIEW_HISTORY()
		# Prepare messages
		for msg in self.msgs:
			msgs.append( msg )
		msgs.append( self.Response('user',{'content':data, 'return_object':True}) )
		# Fire request to AIIA
		#print("msgs: {}".format( msgs ))
		#
		res: ChatResponse = chat(
				self.Options['AI_MODEL'],
				messages=msgs,
				stream=True,
				#temperature=self.Options['AI_TEMPERATURE'],
				options={'temperature':self.Options['AI_TEMPERATURE']}
			)
		self.Parse(res, {'skip_history':opt_skip_history, 'skip_color':True})
	
	#
	def Chat(self):
		self.hLG.echo("Handle.Chat() STARTING!",{'color':True})
		#
		#self.lastMsgs = [] # clear lastMsgs
		#
		x = self.You() # return: 0, 1, 2=continue, 3=break
		#self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False,'debugOnly':False})
		self.hLG.echo("Handle.Chat() You() response: {}\n\n".format(x),{'color':False,})
		#
		if x!=None and x>=2:
			return x # return 2=continue or 3=break, 4=update handle
		
		#
		x = self.AI()
		self.hLG.echo("Handle.Chat() AI() response: {}".format(x),{'color':False})
		
		#
		self.Options['AI_ROW_ID'] = self.Options['AI_ROW_ID']+1
		return x
	
	#
	def You(self):
		# Prepare user content
		inp=""
		self.hLG.echo("You: ",{ 'end':'', 'flush':True, 'color':True, 'colorValue':'green', 'debugOnly':False, 'streamDone':True})
		try:
			inp = user_input({'quit_with_ctrlx':True})
		except Exception as E:
			print("Handle.You() Failed!",E)
			sys.exit(1)
		#
		if rmatch(inp,r"^\!.*"):
			cmds = self.cmds.cmds
			for k in cmds:
				if rmatch(inp,cmds[k]['regex']):
					return cmds[k]['func'](inp)
			print("no match, repeat..., debug({}): {}".format(len(inp),inp))
			return 2 # as continue
		#
		if len(inp)>self.Options['AI_MAX_CONTENT_LEN']:
			print("FAILED: content length {} / {}".format( len(inp), self.Options['AI_MAX_CONTENT_LEN'] ))
			return 2 # as continue
		
		#
		#self.lastMsgs = [] # clear lastMsgs
		
		# Append user content
		if inp != "":
			self.Response('user',{'content':inp})
			#self.lastMsgs.append( inp )
		return 0 # Input without command or successed command with input data
	
	#
	def Parse(self, res, opts={}):
		self.hLG.echo("Handle.Parse() START, lastMsgs.len: {}".format( len(self.lastMsgs) ))
		#
		opt_skip_history = opts['skip_history'] if 'skip_history' in opts else False
		opt_skip_color   = opts['skip_color'] if 'skip_color' in opts else False
		color            = True
		if opt_skip_color:
			color=False
		response         = ""
		#
		for chunk in res:
			part = chunk['message']['content']
			self.hLG.echo(part,{'color':color,'end':'','flush':True, 'debugOnly':False, 'echoByNewLine':True})
			response = response+part
		self.hLG.echo("\n",{'end':'','flush':True,'color':color,'streamDone':True,'debugOnly':False,'echoByNewLine':True})
		self.Response('assistant',{'content':response,'skip_history':opt_skip_history,})
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
	def AI(self):
		self.hLG.echo("Handle.AI() STARTING",{'color':False})
		res           = {}
		msgs          = [] # tempolary array of messages to send to AIIA
		self.lastMsgs = [] # clear lastMsgs
		
		#
		for msg in self.msgs: # loop trough array of history messages that you wish to include for AIIA
			msgs.append( msg )
			self.lastMsgs.append( msg )
		# append last user message
		if len(self.hHM.msgs)>0:
			msgs.append( self.hHM.msgs[ len(self.hHM.msgs)-1 ] )
			self.lastMsgs.append( self.hHM.msgs[ len(self.hHM.msgs)-1 ] )
		
		# Nothing to send to AIIA, continue to repeat input!
		if len(msgs)<=0:
			print("WARNING: msgs len is 0, Repeating user_input!")
			return 2 # as continue
		
		#
		if len(self.hTC.prepared)>0:
			self.hLG.echo("DEBUG preparing chat with tools, {}".format(self.hTC.prepared),{'color':False})
			res: ChatResponse = chat(
				self.Options['AI_MODEL'],
				messages=msgs,
				tools=self.hTC.prepared,
				#temperature=self.Options['AI_TEMPERATURE'],
				options={'temperature':self.Options['AI_TEMPERATURE']}
			)
			self.ParseTools(res)
		# Chat without tools, normal chat
		else:
			self.hLG.echo("DEBUG preparing chat without tools",{'color':False})
			res: ChatResponse = chat(
				self.Options['AI_MODEL'],
				messages=msgs,
				stream=True,
				#temperature=self.Options['AI_TEMPERATURE'],
				options={'temperature':self.Options['AI_TEMPERATURE']}
			)
			self.Parse(res)
	
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
				"ACTION_OPTIONS":{
					"name"       :"Action Options",
					"description":"LIST, SET, GET action options",
					"regex"      :r"^(!AO)|(!AO.[\d+])|(!AO.[\d+].SET.[a-z]\=[\"\/a-zA-Z0-9])|(!AO.[\d+].GET.[a-z])+$",
					"usage"      :"\nLIST Ex.: !AO [action_num]\nGET Ex.: !AO [action_num] GET path\n!SET Ex.: AO [action_num] SET path=/Memorize\n",
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
			for k in self.cmds:
				print("{} - {} Usage: {}".format( self.cmds[k]['name'], self.cmds[k]['description'], self.cmds[k]['usage'] ))
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


