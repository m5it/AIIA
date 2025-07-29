import os,json
from src.functions import *
#
class HistoryManager():
	#
	def __init__(self,opts):
		#print("HistoryManager.__init__() START, DEBUG, opts: ",opts)
		self.handle    = opts['handle'] if 'handle' in opts else False
		self.opt_quiet = opts['quiet'] if 'quiet' in opts else False
		self.opt_path  = opts['path'] if 'path' in opts else ""
		self.handle.hLG.echo("HistoryManager.__init__() STARTED!",{'color':True})
		
		self.choosed   = False
		self.history   = "" # name of choosed history file
		self.available = []
		self.msgs      = []
	
	# method get() - load chat history from history/ some file 
	def Get(self):
		#print("HistoryManager.get() START on history: {}".format( self.history ))
		#
		self.msgs = []
		#
		#if os.path.exists( "{}/{}".format( self.handle.Options['history_path'], self.history )):
		if os.path.exists( "{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], self.history )):
		#	print("HistoryManager.get() loading history from: {}".format( self.history ))
			with open ( "{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], self.history) ) as tmp:
				for line in tmp:
					line = line.strip()
					if line=="" or line==None or line=="\n":
						continue
		#			print("HistoryManager.get() Loading history line: {}".format(line))
					self.msgs.append( json.loads(line) )
	#
	def Available(self):
		#print("HistoryManager.Available() STARTED!")
		#
		for tmp in os.listdir("{}{}/".format( self.opt_path, self.handle.Options['history_path'])):
			if rmatch(tmp,"^\d+\..*"):
				self.available.append(tmp)
		#
		self.available.sort(key=lambda x: int(x.split('.')[0]), reverse=False)
		cnt=0
		for history in self.available:
			if self.opt_quiet==False:
				print("{}.) {}, len: {}".format( cnt, history, len(fread("{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], history))) ))
			cnt = cnt+1
	
	#
	def Choose(self):
		self.handle.hLG.echo("Choose history START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		self.choosed = False
		self.available    = []
		#
		self.Available()
		#
		while self.choosed==False and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input()
			if tmp == 'x':
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				self.choosed = True
				break
			elif tmp[0] == 'v':
				print("Viewing history {}".format(tmp))
				a=tmp.split(" ")
				print("Viewing history debug a[0]: {}, a[1]: {}".format(a[0],a[1]))
				tmpname = self.available[int(a[1])]
				print("Viewing history debug fileName: {}".format(tmpname))
				tmpdata = fread( "{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], tmpname) )
				print("Viewing history debug tmpdata len: {}".format( len(tmpdata) ))
				print(tmpdata)
			try:
				print("Loading history, debug number: {}".format(tmp))
				self.history = self.available[int(tmp)] # filename for history
				print("Loading history, loading file: {}".format(self.history))
				self.Get()
				print("Loading history, self.msgs.len: {}".format( len(self.msgs) ))
				self.choosed = True
			except Exception as E:
				print("Choosing history failed, error: {}".format(E))
	
	# this is ok for any class.. it is just a test! *** love it or remove it.
	def test(self):
		print("HistoryManager.test() STARTED!")
	
