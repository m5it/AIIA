import os
from src.functions import *
#
class InstructManager():
	def __init__(self, opts):
		self.handle = opts['handle'] if 'handle' in opts else False
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
	def Choose(self):
		if self.handle.Options.get('INSTRUCT_CLASS_OVERRIDE', False):
			self.handle.hLG.echo("Persona set via -p: {}".format(self.handle.Options['INSTRUCT_CLASS']),{'color':True,'colorValue':'green','debugOnly':False})
			self.choosed = True
			return
		self.handle.hLG.echo("Choose persona START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		self.available = []
		self.choosed = False
		self.Available()
		while not self.choosed and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input()
			if tmp == 'x':
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
				self.choosed = True
			except ValueError:
				print("Invalid input, enter a number or x to cancel")
			except Exception as E:
				print("Choosing persona failed, error: {}".format(E))
	#
	def test(self):
		print("InstructManager.test() STARTED!")
