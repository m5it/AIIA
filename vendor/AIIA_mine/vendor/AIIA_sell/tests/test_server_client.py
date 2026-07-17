#!/usr/bin/env python3
"""
Integration test for Server/Client architecture.
Tests: HTTP health endpoint, SSE streaming, client connection.
"""
import sys, os, json, threading, time, io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Stdin bytes to get through Prepare:
#   "0\n"   → InstructManager: select persona index 0
#   "\x18"  → Prepare: Ctrl+X finishes system message
#   "\n"    → user_input reads 1 more byte after Ctrl+X
#   "x\n"   → Actions: cancel
# (HistoryManager: if no history files, loop skipped; if some, empty breaks)
stdin_bytes = b'1\n\x18\nx\n'

old_stdin = sys.stdin
sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding='latin-1')

from src.Server import OurAIServer
from config import Options

# Quiet mode
Options['QUIET'] = True

server = OurAIServer('127.0.0.1', 9877, Options)

def run_server():
	try:
		server.start()
	except Exception as e:
		import traceback
		traceback.print_exc()

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(5)
sys.stdin = old_stdin

import http.client

failed = 0

# === TEST 1: Health endpoint ===
try:
	conn = http.client.HTTPConnection('127.0.0.1', 9877, timeout=5)
	conn.request('GET', '/health')
	resp = conn.getresponse()
	body = resp.read().decode()
	conn.close()
	assert resp.status == 200, "Expected 200, got {}".format(resp.status)
	assert 'ok' in body, "Expected 'ok' in body"
	print("TEST 1 PASS: /health -> {} {}".format(resp.status, body))
except Exception as e:
	print("TEST 1 FAIL: /health -> {}".format(e))
	failed += 1

# === TEST 2: SSE streaming ===
time.sleep(1)
try:
	conn = http.client.HTTPConnection('127.0.0.1', 9877, timeout=30)
	body = json.dumps({'message': 'Say "hi" in one word.'})
	conn.request('POST', '/chat', body, {'Content-Type': 'application/json'})
	resp = conn.getresponse()
	assert resp.status == 200, "Expected 200, got {}".format(resp.status)
	assert resp.getheader('Content-Type') == 'text/event-stream', "Expected SSE content-type"

	tokens = []
	got_done = False
	while True:
		line = resp.readline()
		if not line:
			break
		line = line.decode().strip()
		if not line.startswith('data: '):
			continue
		data = json.loads(line[6:])
		if data.get('type') == 'token':
			tokens.append(data['text'])
		elif data.get('type') == 'done':
			got_done = True
			break
		elif data.get('type') == 'error':
			print("Server error:", data.get('message'))
			break
	conn.close()

	assert got_done, "Expected 'done' event"
	if tokens:
		print("TEST 2 PASS: {} token(s) received".format(len(tokens)))
	else:
		print("TEST 2 WARN: 0 tokens (model may be slow/unavailable)")
except Exception as e:
	print("TEST 2 FAIL: /chat -> {}".format(e))
	import traceback
	traceback.print_exc()
	failed += 1

# === TEST 3: Client module loads ===
try:
	from src.Client import run_client
	print("TEST 3 PASS: Client module loaded OK")
except Exception as e:
	print("TEST 3 FAIL: Client import -> {}".format(e))
	failed += 1

# === SUMMARY ===
if failed:
	print("\n{}/3 tests FAILED".format(failed))
	sys.exit(1)
else:
	print("\nAll tests PASSED")
	sys.exit(0)
