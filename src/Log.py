from src.functions import rmatch,initmodule,importmodule
class Log:
	#
	def __init__(self, opts={}):
		#print("Log().__init__() START!")
		# Serious variables
		self.debug      = opts['debug'] if 'debug' in opts else False
		self.handle     = opts['handle'] if 'handle' in opts else None
		# self.handle.Options... # To access global Options object
		self.speak      = self.handle.Options['SPEAK'] if 'SPEAK' in self.handle.Options else False # True | False
		#self.speak_args = self.handle.Options['speak_args'] if 'speak_args' in self.handle.Options else "" # -w -r 20...
		self.hSpeak     = None
		self.streamData = ""
		if self.speak:
			print("Log().__init__() DEBUG Loading speak module.")
			self.hSpeak = initmodule(importmodule("Speak",True,{'path':'src'}),"Speak")
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
		opt_returnStream    = opts['returnStream'] if 'returnStream' in opts else False
		opt_speak           = opts['speak'] if 'speak' in opts else False
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
			#
			tmpcolor = self.CRED
			if opt_colorValue!=None:
				if opt_colorValue=='green':
					tmpcolor = self.CGREEN
				if opt_colorValue=='orange':
					tmpcolor = self.CORANGE
			if opt_returnStream==False:
				if self.hSpeak!=None and opt_speak:
					#print("Log().echo() d1 len {}".format( len(self.streamData) ))
					self.hSpeak.Parse( self.streamData )
				print("{}{}{}{}".format( prefix, tmpcolor, self.streamData, self.CNC ),end=opt_end, flush=opt_flush)
		else:
			if opt_returnStream==False:
				if self.handle.opt_response_with != None:
					print("Log.echo() opt_response_with() START d3")
					self.handle.opt_response_with( self.streamData )
				else:
					#print("Log().echo() d2 len {}".format( len(self.streamData) ))
					print("{}{}".format( prefix, self.streamData ),end=opt_end, flush=opt_flush)
		#
		if opt_streamDone or wait==False:
			#
			if self.handle.opt_response_with != None:
				print("Log.echo() opt_response_with() START d1")
				self.handle.opt_response_with( self.streamData )
			if self.handle.opt_response_done != None:
				print("Log.echo() opt_response_done() START d1")
				self.handle.opt_response_done( self.streamData )
			#
			tmp=""
			if opt_returnStream:
				tmp = self.streamData
				self.streamData = ""
				return tmp
			self.streamData = ""
		return False
	
	#
	def Test(self):
		print("Log.Test() START!")
