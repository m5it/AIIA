import os
from src.functions import *
#
class InstructManager():
	def __init__(self, opts):
		self.handle = opts.get('handle')
		self.handle.hLG.echo("InstructManager.__init__() STARTED!",{'color':True})
		self.available = []
		self.choosed = False
	#
	def Update(self):
		self.available = []
		cls_path = self.handle.Options.get('INSTRUCT_PATH', 'instruct')
		base_path = self.handle.Options.get('path', '')
		instruct_dir = "{}{}".format(base_path, cls_path)
		if not os.path.isdir(instruct_dir):
			return
		for f in sorted(os.listdir(instruct_dir)):
			if f.endswith('.py') and f != '__init__.py':
				name = f[:-3]
				desc = ""
				mod = importmodule(name, False, {'path': cls_path})
				if mod and hasattr(mod, name):
					cls = getattr(mod, name)
					desc = getattr(cls, 'description', '')
				self.available.append({
					'class_name': name,
					'description': desc,
				})
	#
	def Available(self):
		self.Update()
		cnt = 0
		for p in self.available:
			print("{}) {} - {}".format(cnt, p['class_name'], p['description']))
			cnt = cnt + 1
	#
	def Exists(self, name):
		cls_path = self.handle.Options.get('INSTRUCT_PATH', 'instruct')
		base_path = self.handle.Options.get('path', '')
		instruct_dir = "{}{}".format(base_path, cls_path)
		filepath = "{}/{}.py".format(instruct_dir, name)
		return os.path.isfile(filepath)
	#
	def Choose(self):
		if self.handle.Options.get('INSTRUCT_CLASS_OVERRIDE', False):
			self.handle.hLG.echo("Persona set via -p: {}".format(self.handle.Options['INSTRUCT_CLASS']),{'color':True,'colorValue':'green','debugOnly':False})
			self.ApplyPersonaModel(self.handle.Options['INSTRUCT_CLASS'])
			self.choosed = True
			return
		self.handle.hLG.echo("Choose persona START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		self.available = []
		self.choosed = False
		self.Available()
		while not self.choosed and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input()
			if tmp == 'x' or not tmp:
				self.handle.hLG.echo("Canceling persona selection...",{'color':True,'colorValue':'red','debugOnly':False})
				self.choosed = True
				break
			try:
				choice = int(tmp)
				if choice < 0 or choice >= len(self.available):
					print("Invalid number, try again")
					continue
				cls_name = self.available[choice]['class_name']
				self.handle.Options['INSTRUCT_CLASS'] = cls_name
				self.handle.hLG.echo("Chosen persona: {}".format(cls_name),{'color':True,'colorValue':'green'})
				self.ApplyPersonaModel(cls_name)
				self.choosed = True
			except ValueError:
				print("Invalid input, enter a number or x to cancel")
			except Exception as E:
				print("Choosing persona failed, error: {}".format(E))
	#
	def ApplyPersonaModel(self, name):
		cls_path = self.handle.Options.get('INSTRUCT_PATH', 'instruct')
		mod = importmodule(name, False, {'path': cls_path})
		if not mod:
			return
		cls = None
		for n in [name, name.lower(), name.upper()]:
			try:
				cls = getattr(mod, n)
				if cls:
					break
			except Exception:
				continue
		if not cls:
			return
		model = getattr(cls, 'model', None)
		if model and isinstance(model, str) and model.strip():
			old = self.handle.Options.get('AI_MODEL', '')
			self.handle.Options['AI_MODEL'] = model.strip()
			self.handle.hLG.echo("Persona '{}' sets model: {} (was: {})".format(name, model.strip(), old), {'color':True, 'colorValue':'cyan'})
		# Read optional build_thinking_disabled attribute
		thinking_attr = getattr(cls, 'build_thinking_disabled', None)
		if thinking_attr is not None:
			self.handle.Options['BUILD_THINKING_DISABLED'] = bool(thinking_attr)
			self.handle.hLG.echo("Persona '{}' sets build_thinking_disabled: {}".format(name, bool(thinking_attr)), {'color':True, 'colorValue':'cyan'})
		# Read optional max_iterations attribute
		max_iter = getattr(cls, 'max_iterations', None)
		if max_iter is not None:
			self.handle.Options['AI_MAX_ITERATIONS'] = int(max_iter)
			self.handle.hLG.echo("Persona '{}' sets max_iterations: {}".format(name, int(max_iter)), {'color':True, 'colorValue':'cyan'})
		# Read optional mode attribute
		mode = getattr(cls, 'mode', None)
		if mode is not None:
			self.handle.Options['MODE'] = str(mode)
			self.handle.hLG.echo("Persona '{}' sets mode: {}".format(name, str(mode)), {'color':True, 'colorValue':'cyan'})
		# Apply model registry (context limit, num_ctx, vision, think)
		model_name = self.handle.Options.get('AI_MODEL', '')
		if model_name:
			from src.ModelRegistry import apply as apply_registry
			reg_changes = apply_registry(self.handle.Options, model_name)
			if reg_changes:
				for c in reg_changes:
					self.handle.hLG.echo("  Model config: {}".format(c),
						{'color':True, 'colorValue':'cyan'})
		# Check persona dependencies
		if self.handle.Options.get('PERSONA_AUTO_INSTALL_DEPS', True):
			self._check_persona_deps(name, cls)
	#
	def _check_persona_deps(self, name, cls):
		"""Check if persona has dependency requirements and prompt user."""
		requirements = getattr(cls, 'requirements', None)
		if not requirements:
			return
		try:
			req_dict = requirements(self)
		except Exception:
			return
		if not req_dict:
			return
		from src.DependencyChecker import check as check_deps
		status = check_deps(name, req_dict)
		if status['all_installed']:
			self.handle.hLG.echo("Persona '{}' dependencies already satisfied.".format(name),
				{'color':True, 'colorValue':'green','debugOnly':False})
			return
		# Show summary and prompt
		lines = ["Persona '{}' requires additional dependencies:".format(name)]
		pip_missing = status.get('pip_missing', [])
		hf_missing = status.get('hf_missing', [])
		if pip_missing:
			lines.append("  pip packages ({}): {}".format(len(pip_missing), ', '.join(pip_missing)))
		if hf_missing:
			lines.append("  HF models ({}): {}".format(len(hf_missing), ', '.join(hf_missing)))
		size = req_dict.get('size_gb', '?')
		lines.append("  Estimated total: ~{} GB".format(size))
		note = req_dict.get('note', '')
		if note:
			lines.append("  Note: {}".format(note))
		lines.append("Install now? [Y]es / [N]o / [D]etails")
		self.handle.hLG.echo("\n".join(lines),
			{'color':True, 'colorValue':'yellow','debugOnly':False})
		ans = user_input().strip().lower()
		if ans == 'd':
			self.handle.hLG.echo("Missing packages: {}".format(', '.join(pip_missing + hf_missing)),
				{'color':True, 'colorValue':'cyan','debugOnly':False})
			self.handle.hLG.echo("Install now? [Y]es / [N]o: ",
				{'end':'','flush':True,'color':True,'colorValue':'yellow','debugOnly':False})
			ans = user_input().strip().lower()
		if ans in ('y', 'yes'):
			self.handle.hLG.echo("Installing dependencies for '{}'... This may take a while.".format(name),
				{'color':True, 'colorValue':'cyan','debugOnly':False})
			from src.DependencyInstaller import install as install_deps
			ok = install_deps(name, req_dict, self.handle)
			if ok:
				self.handle.hLG.echo("All dependencies installed for '{}'.".format(name),
					{'color':True, 'colorValue':'green','debugOnly':False})
			else:
				self.handle.hLG.echo("Some dependencies failed for '{}'. Run !INSTALL_DEPS {} to retry.".format(name, name),
					{'color':True, 'colorValue':'orange','debugOnly':False})
		else:
			self.handle.hLG.echo("Skipping dependency installation for '{}'.".format(name),
				{'color':True, 'colorValue':'yellow','debugOnly':False})
	#
	#
		
