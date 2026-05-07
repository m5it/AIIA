#!/usr/bin/python
from ollama import ChatResponse, chat
import getopt, os
import atexit, traceback
#
from src.functions import *
#--
#
#os.environ["OLLAMA_HOST"] = "192.168.1.63:11434"
#
Options         = {
	#
	"DEBUG"               :False, # print A lot of Additional informations
	"QUIET"               :False, # quite all prints and show only result. (used with -Y)
	"VERSION"             :0.1,
	"VERSION_NAME"        :"AiiA",
	#
	"SPEAK"               :True,
	#
	"AI_MODEL"            :"gemma4:26b",
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
	"MODE"                :"build",  # "plan" or "build" mode
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
def Run(prepared=False):
	global Options, hHA
	#
	while Options['AI_LIVE']:
		#
		if prepared==False:
			hHA.hPP.Prepare()
		#
		x = hHA.Chat()
		#
		if x==4: # Update Handle() class (reload)
			hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
		elif x==3: # Break
			#print("DEBUG run() in loop, break...")
			break
#--
#
def cleanup():
	global Options,Stats
	print("cleanup() START")
	#
	#hHA.hPP.SaveMemory()
	#
	#Run(True)
	return True
#
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Let KeyboardInterrupt propagate
        print("Exception: Keyboard Interrupt: {}".format(exc_type),{'verbose':True})
        return
    # Extract traceback info
    tb = traceback.extract_tb(exc_traceback)
    # Get the last frame (most recent error)
    frame = tb[-1]
    filename, line, func, text = frame
    print(f"Exception: {exc_type.__name__}: {exc_value} (line {line} in {filename})",{'verbose':True,})
    # Optionally print full traceback
    traceback.print_exception(exc_type, exc_value, exc_traceback)
#
atexit.register(cleanup)
sys.excepthook = handle_exception

#
def Main(argv):
	global Options, hHA
	#
	opt_help = False
	opt_one  = None # Send one request and exit
	oneOpt   = {} # options for one request from terminal
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
	#
	Run()

#
if __name__ == "__main__":
	Main(sys.argv[1:])

