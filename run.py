#!/usr/bin/python
import sys, os
# Ensure the framework root is in sys.path and CWD is removed, so its
# src/ package isn't shadowed by a project CWD that has its own src/
# package (e.g. OurSSH).
_cwd = os.getcwd()
sys.path = [p for p in sys.path if p not in ('', _cwd)]
_framework_dir = os.path.dirname(os.path.abspath(__file__))
if _framework_dir in sys.path:
	sys.path.remove(_framework_dir)
sys.path.insert(0, _framework_dir)

from ollama import chat
import getopt, os, shutil, sys
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
	print("-P [system_prompt]         # Set custom system message prefix")
	print("-Q                         # Quick mode — skip interactive Prepare prompts")
	print("-R                         # Factory reset (delete all state)")
	print("-O / --orchestra [opts]    # Run as orchestra director (--orchestra -h for help)")
	print("-W / --worker [opts]       # Run as orchestra worker (--worker -h for help)")
	print("-S / --server [host:port]  # Run as SSE chat server (default 127.0.0.1:9877)")
	print("-C / --connect [host:port] # Connect to SSE chat server (default 127.0.0.1:9877)")
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
	# 1b. Mode file
	mode_path = Options.get('AI_FILE_MODE', 'mode.aiia')
	try:
		with open(mode_path, 'w') as f:
			f.write('plan')
		print("  Reset mode file        -> mode.aiia = plan")
		removed += 1
	except Exception as e:
		print("  Failed to reset mode.aiia: {}".format(e))
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
	for cookie_path in ['cookies.json', 'tools/koslenium_driver/www/cookies.json', 'tools/cookies.json']:
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
	audit_path = os.path.join(Options.get('path', ''), 'tools/koslenium_driver/www/terminal_audit.log')
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
	global Options, hHA
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
	# Save current mode for -c continuation
	mode_file = Options.get('AI_FILE_MODE')
	if mode_file:
		fwrite(mode_file, Options.get('MODE', 'plan'), True)
	# Save current model for -c continuation
	model_file = Options.get('AI_FILE_MODEL')
	if model_file:
		fwrite(model_file, Options.get('AI_MODEL', ''), True)
	# Save current persona for -c continuation
	persona_file = Options.get('AI_FILE_PERSONA')
	if persona_file:
		fwrite(persona_file, Options.get('INSTRUCT_CLASS', 'Developer'), True)
	return True
#
def handle_exception(exc_type, exc_value, exc_traceback):
	if issubclass(exc_type, KeyboardInterrupt):
		print("Keyboard Interrupt received. Exiting.")
		Options['AI_LIVE'] = False
		sys.exit(1)
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
def _list_personas():
	"""Scan instruct/ directory and return list of persona class names (sorted)."""
	import os
	cls_path = Options.get('INSTRUCT_PATH', 'instruct')
	base_path = Options.get('path', '')
	instruct_dir = "{}{}".format(base_path, cls_path)
	result = []
	if os.path.isdir(instruct_dir):
		for f in sorted(os.listdir(instruct_dir)):
			if f.endswith('.py') and f != '__init__.py':
				result.append(f[:-3])
	return result

def _resolve_persona(value):
	"""If value is a numeric index, resolve it to persona class name."""
	personas = _list_personas()
	try:
		idx = int(value)
		if 0 <= idx < len(personas):
			return personas[idx]
	except (ValueError, IndexError):
		pass
	return value

def _preparse_server_flags(argv):
	"""Extract server-relevant flags from argv for -S/--server mode.
	This runs before full getopt parsing because -S triggers early exit."""
	i = 0
	while i < len(argv):
		a = argv[i]
		# Handle --long=value form
		value = None
		if a.startswith('--') and '=' in a:
			eq = a.index('=')
			value = a[eq + 1:]
			a = a[:eq]
		if a in ('-p', '--persona'):
			if value is None and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
				value = argv[i + 1]
				i += 1
			if value is not None:
				Options['INSTRUCT_CLASS'] = _resolve_persona(value)
				Options['INSTRUCT_CLASS_OVERRIDE'] = True
		elif a in ('-P', '--prompt'):
			if value is None and i + 1 < len(argv):
				value = argv[i + 1]
				i += 1
			if value is not None:
				Options['AI_SYSTEM_MESSAGE'] = value
		elif a in ('-m', '--model'):
			if value is None and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
				value = argv[i + 1]
				i += 1
			if value is not None:
				Options['AI_MODEL'] = value
		elif a == '-T' or a == '--temperature':
			if value is None and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
				value = argv[i + 1]
				i += 1
			if value is not None:
				try:
					Options['AI_OPTIONS']['temperature'] = float(value)
				except ValueError:
					pass
		elif a in ('-Q', '--quick'):
			Options['AI_QUICK'] = True
		elif a in ('-d', '--debug'):
			Options['DEBUG'] = True
		elif a in ('-M', '--memory_specific'):
			if value is None and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
				value = argv[i + 1]
				i += 1
			if value is not None:
				try:
					Options['AI_MEMORY_SPECIFIC'] = int(value)
				except ValueError:
					pass
		i += 1

