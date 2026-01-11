from src.functions import pmatch
import subprocess
#
class Speak:
	def __init__(self):
		print("Speak() START!")
		#
		self.in_block = False
		self.data     = []
		self.spd_args = "-y \"English (Received Pronunciation)+Annie\" -m all -r \"-20\" -R \"20\" -p \"20\""
	#
	def Speak(self,text: str):
		"""Send a string to the system TTS."""
		print("speak() START, text: {}".format(text))
		subprocess.run(['spd-say', self.spd_args, text])
		self.data=[]
	#
	def Parse( self, line ):
		#
		tmp1 = pmatch(line,"<speak>(.*)")
		tmp2 = pmatch(line,"(.*)<.speak>")
		#
		if len(tmp1):
			b = pmatch(tmp1[0],"(.*)<.speak>")
			if len(b)>0:
				if len(self.data):
					self.data.append( "\n" )
				self.data.append( b[0] )
				#... Fire speak
				self.Speak(self.Gen())
			else:
				self.data.append( tmp1[0] )
				self.in_block = True
			
		#
		elif len(tmp2) and self.in_block:
			self.data.append( tmp2[0] )
			self.in_block = False
		#
		else:
			if self.in_block:
				self.data.append(line)
	#
	def Gen(self):
		tmp=""
		# Option 1, speak line by line
		for data in self.data:
			if data=="":
				tmp+="\n"
			#print("data2tmp: ",data)
			tmp+=data
		return tmp
