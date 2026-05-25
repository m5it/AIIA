import os,json
from src.functions import *
#
class HistoryManager():
	#
	def __init__(self,opts):
		#print("HistoryManager.__init__() START, DEBUG, opts: ",opts)
		self.handle    = opts['handle'] if 'handle' in opts else False
		self.opt_quiet = opts['quiet'] if 'quiet' in opts else False
		self.opt_path  = opts['path'] if 'path' in opts else self.handle.Options['history_path']
		self.handle.hLG.echo("HistoryManager.__init__() STARTED!",{'color':True})
		
		self.history   = "" # name of choosed history file
		self.available = []
		self.msgs      = []
		# count tokens
		self.token_prompt   = 0
		self.token_response = 0
	
	# update self.available (list history files)
	def Update(self):
		print("HistoryManager.Update() opt_path: {}".format( self.opt_path ))
		#
		self.available = []
		#
		for tmp in os.listdir("{}/history/".format( self.opt_path )):
			if rmatch(tmp,"^\d+\..*"):
				self.available.append(tmp)
	
	# method get() - load chat history from history/ some file (append to self.msgs)
	def Get(self):
		#
		self.msgs = []
		#
		if os.path.exists( "{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], self.history )):
			with open ( "{}{}/{}".format( self.opt_path, self.handle.Options['history_path'], self.history) ) as tmp:
				for line in tmp:
					line = line.strip()
					if line=="" or line==None or line=="\n":
						continue
					self.msgs.append( json.loads(line) )
	
	#
	def GetLast(self):
		self.history = self.available[ len(self.available)-1 ]
		self.Get()
		self.choosed = True
	
	#
	def CheckDraft(self):
		if self.handle.Options['DRAFT_CONTENT'] is not None:
			print("HistoryManager.CheckDraft() Appending to chat history! draft.len: ",len(self.handle.Options['DRAFT_CONTENT']))
			response = self.handle.Stream( self.handle.Options['DRAFT_CONTENT'] )
			print("DEBUG HistoryManager.CheckDraft() ",response)
			self.handle.Options['DRAFT_CONTENT'] = None
	
	#
	def Available(self):
		#print("HistoryManager.Available() STARTED!")
		#
		self.Update()
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
		choosed = False
		self.available    = []
		#
		self.Available()
		#
		while choosed==False and len(self.available):
			self.handle.hLG.echo("Choose available number (x to cancel): ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input()
			if tmp == 'x':
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				choosed = True
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
				choosed = True
			except Exception as E:
				print("Choosing history failed, error: {}".format(E))
	
	# this is ok for any class.. it is just a test! *** love it or remove it.
	def test(self):
		print("HistoryManager.test() STARTED!")
	
