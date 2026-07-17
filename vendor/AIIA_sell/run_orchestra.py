#!/usr/bin/python
from src.functions import importmodule, initmodule, user_input
import getopt, os, sys, atexit, traceback

from config import Options

hHA = None
hOD = None
ORCHESTRA_PORT = 9876

def Help():
	print()
	print("Help for Orchestra Director...:")
	print("-h                         # Help")
	print("-v                         # Version")
	print("-d                         # Debug")
	print("-m [model_name]            # Choose model")
	print("-p [persona_name]          # Choose persona")
	print("--port [port]              # Orchestra listen port (default: 9876)")
	print()

def Run(prepared=False):
	global Options, hHA, hOD

	hOD.start()

	if prepared == False:
		hHA.hPP.Prepare()

	hHA.hPM.LoadAll(hHA.Options.get('plans_path', 'plans'))

	while Options['AI_LIVE']:
		hOD.poll_workers()

		poll_cb = lambda: hOD.poll_workers()
		x = hHA.You()

		if x == 5:
			if hOD.get_worker_count() > 0:
				hOD.enter_dispatch_mode()
			else:
				hHA.StartBuild()
		elif x >= 3:
			break
		elif x == 2:
			continue

		# Route plan requests to plan worker if set
		plan_worker = hHA.Options.get('PLAN_WORKER', None)
		mode = hHA.Options.get('MODE', 'build')
		if plan_worker and mode == 'plan':
			user_msg = ""
			for msg in reversed(hHA.hHM.msgs):
				if msg['role'] == 'user':
					user_msg = msg['content']
					break
			if user_msg:
				hOD.route_to_plan_worker(user_msg)
		else:
			x = hHA.AI()
			hHA.Options['AI_ROW_ID'] = hHA.Options['AI_ROW_ID'] + 1

def cleanup():
	global Options, hHA, hOD
	print("cleanup() START")

	if hOD:
		hOD.stop()

	if Options['AI_LIVE']:
		print("cleanup() REPEATING")
		hHA = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", Options)
		hHA.hHM.Update()
		hHA.hHM.GetLast()
		hHA.hHM.CheckDraft()
		Run(True)
		return False
	print("cleanup() QUITING")
	return True

def handle_exception(exc_type, exc_value, exc_traceback):
	if issubclass(exc_type, KeyboardInterrupt):
		print("Exception: Keyboard Interrupt: {}".format(exc_type),{'verbose':True})
		return
	frame = traceback.extract_tb(exc_traceback)[-1]
	filename, line, func, text = frame
	print("Exception: {}: {} (line {} in {})".format(exc_type.__name__, exc_value, line, filename))
	traceback.print_exception(exc_type, exc_value, exc_traceback)

atexit.register(cleanup)
sys.excepthook = handle_exception

def Main(argv):
	global Options, hHA, hOD, ORCHESTRA_PORT

	opt_help = False
	opt_one = None
	oneOpt = {}

	try:
		opts, args = getopt.getopt(argv, "dchm:M:Y:T:p:", ["debug", "continue", "model=", "memory_specific=", "you=", "temperature=", "persona=", "port="])
	except getopt.GetoptError:
		opt_help = True

	for opt, arg in opts:
		if opt == "-d" or opt == "--debug":
			Options['DEBUG'] = True
		elif opt == "-c" or opt == "--continue":
			Options['CONTINUE'] = True
		elif opt == "-h":
			opt_help = True
		elif opt == "-v":
			print("{} {}".format(Options['VERSION_NAME'], Options['VERSION']))
			sys.exit(1)
		elif opt == "-m":
			Options['AI_MODEL'] = arg
		elif opt == "-M":
			oneOpt['history_num'] = int(arg)
		elif opt == "-Y":
			opt_one = arg
			Options['QUIET'] = True
		elif opt == "-T":
			print("Setting temperature: {}".format(float(arg)))
			Options['AI_TEMPERATURE'] = float(arg)
		elif opt == "-p" or opt == "--persona":
			Options['INSTRUCT_CLASS'] = arg
			Options['INSTRUCT_CLASS_OVERRIDE'] = True
		elif opt == "--port":
			ORCHESTRA_PORT = int(arg)

	hHA = initmodule(importmodule("Handle", True, {'path': 'src'}), "Handle", Options)
	hHA.Init()

	from src.OrchestraDirector import OrchestraDirector
	hOD = OrchestraDirector(hHA, port=ORCHESTRA_PORT)
	hHA.hOD = hOD

	if opt_help:
		Help()
		sys.exit(1)
	elif opt_one is not None:
		hHA.One(opt_one, oneOpt)
		sys.exit(1)

	print("Welcome to Orchestra Director.")
	print("Orchestra director lets you distribute tasks to worker agents.")
	print("Start workers with: python run_worker.py --connect <host>:<port>")
	print("--------------------------------------------------------------------------\n")

	Run()

if __name__ == "__main__":
	Main(sys.argv[1:])
