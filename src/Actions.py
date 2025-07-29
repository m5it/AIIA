import os,json
from src.functions import user_input, rmatch, importmodule, initmodule, splitFileNameExtension
#
class Actions():
	#
	def __init__(self,opts):
		self.handle = opts['handle'] if 'handle' in opts else False
		self.handle.hLG.echo("Actions.init() START",{'color':True})
		#
		self.available = []
		self.choosed   = False
		self.imported  = {}
	#
	def Available(self):
		n=0
		for tmp in os.listdir("{}/".format(self.handle.Options['actions_path'])):
			if rmatch(tmp,r"^[a-zA-Z].*"):
				self.available.append(tmp)
		for tmp in self.available:
			print("{}.) {}".format(n,tmp))
			n=n+1
	#
	def Choose(self):
		self.handle.hLG.echo("Choose actions START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		self.choosed   = False
		self.available = []
		#
		self.Available()
		#
		while self.choosed==False and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			n = user_input()
			if n=="x":
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				self.choosed = True
				#break
				return False
			else:
				d = self.available[int(n)]
				self.handle.hLG.echo("Actions.Choose() appending {}".format( d ))
				r = splitFileNameExtension(d)
				# DEBUG r: {'name': 'grandekos_createpage', 'extension': 'py'}
				self.handle.hLG.echo("Actions.Choose() r: {}".format( r ))
				# initmodule(importmodule("grandekos_createpage",True),"Action")
				# Check if already imported
				if r['name'] in self.imported:
					return False
				#
				h = initmodule(importmodule("{}.{}".format(self.handle.Options['actions_path'], r['name']),True),"Action",{'handle':self.handle,})
				#
				self.imported[int(n)] = {
					'name'     :r['name'],
					'extension':r['extension'],
					'handle'   :h,
					# Arguments that handle.Exec( args ) accept.
					#'args'     :None,
				}
				#
				#h.Test()
				#return True # Instead continue until `x` is pressed!
		return False

