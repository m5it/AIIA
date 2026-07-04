import json, sys, os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
#
from src.functions import *
from config import Options as DefaultOptions


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	allow_reuse_address = True


class OurAIServer():
	def __init__(self, host, port, Options):
		self.host = host
		self.port = port
		self.Options = Options
		self.handle = None
		self._lock = threading.Lock()
	
	def start(self):
		from src.Handle import Handle
		self.handle = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", self.Options)
		self.handle.Init()
		self.handle.hPP.Prepare()
		#
		_SSEHandler.ai_server = self
		server = ThreadedHTTPServer((self.host, self.port), _SSEHandler)
		#
		print("\n" + "="*60)
		print("  Server listening on http://{}:{}".format(self.host, self.port))
		print("  Connect with: run.py --connect {}:{}".format(self.host, self.port))
		print("="*60 + "\n")
		try:
			server.serve_forever()
		except KeyboardInterrupt:
			print("\nServer shutting down.")
			server.shutdown()
	
	def chat(self, message, write_event):
		with self._lock:
			try:
				result = self.handle.You(message)
				if result == 0:
					self.handle.AI({'stream_callback': write_event})
				elif result == 5:
					self.handle.StartBuild()
				elif result == 6:
					self.handle = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", self.Options)
					self.handle.Init()
					self.handle.hPP.Prepare()
					write_event({'type':'token','text':'[New session started]'})
			except Exception as e:
				write_event({'type':'error','message':str(e)})


class _SSEHandler(BaseHTTPRequestHandler):
	ai_server = None
	
	def do_GET(self):
		if self.path == '/health':
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.send_header('Access-Control-Allow-Origin', '*')
			self.end_headers()
			self.wfile.write(b'{"status":"ok"}')
			return
		self.send_response(404)
		self.end_headers()
	
	def do_POST(self):
		if self.path != '/chat':
			self.send_response(404)
			self.end_headers()
			return
		#
		content_length = int(self.headers.get('Content-Length', 0))
		body = self.rfile.read(content_length)
		try:
			data = json.loads(body)
			message = data.get('message', '')
		except (json.JSONDecodeError, UnicodeDecodeError):
			self.send_response(400)
			self.send_header('Content-Type', 'application/json')
			self.send_header('Access-Control-Allow-Origin', '*')
			self.end_headers()
			self.wfile.write(b'{"error":"invalid JSON"}')
			return
		#
		self.send_response(200)
		self.send_header('Content-Type', 'text/event-stream')
		self.send_header('Cache-Control', 'no-cache')
		self.send_header('Connection', 'keep-alive')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('X-Accel-Buffering', 'no')
		self.end_headers()
		#
		def write_event(event):
			try:
				self.wfile.write("data: {}\n\n".format(json.dumps(event)).encode())
				self.wfile.flush()
			except (BrokenPipeError, ConnectionResetError):
				pass
		#
		self.ai_server.chat(message, write_event)
		write_event({'type':'done'})
	
	def log_message(self, format, *args):
		pass


def start_server(host='127.0.0.1', port=9877, Options=None):
	if Options is None:
		from config import Options
	server = OurAIServer(host, port, Options)
	server.start()
