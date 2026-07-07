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
		self.Options['AI_QUICK'] = True
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
		if self.path == '/chat':
			self._handle_chat()
		elif self.path == '/execute':
			self._handle_execute()
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_chat(self):
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
	
	def _send_json_response(self, status_code, data):
		self.send_response(status_code)
		self.send_header('Content-Type', 'application/json; charset=UTF-8')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		self.wfile.write(json.dumps(data).encode('utf-8'))
	
	def _handle_execute(self):
		"""
		POST /execute — direct tool execution (no AI involved).
		Accepts:  {"tool": "<ToolName>...</ToolName>"}
		Returns:  {"success":true, "tool":"ToolName", "result":"..."}
		      or  {"success":false, "tool":"ToolName", "error":"..."}
		"""
		handle = self.ai_server.handle if self.ai_server else None
		if not handle or not hasattr(handle, 'hTP'):
			self._send_json_response(503, {
				'success': False,
				'error': 'Server handle not ready'
			})
			return
		#
		content_length = int(self.headers.get('Content-Length', 0))
		body = self.rfile.read(content_length)
		try:
			data = json.loads(body)
		except (json.JSONDecodeError, UnicodeDecodeError):
			self._send_json_response(400, {
				'success': False,
				'error': 'Invalid JSON'
			})
			return
		#
		tool_xml = data.get('tool', '')
		if not tool_xml:
			self._send_json_response(400, {
				'success': False,
				'error': 'Missing "tool" field'
			})
			return
		#
		tool_name = ''
		try:
			invocations = handle.hTP.ParseTextToolInvocation(tool_xml)
			if not invocations:
				self._send_json_response(400, {
					'success': False,
					'error': 'No tool invocation found in XML'
				})
				return
			#
			inv = invocations[0]
			tool_name = inv['name']
			params = inv.get('parameters', {})
			#
			result = handle.hTP.ExecuteTextTool(tool_name, params)
			#
			is_error = str(result).startswith('Error:') if result else False
			self._send_json_response(200, {
				'success': not is_error,
				'tool': tool_name,
				'result': str(result) if result else '',
			})
		except Exception as e:
			self._send_json_response(500, {
				'success': False,
				'tool': tool_name or 'unknown',
				'error': str(e),
			})
	
	def log_message(self, format, *args):
		pass


def start_server(host='127.0.0.1', port=9877, Options=None):
	if Options is None:
		from config import Options
	server = OurAIServer(host, port, Options)
	server.start()
