import os, json
from src.functions import fread,fwrite,user_input,importmodule,initmodule
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
		fwrite(self.handle.Options['AI_FILE_SESSID'],self.handle.Options['AI_SESS_ID'],True)
	
	#
	def UpdateFileNames(self):
		self.handle.hLG.echo("Prepare.UpdateFileNames() START")
		# generate history file name depend on session and system message
		if self.handle.Options['AI_FILE_LOAD_HISTORY']==False:
			self.handle.Options['AI_FILE_HISTORY'] = "{}.dbk".format(self.handle.Options['AI_SESS_ID'])
			self.handle.Options['AI_USER_HISTORY'] = "{}.user.dbk".format(self.handle.Options['AI_SESS_ID'])
			#self.handle.hHM.history = self.handle.Options['AI_FILE_HISTORY']
		else:
			self.handle.hLG.echo("Loading existing history: {}".format(self.handle.Options['AI_FILE_HISTORY']),{'color':False})
	
	#
	def SaveMemory(self):
		self.handle.hLG.echo("Prepare.SaveMemory() START, length: {}. history: {}".format( len(self.handle.hHM.msgs), self.handle.hHM.history ),{'color':False})
		#
		history_path = "{}/history/{}".format(self.handle.Options.get('path', ''), self.handle.Options['AI_USER_HISTORY'])
		if os.path.exists(history_path):
			os.remove(history_path)
		# write history here
		for obj in self.handle.hHM.msgs:
			fwrite(history_path,"{}\n".format(json.dumps(obj)),False)
	
	#
	def Prepare(self):
		self.handle.hLG.echo("Prepare.Prepare() START, MODE: {}".format(self.handle.Options.get('MODE', 'build')))
		#
		if self.handle.Options.get('CONTINUING'):
			self.handle.hLG.echo("Continuing previous session (history loaded from HISTORY.md)", {'color':True, 'colorValue':'cyan'})
			return True
		#
		# Choose persona
		self.handle.hIM.Choose()
		#
		mode = self.handle.Options.get('MODE', 'build')
		tool_instructions = self._get_mode_instructions(mode)
		#
		quick = self.handle.Options.get('AI_QUICK', False) or not self.handle.Options.get('AI_LIVE', True)
		if quick:
			# Non-interactive: use persona instructions + optional --prompt prefix
			custom = self.handle.Options.get('AI_SYSTEM_MESSAGE', '')
			if custom:
				system_content = "{}\n\n{}".format(custom, tool_instructions)
			else:
				system_content = tool_instructions
			self.handle.Response('system', {'content': system_content})
			self.handle.hLG.echo("Quick mode — persona loaded, system message set", {'color':True, 'colorValue':'cyan'})
		else:
			# Interactive: prompt for custom system message prefix
			self.handle.hLG.echo("Set system message ( CTRL+x ENTER to Finish. ): ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input({'quit_with_ctrlx':True})
			if tmp!="":
				system_content = "{}\n\n{}".format(tmp, tool_instructions)
			else:
				system_content = tool_instructions
			self.handle.Response('system',{'content':system_content,})
			# Choose history
			self.handle.hHM.Choose()
		# Tools will be loaded dynamically when model invokes them via XML
		return True
	
	#
	def _get_mode_instructions(self, mode):
		cls_name = self.handle.Options.get('INSTRUCT_CLASS', 'Developer')
		cls_path = self.handle.Options.get('INSTRUCT_PATH', 'instruct')
		mod = importmodule(cls_name, True, {'path': cls_path})
		if not mod:
			return "Error: instruct class {} not found in {}".format(cls_name, cls_path)
		cls = None
		for n in [cls_name, cls_name.lower(), cls_name.upper()]:
			try:
				cls = initmodule(mod, n)
				if cls:
					break
			except Exception:
				continue
		if not cls:
			return "Error: could not initialize instruct class {}".format(cls_name)
		if mode == 'plan':
			text = cls.plan()
		else:
			text = cls.build()
		# Replace block placeholders from persona's blocks dict
		blocks = getattr(cls, 'blocks', {})
		if blocks:
			disabled = self.handle.Options.get('BUILD_THINKING_DISABLED', True) if mode != 'plan' else False
			for block_id, replacements in blocks.items():
				if mode == 'plan':
					val = replacements.get('plan', '')
				else:
					val = replacements.get('build_disabled', '') if disabled else replacements.get('build_enabled', '')
				text = text.replace(block_id, val)
		return text

