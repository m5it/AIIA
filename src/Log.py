from src.functions import rmatch,initmodule,importmodule
import re, datetime, os
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
		self.CGRAY      = '\033[90m'   # GRAY
		self.CNC        = '\033[0m'

	def _log_background(self, text):
		if not self.handle:
			return
		log_path = self.handle.Options.get('BACKGROUND_LOG')
		if not log_path:
			return
		clean = re.sub(r'\033\[[0-9;]*m', '', text)
		if not clean.strip():
			return
		ts = datetime.datetime.now().strftime('%H:%M:%S')
		try:
			with open(log_path, 'a') as f:
				f.write("[{}] {}\n".format(ts, clean))
		except:
			pass
	
	#
	def echo(self,text,opts={}):
		o = self._echo_opts(opts)
		if o['debugOnly'] and self.debug==False:
			#print("Log.echo() DEBUG D2, streamData.len: {}".format( len(self.streamData) ))
			return False
		wait = self._echo_accumulate(text, o)
		if wait:
			#print("Log.echo() DEBUG D1, streamData.len: {}".format( len(self.streamData) ))
			return False
		prefix = ""
		if self.debug or o['debugOnly']:
			prefix = "DEBUG "
		self._echo_print(prefix, o)
		return self._echo_finish(o, wait,
			o['echoByNewLine'] or (o['echoByLength']!=False and o['echoByLength']>0))

	#

	def _echo_opts(self, opts):
		return {
			'end'           : opts['end'] if 'end' in opts else '\r\n',
			'flush'         : opts['flush'] if 'flush' in opts else False,
			'color'         : opts['color'] if 'color' in opts else False,
			'colorValue'    : opts['colorValue'] if 'colorValue' in opts else None,
			'debugOnly'     : opts['debugOnly'] if 'debugOnly' in opts else True,
			'echoByNewLine' : opts['echoByNewLine'] if 'echoByNewLine' in opts else False,
			'echoByLength'  : opts['echoByLength'] if 'echoByLength' in opts else False,
			'streamDone'    : opts['streamDone'] if 'streamDone' in opts else False,
			'returnStream'  : opts['returnStream'] if 'returnStream' in opts else False,
			'speak'         : opts['speak'] if 'speak' in opts else False,
		}

	#

	def _echo_accumulate(self, text, o):
		"""Accumulate text into the stream buffer. Returns True when we
		should keep waiting (streaming), False when ready to emit."""
		if o['streamDone']:
			self.streamData = self.streamData+text
			return False
		elif o['echoByNewLine']:
			self.streamData = self.streamData+text
			if rmatch(self.streamData,"\n") or rmatch(self.streamData,".*\n") or rmatch(self.streamData,".*\n.*"):
				return False
		elif o['echoByLength']!=False and o['echoByLength']>0:
			self.streamData = self.streamData+text
			if len(self.streamData)>=o['echoByLength']:
				return False
		else:
			self.streamData = self.streamData+text
			return False
		return True

	#

	def _echo_print(self, prefix, o):
		if o['color']:
			#
			tmpcolor = self.CRED
			if o['colorValue']!=None:
				if o['colorValue']=='green':
					tmpcolor = self.CGREEN
				if o['colorValue']=='orange':
					tmpcolor = self.CORANGE
				if o['colorValue']=='gray':
					tmpcolor = self.CGRAY
			if o['returnStream']==False:
				if self.hSpeak!=None and o['speak']:
					#print("Log().echo() d1 len {}".format( len(self.streamData) ))
					self.hSpeak.Parse( self.streamData )
				print("{}{}{}{}".format( prefix, tmpcolor, self.streamData, self.CNC ),end=o['end'], flush=o['flush'])
		else:
			if o['returnStream']==False:
				if self.handle.opt_response_with != None:
					print("Log.echo() opt_response_with() START d3")
					self.handle.opt_response_with( self.streamData )
				else:
					#print("Log().echo() d2 len {}".format( len(self.streamData) ))
					print("{}{}".format( prefix, self.streamData ),end=o['end'], flush=o['flush'])

	#

	def _echo_finish(self, o, wait, is_streaming):
		if o['streamDone'] or wait==False:
			#
			if self.handle.opt_response_with != None:
				print("Log.echo() opt_response_with() START d1")
				self.handle.opt_response_with( self.streamData )
			if self.handle.opt_response_done != None:
				print("Log.echo() opt_response_done() START d1")
				self.handle.opt_response_done( self.streamData )
			#
			tmp=""
			if o['returnStream']:
				tmp = self.streamData
				self.streamData = ""
				return tmp
			if not is_streaming:
				self._log_background(self.streamData)
			self.streamData = ""
		return False

	#
	def Test(self):
		print("Log.Test() START!")