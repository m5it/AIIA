import os
from src.functions import user_input, rmatch, importmodule, initmodule, splitFileNameExtension
#
class ToolChooser():
	#
	def __init__(self,opts):
		self.handle = opts['handle'] if 'handle' in opts else False
		self.handle.hLG.echo("ToolChooser.__init__() START",{'color':True})
		#
		self.choosed  = False
		self.available = []
		self.selected  = []
		#
		#self.imported  = {}
		self.handles   = {}
		self.prepared  = [] # used as argument for ChatResponse(...) for AI to know which tools are used.
	
	# preview available tools
	def Available(self):
		n=0
		for tool in os.listdir("{}/".format(self.handle.Options['tools_path'])):
			#print("file: {}".format(tool))
			if rmatch(tool,"tool\_.*"):
				self.available.append(tool)
		for tool in self.available:
			print("{}.) {}".format(n,tool))
			n=n+1
	
	#
	def Choose(self):
		self.handle.hLG.echo("Choose tools START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		self.selected  = []
		self.choosed   = False
		self.available = []
		#
		self.Available()
		#
		while self.choosed==False and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			n = user_input()
			#print("data: {}".format(n))
			if n=="x":
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				self.choosed = True
				break
			else:
				d = self.available[int(n)]
				#print("ToolChooser()->choose() appending {}".format( d ))
				# initmodule(importmodule("tool_List",True),"List")
				r = splitFileNameExtension(d)
				#print("ToolChooser.choose() r: {}".format( r ))
				self.selected.append( r['name'] )
		#--
		# Prepare tools
		for tmp in self.selected:
			a=tmp.split("_")
			h = initmodule(importmodule(tmp,True,{'path':self.handle.Options['tools_path']}),a[1])
			self.handles[h.info['name']] = { 'handle':h, }
			self.prepared.append( h.info )
			#self.Options['handle_tools'][h.info['name']] = {
			#	'handle':h,
			#}
			#self.Options['current_tools'].append( h.info )



