import os,json
from src.functions import *
#
class HistoryManager():
	#
	def __init__(self,opts):
		#print("HistoryManager.__init__() START, DEBUG, opts: ",opts)
		self.handle    = opts.get('handle')
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
		#
		self.available = []
		#
		_hdir = self.handle.Options.get('history_path', "{}/history".format(self.handle.Options.get('path', '')))
		for tmp in os.listdir(_hdir):
			if rmatch(tmp,r"^[a-f0-9]+_\d+\..*") or rmatch(tmp,r"^\d+\..*"):
				self.available.append(tmp)
	
	# method get() - load chat history from a file (append to self.msgs)
	# If path is provided, loads from that exact file (e.g. HISTORY.md with embedded JSON comments).
	# Otherwise loads from the standard history/ file path.
	def Get(self, path=None):
		#
		self.msgs = []
		#
		if path:
			file_path = path
		else:
			_hdir = self.handle.Options.get('history_path', "{}/history".format(self.handle.Options.get('path', '')))
			file_path = "{}/{}".format(_hdir, self.history)
		#
		if not os.path.exists(file_path):
			return
		#
		with open(file_path) as tmp:
			for line in tmp:
				line = line.strip()
				if not line:
					continue
				# Parse JSON from HTML comment <!-- {...} -->
				if line.startswith('<!--') and line.endswith('-->'):
					json_str = line[4:-3].strip()
					try:
						self.msgs.append(json.loads(json_str))
					except Exception:
						continue
				# Also support plain JSON-lines (backward compat with .dbk files)
				elif line.startswith('{'):
					try:
						self.msgs.append(json.loads(line))
					except Exception:
						continue
	
	#
	def GetLast(self):
		self.history = self.available[ len(self.available)-1 ]
		self.Get()
		self.choosed = True
	
	#
	def CheckDraft(self):
		if self.handle.Options['DRAFT_CONTENT'] is not None:
			response = self.handle.Stream( self.handle.Options['DRAFT_CONTENT'] )
			self.handle.Options['DRAFT_CONTENT'] = None
	
	#
	def Available(self):
		#print("HistoryManager.Available() STARTED!")
		#
		self.Update()
		#
		self.available.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]), reverse=False)
		cnt=0
		for history in self.available:
			if self.opt_quiet==False:
				print("{}.) {}, len: {}".format( cnt, history, len(fread("{}/{}".format( self.handle.Options.get('history_path', "{}/history".format(self.handle.Options.get('path', ''))), history))) ))
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
			if tmp == 'x' or not tmp:
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				choosed = True
				break
			elif tmp and tmp[0] == 'v':
				print("Viewing history {}".format(tmp))
				a=tmp.split(" ")
				if len(a) > 1:
					print("Viewing history debug a[0]: {}, a[1]: {}".format(a[0],a[1]))
					tmpname = self.available[int(a[1])]
					print("Viewing history debug fileName: {}".format(tmpname))
					tmpdata = fread( "{}/{}".format( self.handle.Options.get('history_path', "{}/history".format(self.handle.Options.get('path', ''))), tmpname) )
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
	
	#
		
	
