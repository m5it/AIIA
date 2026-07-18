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
	"""HTTP SSE server that wraps the AIIA Handle."""
	
	def __init__(self, host, port, Options):
		print(f"DEBUG: OurAIServer.__init__ host={host}, port={port}")
		self.host = host
		self.port = port
		self.Options = Options
		self.handle = None
		self._lock = threading.Lock()
		self.global_auth_enabled = Options.get("SERVER_AUTH_ENABLED", False)
		self.global_username = Options.get("SERVER_USERNAME", "admin")
		self.global_password = Options.get("SERVER_PASSWORD", "aiia")
		self.project_root = Options.get("working_dir", os.getcwd())
		print(f"DEBUG: project_root={self.project_root}")
	
	def _load_project_auth(self, project_path):
		"""Load authentication credentials from project's .aiia/auth.json."""
		if not project_path or not os.path.isdir(project_path):
			return (self.global_auth_enabled, self.global_username, self.global_password)
		
		auth_file = os.path.join(project_path, ".aiia", "auth.json")
		if not os.path.exists(auth_file):
			return (self.global_auth_enabled, self.global_username, self.global_password)
		
		try:
			with open(auth_file, 'r', encoding='utf-8') as f:
				auth_data = json.load(f)
			enabled = auth_data.get('enabled', True)
			username = auth_data.get('username', '')
			password = auth_data.get('password', '')
			return (enabled, username, password)
		except (json.JSONDecodeError, IOError, KeyError) as e:
			print(f"Warning: Error reading auth file for {project_path}: {e}")
			return (True, None, None)
	
	def _build_auth_hash(self, username, password):
		"""Build expected Authorization header value for Basic Auth."""
		credentials = f"{username}:{password}"
		return base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
	
	def check_auth(self, headers, project_path=None):
		"""Check if request is authenticated for the specified project."""
		enabled, expected_user, expected_pass = self._load_project_auth(project_path)
		
		if not enabled:
			return (True, None)
		
		if not expected_user or not expected_pass:
			return (False, "Authentication required but credentials not configured")
		
		auth_header = headers.get('Authorization', '')
		if not auth_header.startswith('Basic '):
			return (False, "Basic authentication required")
		
		provided_hash = auth_header[6:]
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
		
		if recursive:
			for root_dir, dirs, filenames in os.walk(safe_path):
				dirs[:] = [d for d in dirs if not d.startswith('.') 
						  and d not in ('__pycache__', 'node_modules', '.venv', '.git')]
				for filename in filenames:
					full = os.path.join(root_dir, filename)
					rel = os.path.relpath(full, effective_root)
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
		
	def start(self):
		"""Start the server."""
		print("DEBUG: OurAIServer.start() called")
		try:
			from src.Handle import Handle
			print("DEBUG: Importing Handle...")
			self.Options['AI_QUICK'] = True
			print("DEBUG: Creating handle...")
			self.handle = initmodule(importmodule("Handle",True,{'path':'src'}),"Handle", self.Options)
			print("DEBUG: Initializing handle...")
			self.handle.Init()
			print("DEBUG: Preparing handle...")
			self.handle.hPP.Prepare()
			print("DEBUG: Handle ready")
			
			_SSEHandler.ai_server = self
			print(f"DEBUG: Creating ThreadedHTTPServer on {self.host}:{self.port}")
			server = ThreadedHTTPServer((self.host, self.port), _SSEHandler)
			
			print("\n" + "="*60)
			print("  {} server listening on http://{}:{}".format(
				self.Options.get('VERSION_NAME', 'AIIA'), self.host, self.port))
			print("  📁 Project root: {}".format(self.project_root))
			print("  🔐 Per-project authentication: ENABLED")
			print("  Global fallback: {}".format("ENABLED" if self.global_auth_enabled else "DISABLED"))
			print("  Connect with: run.py --connect {}:{}".format(self.host, self.port))
			print("  API docs:     GET http://{}:{}/".format(self.host, self.port))
			print("="*60 + "\n")
			
			print("DEBUG: About to call server.serve_forever()...")
			try:
				server.serve_forever()
				print("DEBUG: serve_forever() returned normally")
			except KeyboardInterrupt:
				print("\nServer shutting down.")
				server.shutdown()
			except Exception as e:
				print(f"DEBUG: Exception in serve_forever: {e}")
				import traceback
				traceback.print_exc()
				raise
				
		except Exception as e:
			print(f"DEBUG: Exception in start(): {e}")
			import traceback
			traceback.print_exc()
			raise
			
		except KeyboardInterrupt:
			print("\nServer shutting down.")
			server.shutdown()
		except Exception as e:
			print(f"DEBUG: Exception in start(): {e}")
			import traceback
			traceback.print_exc()
			raise
	
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
		
		# Get optional root override from header
		root_override = self.headers.get('X-Project-Path')
		
		result = self.ai_server.list_files(path, recursive, root=root_override)
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
		
		# Get optional root override from header
		root_override = self.headers.get('X-Project-Path')
		
		result = self.ai_server.read_file(path, root=root_override)
		if not result.get("success"):
			self._send_json(404 if result.get("error") == "File not found" else 400, result)
		else:
			self._send_json(200, result)
	
	def _get_api_index(self):
		"""Return API documentation."""
		return {
			"name": "AIIA HTTP Server",
			"endpoints": {
				"GET /health": "Health check",
				"POST /chat": "Chat with AI (SSE stream)",
				"POST /execute": "Execute tools directly",
				"GET /api/files/list?path=...": "List files",
				"GET /api/files/read?path=...": "Read file",
				"POST /api/files/write": "Write file",
				"POST /api/files/create": "Create file",
				"POST /api/files/rename": "Rename file",
				"DELETE /api/files/delete": "Delete file"
			},
			"headers": {
				"Authorization": "Basic auth (optional)",
				"X-Project-Path": "Project path override (optional)"
			}
		}
	
	def do_POST(self):
		# Check auth
		if not self._check_auth():
			return
		
		if self.path == '/chat':
			self._handle_chat()
		elif self.path == '/execute':
			self._handle_execute()
		elif self.path == '/api/files/write':
			self._handle_file_write()
		elif self.path == '/api/files/create':
			self._handle_file_create()
		elif self.path == '/api/files/rename':
			self._handle_file_rename()
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_chat(self):
		"""Handle POST /chat with SSE streaming."""
		body = self._get_request_body()
		if body is None:
			self.send_response(400)
			self.end_headers()
			return
			
		message = body.get('message', '')
		
		self.send_response(200)
		self.send_header('Content-Type', 'text/event-stream')
	def _handle_file_list(self):
		"""Handle GET /api/files/list?path=...&recursive=true"""
		from urllib.parse import urlparse, parse_qs
		parsed = urlparse(self.path)
		params = parse_qs(parsed.query)
		
		path = params.get('path', [''])[0]
		recursive = params.get('recursive', ['false'])[0].lower() == 'true'
		
		# Get optional root override from header
		root_override = self.headers.get('X-Project-Path')
		print(f"DEBUG: X-Project-Path header = {root_override}")
		print(f"DEBUG: Using path = {path}")
		
		result = self.ai_server.list_files(path, recursive, root=root_override)
	
	def _handle_execute(self):
		"""Handle POST /execute for direct tool calls."""
		body = self._get_request_body()
		if body is None:
			self.send_response(400)
			self.end_headers()
			return
		
		tool_xml = body.get('tool', '')
		
		# Import and execute tool
		from src.tools import ToolManager
		tm = ToolManager(self.ai_server.handle.hParams)
		result = tm.run(tool_xml)
		
		self._send_json(200, {"result": result})
	
	def _handle_file_write(self):
		"""Handle POST /api/files/write"""
		body = self._get_request_body()
		if body is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		path = body.get('path', '')
		content = body.get('content', '')
		
		if not path:
			self._send_json(400, {"error": "Missing path", "success": False})
			return
		
		result = self.ai_server.write_file(path, content)
		self._send_json(200 if result.get("success") else 400, result)
	
	def _handle_file_create(self):
		"""Handle POST /api/files/create"""
		body = self._get_request_body()
		if body is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		path = body.get('path', '')
		content = body.get('content', '')
		
		if not path:
			self._send_json(400, {"error": "Missing path", "success": False})
			return
		
		result = self.ai_server.write_file(path, content, create_only=True)
		self._send_json(200 if result.get("success") else 400, result)
	
	def _handle_file_rename(self):
		"""Handle POST /api/files/rename"""
		body = self._get_request_body()
		if body is None:
			self._send_json(400, {"error": "Invalid JSON", "success": False})
			return
		
		old_path = body.get('old_path', '')
		new_path = body.get('new_path', '')
		
		if not old_path or not new_path:
			self._send_json(400, {"error": "Missing old_path or new_path", "success": False})
			return
		
		result = self.ai_server.rename_file(old_path, new_path)
		self._send_json(200 if result.get("success") else 400, result)
	
	def do_DELETE(self):
		# Check auth
		if not self._check_auth():
			return
		
		if self.path.startswith('/api/files/delete'):
			self._handle_file_delete()
		else:
			self.send_response(404)
			self.end_headers()
	
