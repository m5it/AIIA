"""HTTP SSE Server Profile — default AIIA server."""

import sys
import json, os, threading, base64, mimetypes, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from server_profiles._ServerBase import ServerProfile
from src.functions import *


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	allow_reuse_address = True


class OurAIServer():
	"""HTTP SSE server that wraps the AIIA Handle."""
	
	def __init__(self, host, port, Options):
		self.host = host
		self.port = port
		self.Options = Options
		self.handle = None
		self._lock = threading.Lock()
		self.global_auth_enabled = Options.get("SERVER_AUTH_ENABLED", False)
		self.global_username = Options.get("SERVER_USERNAME", "admin")
		self.global_password = Options.get("SERVER_PASSWORD", "aiia")
		self.project_root = Options.get("working_dir", os.getcwd())
	
	def _get_safe_path(self, requested_path, root=None):
		"""Get safe absolute path within project root."""
		base_root = root if root else self.project_root
		
		if requested_path.startswith('/'):
			requested_path = requested_path[1:]
		
		full_path = os.path.abspath(os.path.join(base_root, requested_path))
		
		if not full_path.startswith(os.path.abspath(base_root)):
			return None
		
		return full_path
	
	def _file_to_dict(self, full_path, rel_path):
		"""Convert file info to dict for API response."""
		try:
			stat = os.stat(full_path)
			is_dir = os.path.isdir(full_path)
			return {
				"path": rel_path,
				"name": os.path.basename(full_path),
				"is_directory": is_dir,
				"size": stat.st_size if not is_dir else None,
				"modified": stat.st_mtime,
				"mime_type": mimetypes.guess_type(full_path)[0] if not is_dir else None
			}
		except (OSError, IOError):
			return None
	
	def list_files(self, path="", recursive=False, root=None):
		"""List files in project directory."""
		effective_root = root if root else self.project_root
		
		safe_path = self._get_safe_path(path or ".", root=root)
		if safe_path is None or not os.path.exists(safe_path):
			return {"error": "Path not found"}
		
		if not os.path.isdir(safe_path):
			return {"error": "Not a directory"}
		
		files = []
		
		try:
			items = os.listdir(safe_path)
			for item in sorted(items):
				if item.startswith('.'):
					continue
				full = os.path.join(safe_path, item)
				rel = os.path.relpath(full, effective_root)
				info = self._file_to_dict(full, rel)
				if info:
					files.append(info)
		except (OSError, IOError) as e:
			return {"error": str(e)}
		
		return {"files": files, "path": path or ".", "project_root": effective_root}
	
	def read_file(self, path, root=None):
		"""Read file content."""
		safe_path = self._get_safe_path(path, root=root)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		
		if not os.path.exists(safe_path):
			return {"error": "File not found", "success": False}
		
		if os.path.isdir(safe_path):
			return {"error": "Is a directory", "success": False}
		
		try:
			with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
				content = f.read()
			
			return {
				"success": True,
				"content": content,
				"path": path,
				"size": len(content),
				"language": "text"
			}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def write_file(self, path, content, root=None):
		"""Write content to a file."""
		safe_path = self._get_safe_path(path, root=root)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		try:
			os.makedirs(os.path.dirname(safe_path), exist_ok=True)
			with open(safe_path, 'w', encoding='utf-8') as f:
				f.write(content)
			return {"success": True, "path": path, "size": len(content)}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def execute_tool(self, tool_xml):
		"""Execute a tool invocation from XML string."""
		handle = self.handle
		if handle is None:
			return {"error": "Handle not initialized", "success": False}
		with self._lock:
			try:
				invocations = handle.hTP.ParseTextToolInvocation(tool_xml)
				if not invocations:
					return {"error": "No tool invocation found in XML", "success": False}
				handle.hTP.FireToolInvocation(invocations)
				return {"success": True}
			except Exception as e:
				return {"error": str(e), "success": False}
	
	def start(self):
		"""Start the server."""
		from src.Handle import Handle
		self.Options['AI_QUICK'] = True
		self.handle = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", self.Options)
		self.handle.Init()
		self.handle.hPP.Prepare()
		
		_SSEHandler.ai_server = self
		server = ThreadedHTTPServer((self.host, self.port), _SSEHandler)
		
		print("\n" + "="*60, file=sys.stderr)
		print("  AIIA server listening on http://{}:{}".format(self.host, self.port), file=sys.stderr)
		print("  Project root: {}".format(self.project_root), file=sys.stderr)
		print("="*60 + "\n", file=sys.stderr)
		
		try:
			server.serve_forever()
		except KeyboardInterrupt:
			print("\nServer shutting down.", file=sys.stderr)
			server.shutdown()


