"""HTTP SSE Server Profile — default AIIA server.

Endpoints:
  GET  /health                    — {"status":"ok"}
  POST /chat                      — SSE stream of AI tokens
  POST /execute                   — Direct tool execution (no AI)
  
  File API (Project files via HTTP):
  GET  /api/files/list          — List files in project
  GET  /api/files/read          — Read file content
  POST /api/files/write         — Write/overwrite file
  POST /api/files/create        — Create new file
  DELETE /api/files/delete      — Delete file
  POST /api/files/rename        — Rename/move file

This is the standard server for editor clients, AI tools, and API consumers.
Uses stdlib http.server + ThreadingMixIn — no external deps.

Authentication:
  Per-project Basic Auth via .aiia/auth.json in each project directory
  Falls back to global SERVER_AUTH_* settings if project has no auth file
"""

import json, sys, os, threading, base64, mimetypes
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
	Serves project files via /api/files/* endpoints.
	"""
	
	def __init__(self, host, port, Options):
		self.host = host
		self.port = port
		self.Options = Options
		self.handle = None
		self._lock = threading.Lock()
		# Global fallback auth settings
		self.global_auth_enabled = Options.get("SERVER_AUTH_ENABLED", False)
		self.global_username = Options.get("SERVER_USERNAME", "admin")
		self.global_password = Options.get("SERVER_PASSWORD", "aiia")
		# Project root (where files are served from)
		self.project_root = Options.get("working_dir", os.getcwd())
	
	def _load_project_auth(self, project_path):
		"""Load authentication credentials from project's .aiia/auth.json.
		
		Returns: (enabled, username, password) or (False, None, None) if no auth
		"""
		if not project_path or not os.path.isdir(project_path):
			return (self.global_auth_enabled, self.global_username, self.global_password)
		
		auth_file = os.path.join(project_path, ".aiia", "auth.json")
		if not os.path.exists(auth_file):
			# No project-specific auth, use global settings
			return (self.global_auth_enabled, self.global_username, self.global_password)
		
		try:
			with open(auth_file, 'r', encoding='utf-8') as f:
				auth_data = json.load(f)
			enabled = auth_data.get('enabled', True)
			username = auth_data.get('username', '')
			password = auth_data.get('password', '')
			return (enabled, username, password)
		except (json.JSONDecodeError, IOError, KeyError) as e:
			# Error reading auth file, deny access
			print(f"Warning: Error reading auth file for {project_path}: {e}")
			return (True, None, None)  # Auth required but invalid
	
	def _build_auth_hash(self, username, password):
		"""Build expected Authorization header value for Basic Auth."""
		credentials = f"{username}:{password}"
		return base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
	
	def check_auth(self, headers, project_path=None):
		"""Check if request is authenticated for the specified project.
		
		Args:
			headers: HTTP headers dict
			project_path: Optional project path from X-Project-Path header
			
		Returns:
			(True, None) if authenticated or no auth required
			(False, error_message) if authentication failed
		"""
		# Load project-specific or global auth settings
		enabled, expected_user, expected_pass = self._load_project_auth(project_path)
		
		if not enabled:
			return (True, None)
		
		# Auth required but no valid credentials configured
		if not expected_user or not expected_pass:
			return (False, "Authentication required but credentials not configured")
		
		auth_header = headers.get('Authorization', '')
		if not auth_header.startswith('Basic '):
			return (False, "Basic authentication required")
		
		provided_hash = auth_header[6:]  # Remove "Basic " prefix
		expected_hash = self._build_auth_hash(expected_user, expected_pass)
		
		if provided_hash != expected_hash:
			return (False, "Invalid credentials")
		
		return (True, None)
	
	def send_auth_challenge(self, handler, message="Authentication required"):
		"""Send 401 Unauthorized response with WWW-Authenticate header."""
		handler.send_response(401)
		handler.send_header('WWW-Authenticate', 'Basic realm="AIIA Server"')
		handler.send_header('Content-Type', 'application/json')
		handler.end_headers()
		handler.wfile.write(json.dumps({
			"error": "Unauthorized",
			"message": message
		}).encode('utf-8'))
	
	def _get_safe_path(self, requested_path):
		"""Get safe absolute path within project root."""
		# Normalize and make absolute
		if requested_path.startswith('/'):
			requested_path = requested_path[1:]
		
		full_path = os.path.abspath(os.path.join(self.project_root, requested_path))
		
		# Security check: ensure path is within project root
		if not full_path.startswith(os.path.abspath(self.project_root)):
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
	
	def list_files(self, path="", recursive=False):
		"""List files in project directory."""
		safe_path = self._get_safe_path(path or ".")
		if safe_path is None or not os.path.exists(safe_path):
			return {"error": "Path not found"}
		
		if not os.path.isdir(safe_path):
			return {"error": "Not a directory"}
		
		files = []
		
		if recursive:
			for root, dirs, filenames in os.walk(safe_path):
				# Skip hidden dirs and common noise
				dirs[:] = [d for d in dirs if not d.startswith('.') 
						  and d not in ('__pycache__', 'node_modules', '.venv', '.git')]
				for filename in filenames:
					full = os.path.join(root, filename)
					rel = os.path.relpath(full, self.project_root)
					info = self._file_to_dict(full, rel)
					if info:
						files.append(info)
		else:
			try:
				items = os.listdir(safe_path)
				for item in sorted(items):
					if item.startswith('.'):
						continue
					full = os.path.join(safe_path, item)
					rel = os.path.relpath(full, self.project_root)
					info = self._file_to_dict(full, rel)
					if info:
						files.append(info)
			except (OSError, IOError) as e:
				return {"error": str(e)}
		
		return {"files": files, "path": path or ".", "project_root": self.project_root}
	
	def read_file(self, path):
		"""Read file content."""
		safe_path = self._get_safe_path(path)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		
		if not os.path.exists(safe_path):
			return {"error": "File not found", "success": False}
		
		if os.path.isdir(safe_path):
			return {"error": "Is a directory", "success": False}
		
		try:
			with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
				content = f.read()
			
			# Detect language for syntax highlighting hint
			ext = os.path.splitext(path)[1].lower()
			lang_map = {
				'.py': 'python', '.js': 'javascript', '.ts': 'typescript',
				'.json': 'json', '.md': 'markdown', '.html': 'html',
				'.css': 'css', '.sh': 'bash', '.yml': 'yaml', '.yaml': 'yaml'
			}
			
			return {
				"success": True,
				"content": content,
				"path": path,
				"size": len(content),
				"language": lang_map.get(ext, 'text')
			}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def write_file(self, path, content, create_only=False):
		"""Write or create file."""
		safe_path = self._get_safe_path(path)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		
		if create_only and os.path.exists(safe_path):
			return {"error": "File already exists", "success": False}
		
		try:
			# Ensure parent directory exists
			parent = os.path.dirname(safe_path)
			if parent and not os.path.exists(parent):
				os.makedirs(parent, exist_ok=True)
			
			with open(safe_path, 'w', encoding='utf-8') as f:
				f.write(content)
			
			return {
				"success": True,
				"path": path,
				"size": len(content),
				"created": not os.path.exists(safe_path)
			}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def delete_file(self, path):
		"""Delete file or directory."""
		safe_path = self._get_safe_path(path)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		
		if not os.path.exists(safe_path):
			return {"error": "File not found", "success": False}
		
		try:
			if os.path.isdir(safe_path):
				import shutil
				shutil.rmtree(safe_path)
			else:
				os.remove(safe_path)
			return {"success": True, "path": path}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def rename_file(self, old_path, new_path):
		"""Rename/move file."""
		safe_old = self._get_safe_path(old_path)
		safe_new = self._get_safe_path(new_path)
		
		if safe_old is None or safe_new is None:
			return {"error": "Access denied", "success": False}
		
		if not os.path.exists(safe_old):
			return {"error": "Source not found", "success": False}
		
		if os.path.exists(safe_new):
			return {"error": "Destination already exists", "success": False}
		
		try:
			# Ensure parent directory exists
			parent = os.path.dirname(safe_new)
			if parent and not os.path.exists(parent):
				os.makedirs(parent, exist_ok=True)
			
			os.rename(safe_old, safe_new)
			return {"success": True, "old_path": old_path, "new_path": new_path}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
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
		print("  📁 Project root: {}".format(self.project_root))
		print("  🔐 Per-project authentication: ENABLED")
		print("  Global fallback: {}".format("ENABLED" if self.global_auth_enabled else "DISABLED"))
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
	
	def _get_project_path(self):
		"""Extract project path from X-Project-Path header."""
		return self.headers.get('X-Project-Path', self.ai_server.project_root if self.ai_server else None)
	
	def _check_auth(self):
		"""Check authentication and send 401 if needed."""
		project_path = self._get_project_path()
		authenticated, error_msg = self.ai_server.check_auth(self.headers, project_path)
		
		if not authenticated:
			self.ai_server.send_auth_challenge(self, error_msg)
			return False
		return True
	
	def _send_json(self, status_code, data):
		self.send_response(status_code)
		self.send_header('Content-Type', 'application/json; charset=UTF-8')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		self.wfile.write(json.dumps(data).encode('utf-8'))
	
	def _get_request_body(self):
		"""Read and parse JSON request body."""
		content_length = int(self.headers.get('Content-Length', 0))
		if content_length == 0:
			return {}
		body = self.rfile.read(content_length)
		try:
			return json.loads(body.decode('utf-8'))
		except (json.JSONDecodeError, UnicodeDecodeError):
			return None
	
	def do_GET(self):
		# Check auth for all endpoints
		if not self._check_auth():
			return
		
		# File API endpoints
		if self.path.startswith('/api/files/list'):
			self._handle_file_list()
		elif self.path.startswith('/api/files/read'):
			self._handle_file_read()
		# Legacy endpoints
		elif self.path == '/health':
			self._send_json(200, {"status":"ok"})
		elif self.path == '/' or self.path == '/api':
			self._send_json(200, self._get_api_index())
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_file_list(self):
		"""Handle GET /api/files/list?path=...&recursive=true"""
		from urllib.parse import urlparse, parse_qs
		parsed = urlparse(self.path)
		params = parse_qs(parsed.query)
		
		path = params.get('path', [''])[0]
		recursive = params.get('recursive', ['false'])[0].lower() == 'true'
		
		result = self.ai_server.list_files(path, recursive)
		if "error" in result:
			self._send_json(404 if result["error"] == "Path not found" else 400, result)
		else:
			self._send_json(200, result)
	
	def _handle_file_read(self):
		"""Handle GET /api/files/read?path=..."""
		from urllib.parse import urlparse, parse_qs
		parsed = urlparse(self.path)
		params = parse_qs(parsed.query)
		
		path = params.get('path', [''])[0]
		if not path:
			self._send_json(400, {"error": "Missing path parameter", "success": False})
			return
		
		result = self.ai_server.read_file(path)
		if not result.get("success"):
			self._send_json(404 if "not found" in result.get("error", "") else 400, result)
		else:
			self._send_json(200, result)
	
	def do_POST(self):
		# Check auth for all endpoints
		if not self._check_auth():
			return
		
		# File API endpoints
		if self.path == '/api/files/write':
			self._handle_file_write()
		elif self.path == '/api/files/create':
			self._handle_file_create()
		elif self.path == '/api/files/rename':
			self._handle_file_rename()
		# AI endpoints
		elif self.path == '/chat':
			self._handle_chat()
		elif self.path == '/execute':
			self._handle_execute()
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_file_write(self):
		"""Handle POST /api/files/write {path, content}"""
		data = self._get_request_body()
		if data is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		path = data.get('path', '')
		content = data.get('content', '')
		
		if not path:
			self._send_json(400, {"error": "Missing path", "success": False})
			return
		
		result = self.ai_server.write_file(path, content, create_only=False)
		self._send_json(200 if result.get("success") else 400, result)
	
	def _handle_file_create(self):
		"""Handle POST /api/files/create {path, content}"""
		data = self._get_request_body()
		if data is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		path = data.get('path', '')
		content = data.get('content', '')
		
		if not path:
			self._send_json(400, {"error": "Missing path", "success": False})
			return
		
		result = self.ai_server.write_file(path, content, create_only=True)
		self._send_json(201 if result.get("success") else 400, result)
	
	def _handle_file_rename(self):
		"""Handle POST /api/files/rename {old_path, new_path}"""
		data = self._get_request_body()
		if data is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		old_path = data.get('old_path', '')
		new_path = data.get('new_path', '')
		
		if not old_path or not new_path:
			self._send_json(400, {"error": "Missing old_path or new_path", "success": False})
			return
		
		result = self.ai_server.rename_file(old_path, new_path)
		self._send_json(200 if result.get("success") else 400, result)
	
	def do_DELETE(self):
		# Check auth for all endpoints
		if not self._check_auth():
			return
		
		if self.path == '/api/files/delete':
			self._handle_file_delete()
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_file_delete(self):
		"""Handle DELETE /api/files/delete {path}"""
		data = self._get_request_body()
		if data is None:
			# Try to get from query string
			from urllib.parse import urlparse, parse_qs
			parsed = urlparse(self.path)
			params = parse_qs(parsed.query)
			path = params.get('path', [''])[0]
		else:
			path = data.get('path', '')
		
		if not path:
			self._send_json(400, {"error": "Missing path", "success": False})
			return
		
		result = self.ai_server.delete_file(path)
		self._send_json(200 if result.get("success") else 400, result)
	
	def _get_api_index(self):
		"""Return API index with available endpoints."""
		project_path = self._get_project_path()
		auth_info = "per-project"
		if self.ai_server:
			enabled, user, _ = self.ai_server._load_project_auth(project_path)
			auth_info = "required" if enabled else "disabled"
		
		return {
			'service': 'AIIA Agentic AI',
			'version': self.ai_server.Options.get('VERSION', '0.0.0') if self.ai_server else 'unknown',
			'profile': 'HTTP',
			'authentication': auth_info,
			'auth_method': 'Basic Auth with X-Project-Path header',
			'endpoints': [
				{'method': 'GET',  'path': '/',         'description': 'This index'},
				{'method': 'GET',  'path': '/health',   'description': 'Health check'},
				{'method': 'POST', 'path': '/chat',     'description': 'Send message, receive SSE stream of AI tokens'},
				{'method': 'POST', 'path': '/execute',  'description': 'Direct tool execution (no AI)'},
				# File API
				{'method': 'GET',  'path': '/api/files/list',   'description': 'List files in project directory'},
				{'method': 'GET',  'path': '/api/files/read',   'description': 'Read file content'},
				{'method': 'POST', 'path': '/api/files/write',  'description': 'Write/overwrite file'},
				{'method': 'POST', 'path': '/api/files/create', 'description': 'Create new file (fails if exists)'},
				{'method': 'POST', 'path': '/api/files/rename', 'description': 'Rename/move file'},
				{'method': 'DELETE','path': '/api/files/delete', 'description': 'Delete file or directory'},
			],
			'headers': {
				'Authorization': 'Basic base64(username:password)',
				'X-Project-Path': '/path/to/project (optional, uses server default)',
			},
			'links': {
				'chat':    'POST /chat    {"message":"your text"}',
				'execute': 'POST /execute {"tool":"<ToolName>...</ToolName>"}',
			},
		}
	
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
	description = "HTTP SSE server with /chat, /execute, /health, and file API endpoints (per-project Basic Auth)"
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
			# File API
			{'method': 'GET',  'path': '/api/files/list',   'description': 'List files in project directory'},
			{'method': 'GET',  'path': '/api/files/read',   'description': 'Read file content'},
			{'method': 'POST', 'path': '/api/files/write',  'description': 'Write/overwrite file'},
			{'method': 'POST', 'path': '/api/files/create', 'description': 'Create new file'},
			{'method': 'POST', 'path': '/api/files/rename', 'description': 'Rename/move file'},
			{'method': 'DELETE','path': '/api/files/delete', 'description': 'Delete file or directory'},
		]
