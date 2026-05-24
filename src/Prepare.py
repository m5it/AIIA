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
		print("DEBUG Prepare.Prepare() mode: ",mode)
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
	
	#
	def _get_mode_instructions(self, mode):
		if mode == 'plan':
			return self.handle.Options['MODE_INSTRUCTIONS_PLAN']
		else:  # build mode
			return self.handle.Options['MODE_INSTRUCTIONS_BUILD']

