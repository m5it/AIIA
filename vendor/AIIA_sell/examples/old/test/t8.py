#!/usr/bin/python
#
# Scrap html speak, break.. blocks
#--
import os,re, subprocess
#
def pmatch(input,regex):
	ret=[]
	#a = re.findall( regex, input, flags=re.IGNORECASE|re.DOTALL )
	a = re.findall( regex, input, flags=re.IGNORECASE )
	if a is not None:
		if type(a) is list and len(a)>0 and type(a[0]) is tuple:
			a = a[0]
		for v in a:
			ret.append( v )
	return ret
#--
#
in_speak     = False
speak_data   = []
#
"""tmp = 'hello, world\n\
abcdef\n\
<speak>This should be. \n\
Lets add new line...\n\
Is good spoken?</speak>\n\
more text...\n\
<speak>Another test.</speak>\
done.'"""
tmp="<speak>Hello, World.</speak>"
print("tmp: ",tmp)

#
def Speak(text: str):
	global speak_data
	"""Send a string to the system TTS."""
	print("speak() START, text: {}".format(text))
	subprocess.run(['spd-say', "-y \"English (Received Pronunciation)+Annie\" -m all -r \"-20\" -R \"20\" -p \"20\"", text])
	#subprocess.run(['spd-say', text, "-r -20 -p -20 -R 20 -l 'en-US-NYC+Eva'"])
	#subprocess.run(['spd-say', text,])
	speak_data=[]
#
def Parse( line ):
	global speak_data, in_speak
	#
	tmp1 = pmatch(line,"<speak>(.*)")
	tmp2 = pmatch(line,"(.*)<.speak>")
	#
	if len(tmp1):
		b = pmatch(tmp1[0],"(.*)<.speak>")
		if len(b)>0:
			if len(speak_data):
				speak_data.append( "\n" )
			speak_data.append( b[0] )
			# can be fired speak
			#...
			Speak(Gen())
		else:
			speak_data.append( tmp1[0] )
			in_speak = True
		
	#
	elif len(tmp2) and in_speak:
		speak_data.append( tmp2[0] )
		in_speak = False
		# can be fired speak
		#...
		#Speak(Gen())
	#
	else:
		if in_speak:
			speak_data.append(line)
#
def Gen():
	global speak_data
	tmp=""
	# Option 1, speak line by line
	for data in speak_data:
		if data=="":
			tmp+="\n"
		#print("data2tmp: ",data)
		tmp+=data
	return tmp
#--
#
a = pmatch(tmp,".*")
for l in a:
	Parse( l )
#--
# Start speaking here. ( Fire speak at end of all data... )
#Speak( Gen() )