#
def Main(argv):
	global Options, hHA
	#
	# Pre-parse server-relevant flags before subcommand routing
	_preparse_server_flags(argv)
	#
	# Subcommand routing: ourai --orchestra [args...] or ourai --worker [args...]
	if '--orchestra' in argv:
		from run_orchestra import Main as OrchestraMain
		idx = argv.index('--orchestra')
		OrchestraMain(argv[idx + 1:])
		Options['AI_LIVE'] = False
		sys.exit(0)
	if '--worker' in argv:
		from run_worker import Main as WorkerMain
		idx = argv.index('--worker')
		WorkerMain(argv[idx + 1:])
		Options['AI_LIVE'] = False
		sys.exit(0)
	if '--server' in argv or '-S' in argv:
		opt = '--server' if '--server' in argv else '-S'
		idx = argv.index(opt)
		_host_port = argv[idx + 1] if len(argv) > idx + 1 and not argv[idx + 1].startswith('-') else None
		host = '127.0.0.1'
		port = 9877
		if _host_port:
			parts = _host_port.split(':')
			host = parts[0] if parts[0] else host
			port = int(parts[1]) if len(parts) > 1 else port
		from src.Server import start_server
		Options['AI_LIVE'] = False
		start_server(host, port, Options)
		sys.exit(0)
	if '--connect' in argv or '-C' in argv:
		opt = '--connect' if '--connect' in argv else '-C'
		idx = argv.index(opt)
		_host_port = argv[idx + 1] if len(argv) > idx + 1 and not argv[idx + 1].startswith('-') else None
		host = '127.0.0.1'
		port = 9877
		if _host_port:
			parts = _host_port.split(':')
			host = parts[0] if parts[0] else host
			port = int(parts[1]) if len(parts) > 1 else port
		from src.Client import run_client
		Options['AI_LIVE'] = False
		run_client(host, port)
		sys.exit(0)
	#
	opt_help = False
	opt_one  = None # Send one request and exit
	oneOpt   = {} # options for one request from terminal
	opts     = [] # default to empty (avoids UnboundLocalError if getopt fails)
	args     = []
	#
	try:
		opts, args = getopt.getopt(argv,"vdchm:M:Y:T:p:QRS:C:P:",["debug", "continue", "help", "model=", "memory_specific=", "you=", "temperature=", "persona=", "quick", "reset", "server=", "connect=", "prompt="])
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
			Options['AI_LIVE'] = False
			sys.exit(0)
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
			Options['AI_OPTIONS']['temperature'] = float(arg)
		elif opt=="-R" or opt=="--reset":
			if not _confirm_factory_reset():
				sys.exit(0)
			reset_to_factory()
			Options['AI_LIVE'] = False
			sys.exit(0)
		elif opt=="-Q" or opt=="--quick":
			Options['AI_QUICK'] = True
		elif opt=="-P" or opt=="--prompt":
			Options['AI_SYSTEM_MESSAGE'] = arg
		elif opt=="-p" or opt=="--persona":
			Options['INSTRUCT_CLASS'] = _resolve_persona(arg)
			Options['INSTRUCT_CLASS_OVERRIDE'] = True
	#
	# Auto-detect project directory from CWD
	cwd = os.getcwd()
	framework_dir = os.path.dirname(os.path.abspath(__file__))
	if cwd != framework_dir:
		Options['working_dir'] = cwd
	#
	# Show help before initializing Handle (no need to load AI system just for --help)
	if opt_help:
		Help()
		Options['AI_LIVE'] = False
		sys.exit(0)
	#
	hHA      = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
	hHA.Init()
	
	#
	# One request / response and exit
	if opt_one!=None:
		hHA.One(opt_one,oneOpt)
		Options['AI_LIVE'] = False
		sys.exit(0)
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

