import json, sys, os
from urllib.request import Request, urlopen
from urllib.error import URLError


def run_client(host='127.0.0.1', port=9877):
	base_url = "http://{}:{}".format(host, port)
	#
	try:
		req = Request("{}/health".format(base_url))
		urlopen(req, timeout=3)
	except URLError:
		print("Error: Cannot connect to server at {}:{}".format(host, port), file=sys.stderr)
		print("Make sure the server is running: run.py --server {}:{}".format(host, port), file=sys.stderr)
		sys.exit(1)
	#
	print("Connected to AIIA server at {}:{}".format(host, port))
	print("Type your messages. Ctrl+C or !exit to quit.\n")
	#
	while True:
		try:
			inp = input("You: ").strip()
		except (EOFError, KeyboardInterrupt):
			print()
			break
		#
		if not inp:
			continue
		#
		if inp == '!exit' or inp == '!quit':
			break
		if inp == '!help':
			print("\nCommands:")
			print("  !exit, !quit  - Disconnect")
			print("  !help         - Show this help")
			print("  !MODE plan    - Switch to plan mode")
			print("  !MODE build   - Switch to build mode")
			print("  !NEW SESSION  - Start fresh session")
			print("  (all other !commands are sent to the server)")
			print()
			continue
		#
		_send_and_display(base_url, inp)


def _send_and_display(base_url, message):
	import http.client
	from urllib.parse import urlparse
	#
	parsed = urlparse(base_url)
	conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=120)
	#
	body = json.dumps({'message': message})
	conn.request('POST', '/chat', body, {'Content-Type': 'application/json'})
	response = conn.getresponse()
	#
	if response.status != 200:
		print("Server error: {} {}".format(response.status, response.reason), file=sys.stderr)
		return
	#
	buf = ""
	first_token = True
	#
	while True:
		line = response.readline()
		if not line:
			break
		line = line.decode('utf-8', errors='replace').strip()
		if not line.startswith('data: '):
			continue
		#
		try:
			data = json.loads(line[6:])
		except json.JSONDecodeError:
			continue
		#
		if data.get('type') == 'token':
			if first_token:
				print()
				first_token = False
			print(data['text'], end='', flush=True)
		elif data.get('type') == 'tool':
			if first_token:
				print()
				first_token = False
			print("\n  \u2699 {}(...)".format(data['name']), end='', flush=True)
		elif data.get('type') == 'error':
			print("\nError: {}".format(data['message']), file=sys.stderr)
		elif data.get('type') == 'done':
			if first_token:
				print()
			print()
	conn.close()
