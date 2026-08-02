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

import os, sys, json
import atexit, traceback
#
from config import Options
from src.functions import *
from src.cli import Help, parse_cli, _preparse_server_flags
#--
#
#os.environ["OLLAMA_HOST"] = "192.168.1.63:11434"
#
hHA = None # handle to class Handle()
#--
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
			state['backend'] = Options.get('AI_BACKEND', 'ollama')
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
	print(f"Exception: {exc_type.__name__}: {exc_value} (line {line} in {filename})")
	# Optionally print full traceback
	traceback.print_exception(exc_type, exc_value, exc_traceback)
#
atexit.register(cleanup)
sys.excepthook = handle_exception

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
	opt_help, opt_one, oneOpt, opt_history_lists = parse_cli(argv, _cwd, _framework_dir)
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
