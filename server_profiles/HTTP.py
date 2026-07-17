"""HTTP SSE Server Profile — default AIIA server.

Endpoints:
  GET  /health                    — {"status":"ok"}
  POST /chat                      — SSE stream of AI tokens
  POST /execute                   — Direct tool execution (no AI)

This is the standard server for editor clients, AI tools, and API consumers.
Uses stdlib http.server + ThreadingMixIn — no external deps.
"""

import json, sys, os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from server_profiles._ServerBase import ServerProfile
from src.functions import *


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	allow_reuse_address = True


class OurAIServer():
	"""HTTP SSE server that wraps the AIIA Handle.
	
	Runs the full AIIA chat loop and AI engine.
	Accepts chat messages via POST /chat (SSE stream).
	Accepts direct tool calls via POST /execute.
	"""
	
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
		print("  {} server listening on http://{}:{}".format(
			self.Options.get('VERSION_NAME', 'AIIA'), self.host, self.port))
		print("  Connect with: run.py --connect {}:{}".format(self.host, self.port))
		print("  API docs:     GET http://{}:{}/".format(self.host, self.port))
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
				elif result == 1:
					self._stream_tool_results(write_event)
				elif result == 5:
					self.handle.StartBuild()
				elif result == 6:
					self.handle = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", self.Options)
					self.handle.Init()
					self.handle.hPP.Prepare()
					write_event({'type':'token','text':'[New session started]'})
			except Exception as e:
				write_event({'type':'error','message':str(e)})
	
	def _stream_tool_results(self, write_event):
		handle = self.handle
		results = getattr(handle, '_direct_tool_results', [])
		for item in results:
			name = item.get('name', '')
			content = item.get('content', '')
			if name == 'TreeView':
				write_event({'type':'tool','tool':name,'params':{'xml':content}})
			elif name == 'ReadFile':
				write_event({'type':'tool','tool':name,'params':{'contentOfFile':content}})
			elif name == 'WriteFile':
				write_event({'type':'tool','tool':name,'params':{'result':content}})
			else:
				write_event({'type':'tool','tool':name,'params':{'result':content}})
		handle._direct_tool_results = []


class _SSEHandler(BaseHTTPRequestHandler):
	ai_server = None
	
	def do_GET(self):
		if self.path == '/health':
			self._send_json(200, {"status":"ok"})
		elif self.path == '/' or self.path == '/api':
			self._send_json(200, self._get_api_index())
		else:
			self.send_response(404)
			self.end_headers()
	
	def _get_api_index(self):
		"""Return API index with available endpoints."""
		return {
			'service': 'AIIA Agentic AI',
			'version': self.ai_server.Options.get('VERSION', '0.0.0') if self.ai_server else 'unknown',
			'profile': 'HTTP',
			'endpoints': [
				{'method': 'GET',  'path': '/',         'description': 'This index'},
				{'method': 'GET',  'path': '/health',   'description': 'Health check'},
				{'method': 'POST', 'path': '/chat',     'description': 'Send message, receive SSE stream of AI tokens'},
				{'method': 'POST', 'path': '/execute',  'description': 'Direct tool execution (no AI)'},
			],
			'links': {
				'chat':    'POST /chat    {"message":"your text"}',
				'execute': 'POST /execute {"tool":"<ToolName>...</ToolName>"}',
			},
		}
	
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
			self._send_json(400, {"error":"invalid JSON"})
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
	
	def _send_json(self, status_code, data):
		self.send_response(status_code)
		self.send_header('Content-Type', 'application/json; charset=UTF-8')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		self.wfile.write(json.dumps(data).encode('utf-8'))
	
	def _handle_execute(self):
		handle = self.ai_server.handle if self.ai_server else None
		if not handle or not hasattr(handle, 'hTP'):
			self._send_json(503, {
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
			self._send_json(400, {
				'success': False,
				'error': 'Invalid JSON'
			})
			return
		#
		tool_xml = data.get('tool', '')
		if not tool_xml:
			self._send_json(400, {
				'success': False,
				'error': 'Missing "tool" field'
			})
			return
		#
		tool_name = ''
		try:
			invocations = handle.hTP.ParseTextToolInvocation(tool_xml)
			if not invocations:
				self._send_json(400, {
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
			self._send_json(200, {
				'success': not is_error,
				'tool': tool_name,
				'result': str(result) if result else '',
			})
		except Exception as e:
			self._send_json(500, {
				'success': False,
				'tool': tool_name or 'unknown',
				'error': str(e),
			})
	
	def log_message(self, format, *args):
		pass


class HTTP(ServerProfile):
	"""HTTP SSE Server — default AIIA API server for editor clients and AI tools."""
	
	name = "HTTP"
	description = "HTTP SSE server with /chat, /execute, /health endpoints"
	default_port = 9877
	
	@classmethod
	def create_server(cls, host, port, Options):
		server = OurAIServer(host, port, Options)
		server.start()
		return server
	
	@classmethod
	def get_endpoints(cls):
		return [
			{'method': 'GET',  'path': '/',         'description': 'API index with available endpoints'},
			{'method': 'GET',  'path': '/health',   'description': 'Health check returning {"status":"ok"}'},
			{'method': 'POST', 'path': '/chat',     'description': 'Send message (JSON), receive SSE stream of AI tokens'},
			{'method': 'POST', 'path': '/execute',  'description': 'Direct tool execution via XML, returns JSON result'},
		]