class _SSEHandler(BaseHTTPRequestHandler):
	ai_server = None
	
	def log_message(self, format, *args):
		ts = time.strftime('%H:%M:%S')
		print('[{}] {}'.format(ts, format % args), file=sys.stderr)
	
	def _log_err(self, msg):
		ts = time.strftime('%H:%M:%S')
		print('[{}] {}'.format(ts, msg), file=sys.stderr)
	
	def do_GET(self):
		try:
			self._do_GET_impl()
		except Exception as e:
			self._log_err("ERROR in do_GET: {}".format(e))
			import traceback
			traceback.print_exc(file=sys.stderr)
			try:
				self.send_response(500)
				self.end_headers()
			except:
				pass
	
	def _do_GET_impl(self):
		if not self._check_auth():
			self._send_json(401, {'error': 'Unauthorized'})
			return
		
		if self.path == '/health':
			self._send_json(200, {"status": "ok"})
			return
		
		if self.path.startswith('/api/files/list'):
			self._handle_file_list()
			return
		
		if self.path.startswith('/api/files/read'):
			self._handle_file_read()
			return
		
		self.send_response(404)
		self.end_headers()
	
	def do_POST(self):
		"""Handle POST requests."""
		try:
			self._do_POST_impl()
		except Exception as e:
			self._log_err("ERROR in do_POST: {}".format(e))
			import traceback
			traceback.print_exc(file=sys.stderr)
			try:
				self.send_response(500)
				self.end_headers()
			except:
				pass
	
	def do_OPTIONS(self):
		"""Handle CORS preflight."""
		self.send_response(204)
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Project-Path')
		self.end_headers()
	
	def _do_POST_impl(self):
		"""Implementation of POST handling."""
		if not self._check_auth():
			self._send_json(401, {'error': 'Unauthorized'})
			return
		
		content_len = int(self.headers.get('Content-Length', 0))
		body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else '{}'
		
		try:
			data = json.loads(body)
		except json.JSONDecodeError:
			self._send_json(400, {'error': 'Invalid JSON'})
			return
		
		if self.path == '/chat':
			self._handle_chat(data)
		elif self.path == '/api/files/write':
			self._handle_file_write(data)
		elif self.path == '/execute':
			self._handle_execute(data)
		else:
			self._send_json(404, {'error': 'Unknown endpoint'})
	
	def _handle_chat(self, data):
		"""Handle chat requests with SSE streaming."""
		try:
			message = data.get('message', '')
			if not message:
				self._send_json(400, {'error': 'Missing message'})
				return
			
			# Stream response
			self._send_sse_stream(message)
				
		except Exception as e:
			self._log_err("ERROR in _handle_chat: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_file_write(self, data):
		"""Handle file write requests."""
		try:
			path = data.get('path', '')
			content = data.get('content', '')
			if not path:
				self._send_json(400, {'error': 'Missing path'})
				return
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.write_file(path, content, root=root_override)
			self._send_json(200 if result.get('success') else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_file_write: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_execute(self, data):
		"""Handle tool execution requests."""
		try:
			tool_xml = data.get('tool', '')
			if not tool_xml:
				self._send_json(400, {'error': 'Missing tool XML'})
				return
			result = self.ai_server.execute_tool(tool_xml)
			self._send_json(200 if result.get('success') else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_execute: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _send_sse_stream(self, message):
		"""Send SSE streaming response via Handle AI."""
		self.send_response(200)
		self.send_header('Content-Type', 'text/event-stream')
		self.send_header('Cache-Control', 'no-cache')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		
		handle = self.ai_server.handle
		if handle is None:
			self._send_json(503, {'error': 'Handle not initialized'})
			return
		
		def sse_write(event):
			try:
				self.wfile.write('data: {}\n\n'.format(json.dumps(event)).encode('utf-8'))
				self.wfile.flush()
			except Exception:
				pass
		
		try:
			with self.ai_server._lock:
				handle.Response('user', {'content': message})
				handle.AI(opts={'stream_callback': sse_write})
			sse_write({'type': 'done'})
		except BrokenPipeError:
			pass
		except Exception as e:
			self._log_err("ERROR in SSE stream: {}".format(e))
			sse_write({'type': 'error', 'message': str(e)})
	
	def _check_auth(self):
		"""Check Basic auth header."""
		if not self.ai_server.global_auth_enabled:
			return True
		auth = self.headers.get('Authorization', '')
		if not auth:
			return False
		expected = 'Basic {}'.format(base64.b64encode(
			'{}:{}'.format(self.ai_server.global_username,
			               self.ai_server.global_password).encode()
		).decode())
		return auth == expected
	
	def _send_json(self, status_code, data):
		self.send_response(status_code)
		self.send_header('Content-Type', 'application/json; charset=UTF-8')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		self.wfile.write(json.dumps(data).encode('utf-8'))
	
	def _handle_file_list(self):
		try:
			from urllib.parse import urlparse, parse_qs
			parsed = urlparse(self.path)
			params = parse_qs(parsed.query)
			
			path = params.get('path', [''])[0]
			recursive = params.get('recursive', ['false'])[0].lower() == 'true'
			root_override = self.headers.get('X-Project-Path')
			
			result = self.ai_server.list_files(path, recursive, root=root_override)
			
			if "error" in result:
				self._send_json(404, result)
			else:
				self._send_json(200, result)
				
		except Exception as e:
			self._log_err("ERROR in _handle_file_list: {}".format(e))
			import traceback
			traceback.print_exc(file=sys.stderr)
			self._send_json(500, {"error": str(e)})
	
	def _handle_file_read(self):
		try:
			from urllib.parse import urlparse, parse_qs
			parsed = urlparse(self.path)
			params = parse_qs(parsed.query)
			
			path = params.get('path', [''])[0]
			if not path:
				self._send_json(400, {"error": "Missing path parameter"})
				return
			
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.read_file(path, root=root_override)
			
			if not result.get("success"):
				self._send_json(404, result)
			else:
				self._send_json(200, result)
				
		except Exception as e:
			self._log_err("ERROR in _handle_file_read: {}".format(e))
			self._send_json(500, {"error": str(e)})


class HTTPServerWrapper:
	"""Wrapper for serve_forever interface."""
	
	def __init__(self, our_server):
		self.our_server = our_server
		self._thread = None
		self._running = False
		
	def serve_forever(self):
		import threading
		self._running = True
		self._thread = threading.Thread(target=self._run_server, daemon=True)
		self._thread.start()
		import time
		try:
			while self._running:
				time.sleep(0.1)
		except KeyboardInterrupt:
			pass
		
	def _run_server(self):
		try:
			self.our_server.start()
		except Exception as e:
			print("[HTTP] ERROR in server thread: {}".format(e), file=sys.stderr)
			import traceback
			traceback.print_exc(file=sys.stderr)
		finally:
			self._running = False
		
	def shutdown(self):
		self._running = False


class HTTP(ServerProfile):
	"""HTTP Server Profile for AIIA."""
	
	name = "HTTP"
	description = "HTTP SSE server for AIIA editor clients"
	default_port = 9877
	
	@classmethod
	def create_server(cls, host, port, Options):
		server = OurAIServer(host, port, Options)
		return HTTPServerWrapper(server)
	
	def run(self, host, port, Options):
		server = OurAIServer(host, port, Options)
		server.start()