class HTTPServerWrapper:
	"""Wrapper that provides serve_forever/shutdown interface for OurAIServer."""
	
	def __init__(self, our_server):
		print("DEBUG: HTTPServerWrapper.__init__ called")
		self.our_server = our_server
		self._thread = None
		self._running = False
		
	def serve_forever(self):
		"""Start server in a thread and block."""
		print("DEBUG: HTTPServerWrapper.serve_forever called")
		import threading
		self._running = True
		print(f"DEBUG: _running = {self._running}")
		
		self._thread = threading.Thread(target=self._our_server_start, daemon=True)
		self._thread.start()
		print(f"DEBUG: Thread started")
		
		# Block until shutdown
		import time
		try:
			print("DEBUG: Entering wait loop")
			while self._running:
				time.sleep(0.1)
			print("DEBUG: Exited wait loop (_running is False)")
		except KeyboardInterrupt:
			print("\nDEBUG: KeyboardInterrupt received")
		except Exception as e:
			print(f"DEBUG: Exception in wait loop: {e}")
			import traceback
			traceback.print_exc()
		
		print("DEBUG: serve_forever returning")
		
	def _our_server_start(self):
		"""Wrapper to catch exceptions."""
		print("DEBUG: _our_server_start started")
		try:
			self.our_server.start()
			print("DEBUG: our_server.start() returned normally")
		except Exception as e:
			print(f"DEBUG: Server error in thread: {e}")
			import traceback
			traceback.print_exc()
		finally:
			print("DEBUG: Setting _running = False")
			self._running = False
		
	def shutdown(self):
		"""Shutdown the server."""
		print("DEBUG: shutdown called")
		self._running = False
		
	def _our_server_start(self):
		"""Wrapper to catch exceptions."""
		try:
			self.our_server.start()
		except Exception as e:
			print(f"DEBUG: Server error in thread: {e}")
			import traceback
			traceback.print_exc()
		
	def shutdown(self):
		"""Shutdown the server."""
		print("DEBUG: shutdown called")
		pass


class HTTP(ServerProfile):
	"""HTTP Server Profile for AIIA."""
	
	name = "HTTP"
	description = "HTTP SSE server for AIIA editor clients"
	default_port = 9877
	
	@classmethod
	def create_server(cls, host, port, Options):
		"""Create and return HTTP server instance."""
		print(f"DEBUG: HTTP.create_server called host={host}, port={port}")
		try:
			server = OurAIServer(host, port, Options)
			print(f"DEBUG: OurAIServer created, project_root={server.project_root}")
			return HTTPServerWrapper(server)
		except Exception as e:
			print(f"DEBUG: Error creating server: {e}")
			import traceback
			traceback.print_exc()
			raise
	
	def run(self, host, port, Options):
		"""Run the server (legacy method)."""
		print(f"DEBUG: HTTP.run called")
		server = OurAIServer(host, port, Options)
		server.start()
