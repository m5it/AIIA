import getopt
import os
import sys

from config import Options
from src.FactoryReset import _confirm_factory_reset, reset_to_factory
from src.PersonaResolver import _resolve_persona

#
def Help():
	print()
	print("Help for AIIA...: ")
	print("-h                         # Help")
	print("--history-lists            # List all available history files and exit")
	print("-v                         # Version")
	print("-d                         # Debug")
	print("-m [model_name]            # Choose model")
	print("-b [backend_name]          # Choose LLM backend (ollama|vllm)")
	print("-M [history_num]           # Memorize specific history")
	print("-p [persona_name]          # Choose persona (e.g. Developer, Friend, SysAdmin)")
	print("-P [system_prompt]         # Set custom system message prefix")
	print("-Q                         # Quick mode — skip interactive Prepare prompts")
	print("-R                         # Factory reset (delete all state)")
	print("-O / --orchestra [opts]    # Run as orchestra director (--orchestra -h for help)")
	print("-W / --worker [opts]       # Run as orchestra worker (--worker -h for help)")
	print("--work [opts]              # Run as aiia_work marketplace client (--work -h for help)")
	print("-S / --server [host:port]  # Run as SSE chat server (default 127.0.0.1:9877)")
	print("-C / --connect [host:port] # Connect to SSE chat server (default 127.0.0.1:9877)")
	print("-Y [content_data]          # Set data / content to send as request to AIIA.")
	print("--site-scripts-path [path]  # Path to per-website JS support scripts (default: project wwwurljssupport/ or ~/.config/aiia/wwwurljssupport/)")
	print()

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
			value, i = _flag_take_value(value, argv, i)
			if value is not None:
				Options['INSTRUCT_CLASS'] = _resolve_persona(value)
				Options['INSTRUCT_CLASS_OVERRIDE'] = True
		elif a in ('-P', '--prompt'):
			value, i = _flag_take_value(value, argv, i, allow_dash=True)
			if value is not None:
				Options['AI_SYSTEM_MESSAGE'] = value
		elif a in ('-m', '--model'):
			value, i = _flag_take_value(value, argv, i)
			if value is not None:
				Options['AI_MODEL'] = value
		elif a in ('-b', '--backend'):
			value, i = _flag_take_value(value, argv, i)
			if value is not None:
				Options['AI_BACKEND'] = value.lower()
		elif a == '-T' or a == '--temperature':
			value, i = _flag_take_value(value, argv, i)
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
			value, i = _flag_take_value(value, argv, i)
			if value is not None:
				try:
					Options['AI_MEMORY_SPECIFIC'] = int(value)
				except ValueError:
					pass
		elif a == '--site-scripts-path':
			value, i = _flag_take_value(value, argv, i)
			if value is not None:
				Options['SITE_SCRIPTS_PATH'] = os.path.abspath(value) if not os.path.isabs(value) else value
		i += 1

def _flag_take_value(value, argv, i, allow_dash=False):
	"""When a flag has no inline `--flag=value` value, consume the next
	argv entry as its value. Returns (value, new_i)."""
	if value is None and i + 1 < len(argv) and (allow_dash or not argv[i + 1].startswith('-')):
		return argv[i + 1], i + 1
	return value, i

#
def parse_cli(argv, cwd, framework_dir):
	opt_help = False
	opt_one  = None # Send one request and exit
	opt_history_lists = False
	oneOpt   = {} # options for one request from terminal
	opts     = [] # default to empty (avoids UnboundLocalError if getopt fails)
	args     = []
	#
	try:
		opts, args = getopt.getopt(argv,"vdchm:M:Y:T:p:QRS:C:P:b:",["debug", "continue", "help", "model=", "memory_specific=", "you=", "temperature=", "persona=", "quick", "reset", "server=", "connect=", "prompt=", "history-lists", "site-scripts-path=", "backend="])
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
			_cli_version_exit()
		elif opt=="-m":
			Options['AI_MODEL'] = arg
		elif opt=="-b":
			Options['AI_BACKEND'] = arg.lower()
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
			_cli_factory_reset()
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
	if Options.get('working_dir') is None and cwd != framework_dir:
		Options['working_dir'] = cwd
	#
	return opt_help, opt_one, oneOpt, opt_history_lists

def _cli_version_exit():
	print("{} {}".format( Options['VERSION_NAME'], Options['VERSION'] ))
	Options['AI_LIVE'] = False
	sys.exit(0)

def _cli_factory_reset():
	if not _confirm_factory_reset():
		sys.exit(0)
	reset_to_factory()
	Options['AI_LIVE'] = False
	sys.exit(0)
