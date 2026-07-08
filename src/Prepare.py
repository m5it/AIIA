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
		# Apply model registry (even if no persona was chosen — covers default model)
		from src.ModelRegistry import apply as apply_registry
		_model = self.handle.Options.get('AI_MODEL', '')
		if _model:
			_changes = apply_registry(self.handle.Options, _model)
			if _changes:
				for _c in _changes:
					self.handle.hLG.echo("  Model config: {}".format(_c),
						{'color':True, 'colorValue':'cyan'})
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
	def _save_instruction_tip(self, cls, cls_name):
		"""Save persona's plan() and build() as a tip for AI_INSTRUCT_OPTION=2.

		Splits build() at 'AVAILABLE TOOLS' into two tips:
		- instruct_{name}:       workflow rules only (small, loaded via ReinsertTip)
		- tool_reference_build:  detailed tool docs (larger, loaded on demand)
		"""
		base_title = "instruct_{}".format(cls_name.lower())
		plan_text = cls.plan() if hasattr(cls, 'plan') else ""
		build_text = cls.build() if hasattr(cls, 'build') else ""
		# Split build text at "AVAILABLE TOOLS" marker
		tool_marker = "\nAVAILABLE TOOLS"
		split_pos = build_text.find(tool_marker)
		if split_pos != -1:
			build_workflow = build_text[:split_pos]
			build_tools = build_text[split_pos:]
		else:
			build_workflow = build_text
			build_tools = ""
		# Main tip: workflow-only instructions
		entries = []
		if plan_text:
			entries.append({'role': 'model', 'content': "[PLAN MODE INSTRUCTIONS]\n" + plan_text})
		if build_workflow:
			entries.append({'role': 'model', 'content': "[BUILD MODE INSTRUCTIONS]\n" + build_workflow})
		if self.handle and hasattr(self.handle, 'hTM'):
			self.handle.hTM.delete(base_title, 'model')
			self.handle.hTM.save(base_title, 'model', entries)
		# Secondary tip: tool reference docs (on-demand)
		if build_tools:
			tool_tip_title = "tool_reference_build"
			tool_entries = [{'role': 'model', 'content': "[BUILD MODE TOOL REFERENCE]\n" + build_tools}]
			if build_text:
				tool_entries.append({'role': 'model', 'content': "[BUILD MODE WORKFLOW EXAMPLE]\n" + build_text})
			self.handle.hTM.delete(tool_tip_title, 'model')
			self.handle.hTM.save(tool_tip_title, 'model', tool_entries)
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
		# Option 2: short prompt + tips
		if self.handle.Options.get('AI_INSTRUCT_OPTION', 1) == 2:
			self._save_instruction_tip(cls, cls_name)
			base_title = "instruct_{}".format(cls_name.lower())
			return (
				"Your role: {}\n\n"
				"Your core instructions are stored as a tip.\n"
				"Use <GetTip> {} or <ReinsertTip> {} to load them.\n"
				"The tip contains separate entries for plan and build mode.\n"
				"Detailed tool reference docs are in a separate tip:\n"
				"  <GetTip> tool_reference_build</GetTip>\n"
				"  <ReinsertTip> tool_reference_build</ReinsertTip>"
			).format(
				getattr(cls, 'description', cls_name),
				base_title, base_title
			)
		# Option 1: full persona class instructions (default)
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

