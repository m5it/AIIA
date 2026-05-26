#!/usr/bin/python
from ollama import ChatResponse, chat
import getopt, os, shutil
import atexit, traceback
#
from config import Options
from src.functions import *
#--
#
#os.environ["OLLAMA_HOST"] = "192.168.1.63:11434"
#
hHA = None # handle to class Handle()
#--
#
def Help():
	print()
	print("Help for AIIA...: ")
	print("-h                         # Help")
	print("-v                         # Version")
	print("-d                         # Debug")
	print("-m [model_name]            # Choose model")
	print("-M [history_num]           # Memorize specific history")
	print("-p [persona_name]          # Choose persona (e.g. Developer, Friend, SysAdmin)")
	print("-R                         # Factory reset (delete all state)")
	print("-Y [content_data]          # Set data / content to send as request to AIIA.")
	print()
#
def _confirm_factory_reset():
	print()
	print("=" * 60)
	print("  FACTORY RESET - WARNING")
	print("=" * 60)
	print()
	print("This will permanently delete:")
	print("  - All chat history       (history/ directory)")
	print("  - All saved plans        (plans/ directory)")
	print("  - Session counter        (sessid.aiia)")
	print("  - Project HISTORY.md     (working directory)")
	print("  - Project PLAN.md        (working directory)")
	print("  - All saved tips         (~/.config/ourai/tips/)")
	print("  - Web cookies            (cookies.json)")
	print("  - Terminal audit log     (terminal_audit.log)")
	print()
	print("This cannot be undone.")
	print()
	ans = input("Continue? [y/N]: ").strip().lower()
	return ans in ('y', 'yes')
#
def reset_to_factory():
	global Options
	print("\nResetting to factory defaults...")
	removed = 0
	#
	# 1. Session ID
	sessid_path = Options.get('AI_FILE_SESSID', 'sessid.aiia')
	try:
		with open(sessid_path, 'w') as f:
			f.write('0')
		print("  Reset session counter  -> sessid.aiia = 0")
		removed += 1
	except Exception as e:
		print("  Failed to reset sessid.aiia: {}".format(e))
	#
	# 2. History directory
	history_dir = os.path.join(Options.get('path', ''), Options.get('history_path', 'history'))
	if os.path.isdir(history_dir):
		try:
			shutil.rmtree(history_dir)
			os.makedirs(history_dir, exist_ok=True)
			print("  Cleared history        -> {}".format(history_dir))
			removed += 1
		except Exception as e:
			print("  Failed to clear history: {}".format(e))
	#
	# 3. Plans directory
	plans_dir = os.path.join(Options.get('path', ''), Options.get('plans_path', 'plans'))
	if os.path.isdir(plans_dir):
		try:
			shutil.rmtree(plans_dir)
			os.makedirs(plans_dir, exist_ok=True)
			print("  Cleared plans          -> {}".format(plans_dir))
			removed += 1
		except Exception as e:
			print("  Failed to clear plans: {}".format(e))
	#
	# 4. Project HISTORY.md and PLAN.md (only if working_dir differs from framework)
	working_dir = Options.get('working_dir')
	framework_dir = Options.get('path', '').rstrip('/')
	if working_dir and working_dir != framework_dir:
		for fname in ('HISTORY.md', 'PLAN.md'):
			fpath = os.path.join(working_dir, fname)
			if os.path.exists(fpath):
				try:
					os.remove(fpath)
					print("  Removed project {}  -> {}".format(fname, fpath))
					removed += 1
				except Exception as e:
					print("  Failed to remove {}: {}".format(fname, e))
	#
	# 5. Tips directory
	tips_path = Options.get('TIPS_PATH', os.path.expanduser('~/.config/ourai/tips'))
	if os.path.isdir(tips_path):
		try:
			shutil.rmtree(tips_path)
			print("  Cleared tips           -> {}".format(tips_path))
			removed += 1
		except Exception as e:
			print("  Failed to clear tips: {}".format(e))
	#
	# 6. Cookie files
	for cookie_path in ['cookies.json', 'tools/www/cookies.json', 'tools/cookies.json']:
		fpath = os.path.join(Options.get('path', ''), cookie_path)
		if os.path.exists(fpath):
			try:
				os.remove(fpath)
				print("  Removed cookies        -> {}".format(fpath))
				removed += 1
			except Exception as e:
				print("  Failed to remove {}: {}".format(fpath, e))
	#
	# 7. Terminal audit log
	audit_path = os.path.join(Options.get('path', ''), 'tools/www/terminal_audit.log')
	if os.path.exists(audit_path):
		try:
			os.remove(audit_path)
			print("  Removed audit log      -> {}".format(audit_path))
			removed += 1
		except Exception as e:
			print("  Failed to remove audit log: {}".format(e))
	#
	print()
	if removed > 0:
		print("Factory reset complete. {} item(s) cleared.".format(removed))
	else:
		print("Nothing to reset — already clean.")
	print("Run `ourai` to start a fresh session.")
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
			# Set current chat history back.
			hHA.hHM.Update()
			hHA.hHM.GetLast()
		elif x==6: # New Session - fresh start with Prepare()
			hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
			hHA.Init()
			prepared = False
			continue
		elif x==3: # Break
			#print("DEBUG run() in loop, break...")
			Options['AI_LIVE'] = False
			break
#--
#
def cleanup():
	global Options,Stats
	print("cleanup() START")
	#
	if Options['AI_LIVE']:
		print("cleanup() REPEATING")
		hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
		# Set current chat history back.
		hHA.hHM.Update()
		hHA.hHM.GetLast()
		# Append `failed` response from assistant
		hHA.hHM.CheckDraft()
		#
		Run(True)
		return False
	print("cleanup() QUITING")
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
		opts, args = getopt.getopt(argv,"dchm:M:Y:T:p:R",["--debug", "--continue", "--model", "--memory_specific", "--you", "--temperature", "--persona", "--reset"])
	except getopt.GetoptError:
		opt_help = True
	
	#
	for opt, arg in opts:
		if opt=="-d" or opt=="--debug":
			Options['DEBUG'] = True
		elif opt=="-c" or opt=="--continue":
			Options['CONTINUE'] = True
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
		elif opt=="-R" or opt=="--reset":
			if not _confirm_factory_reset():
				sys.exit(0)
			reset_to_factory()
			sys.exit(0)
		elif opt=="-p" or opt=="--persona":
			Options['INSTRUCT_CLASS'] = arg
			Options['INSTRUCT_CLASS_OVERRIDE'] = True
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

