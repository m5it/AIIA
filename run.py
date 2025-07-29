#!/usr/bin/python
from ollama import ChatResponse, chat
#import select
import signal, getopt
#
from src.functions import *
#--
#
Options         = {
	#
	"DEBUG"               :False, # print A lot of Additional informations
	"QUIET"               :False, # quite all prints and show only result. (used with -Y)
	"VERSION"             :0.1,
	"VERSION_NAME"        :"AiiA",
	#
	"AI_MODEL"            :"llama3.1",
	"AI_FILE_SESSID"      :"sessid.aiia",
	"AI_USER_HISTORY"     :"huser.aiia",
	"AI_FILE_HISTORY"     :"history.aiia",
	"AI_FILE_LOAD_HISTORY":False,
	"AI_SESS_ID"          :0,
	"AI_ROW_ID"           :0,
	"AI_MAX_CONTENT_LEN"  :20000,
	"AI_LIVE"             :True,
	"AI_TEMPERATURE"      :0.7,
	#
	"path"                :"{}/".format(os.path.dirname(__file__)),
	"tools_path"          :"tools",
	"actions_path"        :"actions",
	"history_path"        :"history",
}
#
hHA = None # handle to class Handle()
#--
#
def signal_handler(sig, frame):
	Run()
#
signal.signal(signal.SIGINT, signal_handler)

#
def Help():
	print()
	print("Help for AIIA...: ")
	print("-h                         # Help")
	print("-v                         # Version")
	print("-m [model_name]            # Choose model")
	print("-M [history_num]           # Memorize specific history")
	print("-Y [content_data]          # Set data / content to send as request to AIIA.")
	print()
#
def Run():
	global Options, hHA
	#
	while True:
		x = hHA.Chat()
		#
		if x==4: # Update Handle() class (reload)
			hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
		elif x==3: # Break
			#print("DEBUG run() in loop, break...")
			break

#
def Main(argv):
	global Options, hHA
	#
	opt_help = False
	opt_one  = None # Send one request and exit
	oneOpt   = {} # options for one request from terminal
	#
	#print("__file__      : {}".format( __file__ ))
	#print("real(__file__): {}".format( os.path.dirname(__file__) ))
	#sys.exit(1)
	#
	try:
		opts, args = getopt.getopt(argv,"dvhm:M:Y:T:",["--model", "--memory_specific", "--you", "--temperature"])
	except getopt.GetoptError:
		opt_help = True
	#
	for opt, arg in opts:
		if opt=="-d":
			Options['DEBUG'] = True
		elif opt=="-h":
			opt_help = True
		elif opt=="-v":
			print("{} {}".format( Options['VERSION_NAME'], Options['VERSION'] ))
			sys.exit(1)
		elif opt=="-m":
			Options['AI_MODEL'] = arg
		elif opt=="-M":
			# Load memory from specific user prepared file.dbk
			oneOpt['history_num'] = int(arg)
		elif opt=="-Y":
			# Data for AIIA
			opt_one = arg
			Options['QUIET'] = True
		elif opt=="-T":
			print("AIIA => Setting temperature: {}".format( float(arg) ))
			Options['AI_TEMPERATURE'] = float(arg)
	#
	hHA      = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
	hHA.Init()
	
	#
	if opt_help:
		Help()
		sys.exit(1)
	# One request / response and exit
	elif opt_one!=None:
		hHA.One(opt_one,oneOpt)
		sys.exit(1)
	#--
	print("Welcome to AIIA.")
	print("  * AIIA is like LM Studio for `Large language models` just running in terminal and in python.")
	print("If you have any questions you can join #help on https://chat.grandekos.com")
	print("--------------------------------------------------------------------------\n")
	#--
	while Options['AI_LIVE']:
		# Prepare actions, history, tools, system message
		hHA.Prepare()
		#
		Run()

#
if __name__ == "__main__":
	Main(sys.argv[1:])

