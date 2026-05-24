#from ollama import chat
import ollama
import select
import json, sys, time, os
import signal
from functions import *
#res = ollama.generate(model='llama3.2', prompt='Show me example for hello world app in python.')
#print("ollama response: {}".format( res ))

#
AI_MODEL        = 'llama3.2'
AI_SESS_ID      = 0
AI_FILE_HISTORY = 'history.aiia'
AI_FILE_SESSID  = 'sessid.aiia'
AI_RUNNING      = False
#--
def signal_handler(sig, frame):
	#global AI_SESS_ID, AI_FILE_SESSID
	#print("OurAIIA is quiting with sessionId: {}".format( AI_SESS_ID ))
	#fwrite(AI_FILE_SESSID,AI_SESS_ID,True)
	print("Ctrl-D to Quit!")
	print("You: ", end='', flush=True)
#
signal.signal(signal.SIGINT, signal_handler)

#
def response_object(role='user',opts=[]):
	global AI_SESS_ID, AI_FILE_HISTORY
	# generate response object
	obj = {
		'role'     :role,
		'content'  :opts['content'],
		'timestamp':time.time(),
		'sessionId':AI_SESS_ID,
	}
	# write history here
	fwrite(AI_FILE_HISTORY,"{}\n".format(json.dumps(obj)),False)
	return obj

#
def run():
	global AI_SESS_ID, AI_FILE_SESSID, AI_FILE_HISTORY, AI_RUNNING
	#
	msgs            = [] # so we save history. if this is good idea i am not sure.
	ollama_cmd      = None
	ollama_data     = None
	
	if AI_RUNNING==False:
		# load session id
		tmp = fread( AI_FILE_SESSID )
		if tmp!=False:
			AI_SESS_ID = int(tmp)
		AI_SESS_ID = AI_SESS_ID+1
		print("DEBUG AI_SESS_ID: {}".format( AI_SESS_ID ))
		fwrite(AI_FILE_SESSID,AI_SESS_ID,True)
		
		# load history
		#tmp = fread( AI_FILE_HISTORY )
		if os.path.exists( "{}".format( AI_FILE_HISTORY ) ):
			with open ( AI_FILE_HISTORY ) as tmp:
				for line in tmp:
					print("DEBUG Loading history: {}".format(line))
					jsonobj = json.loads(line)
					msgs.append( jsonobj )
	#
	AI_RUNNING=True
	#
	while True:
		# VARS
		con = "" # response content
		inp = "" # user input or data for AI
		# EXEC CMD
		if ollama_cmd is not None:
			#
			if rmatch(ollama_cmd,r"^\!.*"):
				print("Executing but before parsing...!...")
				# READ
				if rmatch(ollama_cmd,r"!READ.*"):
					a = pmatch(ollama_cmd,r"\!READ.(.*)")
					if len(a)>0:
						inp = fread(a[0])
						if inp==False:
							inp="File {} don't exist's!".format(a[0])
					else:
						inp = "Something is wrong with your syntax: {}".format(ollama_cmd)
				# LS
				
				#...
			#
			else:
				# We are running in chrooted environment!
				print("Executing {}".format(ollama_cmd))
				inp = os.popen( ollama_cmd ).read()
			#
			ollama_cmd = None
			print("Responding to AIIA: {}".format( inp ))
		# USER INPUT
		else:
			inp = input("\nYou: ")
		
		# USER CMDS, EXIT or CONTINUE or...
		if inp == "exit":
			print("Exiting...")
			break
		# show session id and continue
		elif rmatch(inp,r"^\!\#SHOW.SID"):
			print("SHOW SESSID: {}".format( AI_SESS_ID ))
			continue
		# show number of history and continue
		elif rmatch(inp,r"^\!\#SHOW.NHIS"):
			print("SHOW NUM HISTORY: {}".format( len(msgs) ))
			continue
		# clear history and continue
		elif rmatch(inp,r"^\!\#CLEAR.HIS"):
			print("CLEARING HISTORY: {}...0".format( len(msgs) ))
			msgs = []
			continue
		
		#-------------------------------------------------------------------
		# SEND TO OurAIIA
		#msgs.append({"role":"user","content":inp})
		msgs.append( response_object('user',{'content':inp}) )
		res = ollama.chat( model=AI_MODEL, messages=msgs )
		#
		con = res.message.content
		print("AIIA: {}".format( con ))
		# APPEND HISTORY TO ARRAY
		#msgs.append({"role":"assistant","content":con})
		msgs.append(response_object('assistant',{'content':con}))
		
		#-------------------------------------------------------------------
		# CHECK RESPONSE IF CMD IS REQUESTED
		#--
		if rmatch(con,r"\!DATE"):
			print("Looks ollama wana see current date...")
			ollama_cmd = "date"
		elif rmatch(con,r"\!READ\x20.*"):
			print("Looks ollama wana read data...")
			ollama_cmd = con
		elif rmatch(con,r"!LS"):
			print("Looks ollama wana ls on data...")
			ollama_cmd = con

#
def main(argv):
	run()

#
if __name__ == "__main__":
	main(sys.argv[1:])

