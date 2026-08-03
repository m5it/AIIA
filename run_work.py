#!/usr/bin/python
import getopt, os, sys

from config import Options

hWC = None

def Help():
	print()
	print("Help for aiia_work marketplace client...:")
	print("-h                         # Help")
	print("-v                         # Version")
	print("-d                         # Debug")
	print("--base-url URL             # Marketplace API base URL (default: https://apis.aiia-frame.work/rest/aiia_work)")
	print("--api-key KEY              # API key (X-Api-Key). Overrides env/config/stored key")
	print("--sso-token TOKEN          # SSO bearer token (required for !WORK KEYGEN)")
	print("--key-file PATH            # Stored API key file (default: ~/.config/aiia/aiia_work.json)")
	print("--role ROLE                # Default keygen role (giver|worker|both)")
	print()
	print("Commands (type at the prompt):")
	print("  !WORK HELP")
	print("  !WORK KEYGEN [label] [role]")
	print("  !WORK KEYS | KEYREVOKE <id>")
	print("  !WORK CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]")
	print("  !WORK LIST | SHOW <id> | STATUS <id> <status>")
	print("  !WORK APPLY <project> <msg> | MY | ACCEPT <rid> | DECLINE <rid>")
	print("  !WORK CMD <name> [json]")
	print()

def Main(argv):
	global Options, hWC

	opt_help = False
	kwargs = {}

	try:
		opts, args = getopt.getopt(argv, "dhv", ["debug", "help", "base-url=", "api-key=", "sso-token=", "key-file=", "role="])
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
		elif opt == "--base-url":
			kwargs['base_url'] = arg
		elif opt == "--api-key":
			kwargs['api_key'] = arg
		elif opt == "--sso-token":
			kwargs['sso_token'] = arg
		elif opt == "--key-file":
			kwargs['key_file'] = arg
		elif opt == "--role":
			Options['AIIA_WORK_ROLE'] = arg

	if opt_help:
		Help()
		sys.exit(0)

	from aiia_work.client import WorkClient
	from aiia_work.console import WorkConsole

	hWC = WorkConsole(client=WorkClient(options=Options, **kwargs))
	hWC.loop()

if __name__ == "__main__":
	Main(sys.argv[1:])
