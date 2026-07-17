#!/usr/bin/python
from src.functions import importmodule, initmodule
import getopt, os, sys, socket

from config import Options

hHA = None
hOW = None

def Help():
	print()
	print("Help for Orchestra Worker...:")
	print("-h                         # Help")
	print("-v                         # Version")
	print("-d                         # Debug")
	print("-m [model_name]            # Choose model")
	print("-p [persona_name]          # Choose persona")
	print("--connect HOST:PORT        # Director address (required)")
	print("--name NAME                # Worker name (default: hostname)")
	print()

def Main(argv):
	global Options, hHA, hOW

	opt_help = False
	connect_str = None
	worker_name = None

	try:
		opts, args = getopt.getopt(argv, "dhm:p:", ["debug", "help", "model=", "persona=", "connect=", "name="])
	except getopt.GetoptError:
		opt_help = True

	for opt, arg in opts:
		if opt == "-d" or opt == "--debug":
			Options['DEBUG'] = True
		elif opt == "-h" or opt == "--help":
			opt_help = True
		elif opt == "-v":
			print("{} {}".format(Options['VERSION_NAME'], Options['VERSION']))
			sys.exit(1)
		elif opt == "-m" or opt == "--model":
			Options['AI_MODEL'] = arg
		elif opt == "-p" or opt == "--persona":
			Options['INSTRUCT_CLASS'] = arg
			Options['INSTRUCT_CLASS_OVERRIDE'] = True
		elif opt == "--connect":
			connect_str = arg
		elif opt == "--name":
			worker_name = arg

	if opt_help or not connect_str:
		Help()
		sys.exit(1 if not connect_str else 0)

	# Parse connect string
	if ":" in connect_str:
		host, port_str = connect_str.rsplit(":", 1)
		port = int(port_str)
	else:
		host = connect_str
		port = 9876

	Options['QUIET'] = True

	hHA = initmodule(importmodule("Handle", True, {'path': 'src'}), "Handle", Options)
	hHA.Init()

	from src.OrchestraWorker import OrchestraWorker
	hOW = OrchestraWorker(hHA, host, port, name=worker_name)

	print("Orchestra Worker starting...")
	print("  Name:     {}".format(hOW.name))
	print("  Model:    {}".format(Options['AI_MODEL']))
	print("  Persona:  {}".format(Options['INSTRUCT_CLASS']))
	print("  Director: {}:{}".format(host, port))
	print("--------------------------------------------------------------------------\n")

	try:
		hOW.connect()
		hOW.task_loop()
	except KeyboardInterrupt:
		print("\nWorker interrupted.")
	except Exception as e:
		print("Worker error: {}".format(e))
	finally:
		if hOW:
			hOW.disconnect()
		print("Worker stopped.")

if __name__ == "__main__":
	Main(sys.argv[1:])
