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
import getopt, os, shutil, sys, json
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
	print("--history-lists            # List all available history files and exit")
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
	print("--site-scripts-path [path]  # Path to per-website JS support scripts (default: project wwwurljssupport/ or ~/.config/aiia/wwwurljssupport/)")
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
	print("  - All saved tips         (~/.config/aiia/tips/)")
	print("  - Background activity log (background.log)")
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
	# 1. State file — reset session counter and mode
	state_path = Options.get('AI_FILE_STATE', 'state.aiia')
	try:
		tmp = state_path + '.tmp'
		_default_state = '{"sess_id":0,"mode":"plan"}'
		with open(tmp, 'w') as f:
			f.write(_default_state)
		os.replace(tmp, state_path)
		print("  Reset state.aiia       -> sess_id=0, mode=plan")
		removed += 1
	except Exception as e:
		print("  Failed to reset state.aiia: {}".format(e))
	# Remove legacy per-file .aiia state files
	framework_dir = Options.get('path', '').rstrip('/')
	for fname in ('sessid.aiia', 'mode.aiia', 'model.aiia', 'persona.aiia',
				  'used_models.aiia', 'tokens.aiia'):
		fpath = os.path.join(framework_dir, fname)
		if os.path.exists(fpath):
			try:
				os.remove(fpath)
				print("  Removed legacy {} -> {}".format(fname, fpath))
			except Exception as e:
				print("  Failed to remove {}: {}".format(fname, e))
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
	tips_path = Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
	if os.path.isdir(tips_path):
		try:
			shutil.rmtree(tips_path)
			print("  Cleared tips           -> {}".format(tips_path))
			removed += 1
		except Exception as e:
			print("  Failed to clear tips: {}".format(e))
	#
	# 5b. Background log
	bg_log_path = Options.get('BACKGROUND_LOG')
	if bg_log_path and os.path.exists(bg_log_path):
		try:
			os.remove(bg_log_path)
			print("  Cleared background.log -> {}".format(bg_log_path))
		except Exception as e:
			print("  Failed to remove background.log: {}".format(e))
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
	print("Run `aiia` to start a fresh session.")
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
	# Save current state for -c continuation
	state_path = Options.get('AI_FILE_STATE')
	if state_path:
		try:
			state = {}
			if os.path.exists(state_path):
				try:
					state = json.loads(fread(state_path))
				except Exception:
					state = {}
			state['mode'] = Options.get('MODE', 'plan')
			state['model'] = Options.get('AI_MODEL', '')
			state['persona'] = Options.get('INSTRUCT_CLASS', 'Developer')
			tmp = state_path + '.tmp'
			fwrite(tmp, json.dumps(state), True)
			os.replace(tmp, state_path)
		except Exception as e:
			print("  Failed to save state: {}".format(e))
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
		elif a == '--site-scripts-path':
			if value is None and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
				value = argv[i + 1]
				i += 1
			if value is not None:
				Options['SITE_SCRIPTS_PATH'] = os.path.abspath(value) if not os.path.isabs(value) else value
		i += 1

#
def Main(argv):
	global Options, hHA
	#
	# Pre-parse server-relevant flags before subcommand routing
	_preparse_server_flags(argv)
	#
	# Auto-migrate old ~/.config/ourai/ to ~/.config/aiia/
	_old_config = os.path.expanduser('~/.config/ourai')
	_new_config = os.path.expanduser('~/.config/aiia')
	if os.path.isdir(_old_config) and not os.path.isdir(_new_config):
		try:
			os.rename(_old_config, _new_config)
			print("Migrated ~/.config/ourai -> ~/.config/aiia")
		except Exception as e:
			print("Failed to migrate ~/.config/ourai: {}".format(e))
	#
	# Subcommand routing: aiia --orchestra [args...] or aiia --worker [args...]
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
		_spec = argv[idx + 1] if len(argv) > idx + 1 and not argv[idx + 1].startswith('-') else None
		#
		from src.ServerFactory import ServerFactory
		profile_name, host, port = ServerFactory.resolve_profile_spec(_spec, Options)
		#
		from src.Server import start_server
		Options['AI_LIVE'] = False
		start_server(host, port, Options, profile=profile_name)
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
	# Load per-project config overrides (aiia.json in CWD)
	# Applied before CLI parsing so CLI flags have final say
	if _cwd != _framework_dir:
		project_config_path = os.path.join(_cwd, 'aiia.json')
		if os.path.exists(project_config_path):
			try:
				with open(project_config_path, 'r') as f:
					for key, val in json.load(f).items():
						if key in Options:
							if isinstance(Options[key], dict) and isinstance(val, dict):
								Options[key].update(val)
							else:
								Options[key] = val
				Options['working_dir'] = _cwd
			except Exception as e:
				print("Warning: Failed to load {}: {}".format(project_config_path, e))
	#
	opt_help = False
	opt_one  = None # Send one request and exit
	opt_history_lists = False
	oneOpt   = {} # options for one request from terminal
	opts     = [] # default to empty (avoids UnboundLocalError if getopt fails)
	args     = []
	#
	try:
		opts, args = getopt.getopt(argv,"vdchm:M:Y:T:p:QRS:C:P:",["debug", "continue", "help", "model=", "memory_specific=", "you=", "temperature=", "persona=", "quick", "reset", "server=", "connect=", "prompt=", "history-lists", "site-scripts-path="])
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
		elif opt=="--history-lists":
			opt_history_lists = True
		elif opt=="--site-scripts-path":
			Options['SITE_SCRIPTS_PATH'] = os.path.abspath(arg) if not os.path.isabs(arg) else arg
	#
	# Set working_dir from CWD (fallback if aiia.json didn't already set it)
	if Options.get('working_dir') is None and _cwd != _framework_dir:
		Options['working_dir'] = _cwd
	#
	# Show help before initializing Handle (no need to load AI system just for --help)
	if opt_help:
		Help()
		Options['AI_LIVE'] = False
		sys.exit(0)
	#
	hHA      = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
	hHA.Init()
	
	# List available history files and exit
	if opt_history_lists:
		hHA.hHM.Available()
		sys.stdout.flush()
		os._exit(0)
	
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

