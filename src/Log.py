from src.functions import rmatch
class Log:
	#
	def __init__(self, opts={}):
		#print("Log.__init__() START!")
		# Serious variables
		self.debug      = opts['debug'] if 'debug' in opts else False
		self.streamData = ""
		# Color variables
		# Black        0;30     Dark Gray     1;30
		# Red          0;31     Light Red     1;31
		# Green        0;32     Light Green   1;32
		# Brown/Orange 0;33     Yellow        1;33
		# Blue         0;34     Light Blue    1;34
		# Purple       0;35     Light Purple  1;35
		# Cyan         0;36     Light Cyan    1;36
		# Light Gray   0;37     White         1;37
		#self.CRED = '\033[0;31m' # RED DARK
		self.CORANGE    = '\033[1;33m'
		self.CGREEN     = '\033[1;32m' # GREEN
		self.CRED       = '\033[1;31m' # RED
		self.CNC        = '\033[0m'
	
	#
	def echo(self,text,opts={}):
		#print("Log.echo() START DEBUG opts",opts)
		wait                = True
		opt_end             = opts['end'] if 'end' in opts else '\r\n'
		opt_flush           = opts['flush'] if 'flush' in opts else False
		opt_color           = opts['color'] if 'color' in opts else False # True or False
		opt_colorValue      = opts['colorValue'] if 'colorValue' in opts else None # True or False
		opt_debugOnly       = opts['debugOnly'] if 'debugOnly' in opts else True
		opt_echoByNewLine   = opts['echoByNewLine'] if 'echoByNewLine' in opts else False
		opt_echoByLength    = opts['echoByLength'] if 'echoByLength' in opts else False
		opt_streamDone      = opts['streamDone'] if 'streamDone' in opts else False
		#
		if opt_debugOnly and self.debug==False:
			#print("Log.echo() DEBUG D2, streamData.len: {}".format( len(self.streamData) ))
			return False
		#--
		#
		if opt_streamDone:
			self.streamData = self.streamData+text
			wait = False
		elif opt_echoByNewLine:
			self.streamData = self.streamData+text
			if rmatch(self.streamData,"\n") or rmatch(self.streamData,".*\n") or rmatch(self.streamData,".*\n.*"):
				wait = False
		elif opt_echoByLength!=False and opt_echoByLength>0:
			self.streamData = self.streamData+text
			if len(self.streamData)>=opt_echoByLength:
				wait = False
		else:
			self.streamData = self.streamData+text
			wait = False
		#--
		#
		if wait:
			#print("Log.echo() DEBUG D1, streamData.len: {}".format( len(self.streamData) ))
			return False
		#--
		prefix=""
		if self.debug or opt_debugOnly:
			prefix = "DEBUG "
		#
		if opt_color:
			#print("Log.echo() DEBUG D4, streamData.len: {}".format( len(self.streamData) ))
			tmpcolor = self.CRED
			if opt_colorValue!=None:
				if opt_colorValue=='green':
					tmpcolor = self.CGREEN
				if opt_colorValue=='orange':
					tmpcolor = self.CORANGE
			print("{}{}{}{}".format( prefix, tmpcolor, self.streamData, self.CNC ),end=opt_end, flush=opt_flush)
		else:
			#print("Log.echo() DEBUG D5, streamData.len: {}".format( len(self.streamData) ))
			print("{}{}".format( prefix, self.streamData ),end=opt_end, flush=opt_flush)
		if opt_streamDone or wait==False:
			#print("Log.echo() DEBUG D3, streamData.len: {}".format( len(self.streamData) ))
			self.streamData = ""
		return False
	
	#
	def Test(self):
		print("Log.Test() START!")
