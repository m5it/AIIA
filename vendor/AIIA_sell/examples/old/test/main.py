# Refs: 
# https://lmstudio.ai/docs/python/llm-prediction/chat-completion
#--
import lmstudio as lms
import select
import json, sys, time, os
import signal
from functions import *
#--
AI_MODEL        = 'llama3.2'
AI_SESS_ID      = 0
AI_FILE_HISTORY = 'history.aiia'
AI_FILE_SESSID  = 'sessid.aiia'
AI_RUNNING      = False
AIM             = None # model
AIC             = None # chat
#--
def signal_handler(sig, frame):
	print("Ctrl-D to Quit!")
	print("You: ", end='', flush=True)
#
signal.signal(signal.SIGINT, signal_handler)

#
def run():
	global AI_SESS_ID, AI_FILE_SESSID, AIM, AIC, AI_RUNNING
	#
	ollama_cmd      = None
	ollama_data     = None
	#
	if AI_RUNNING==False:
		# load session id
		tmp = fread( AI_FILE_SESSID )
		if tmp!=False:
			AI_SESS_ID = int(tmp)
		AI_SESS_ID = AI_SESS_ID+1
		print("DEBUG AI_SESS_ID: {}".format( AI_SESS_ID ))
		fwrite(AI_FILE_SESSID,AI_SESS_ID,True)
	#
	AI_RUNNING=True
	#
	#AIC = lms.Chat("You are a task focused AI assistant")
	#AIC = lms.Chat("If i say what time or date is, you should say `!DATE`")
	AIC = lms.Chat()
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
		
		#-------------------------------------------------------------------
		# TO AIIA
		AIC.add_user_message( inp )
		prediction_stream = AIM.respond_stream(
			AIC,
			on_message=AIC.append,
		)
		#print("AIIA({}): ".format( len(prediction_stream) ), end="", flush=True)
		conlen=0
		print("AIIA(): ", end="", flush=True)
		for fragment in prediction_stream:
			print( fragment.content , end="", flush=True)
			con = "{}{}".format( con, fragment.content )
			conlen=conlen+1
		print()
		
		print("DEBUG AIIA CON( {} ): \n{}\n".format(conlen, con))
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
	global AIM
	AIM = lms.llm()
	run()

#
if __name__ == "__main__":
	main(sys.argv[1:])

