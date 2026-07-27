"""HTTP SSE Server Profile — default AIIA server."""

import sys
import json, os, threading, base64, mimetypes, time, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from server_profiles._ServerBase import ServerProfile
from src.functions import *
from src.EventBus import EventBus


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
		self._ai_lock = threading.Lock()
		self.global_auth_enabled = Options.get("SERVER_AUTH_ENABLED", False)
		self.global_username = Options.get("SERVER_USERNAME", "admin")
		self.global_password = Options.get("SERVER_PASSWORD", "aiia")
		self.project_root = Options.get("working_dir", os.getcwd())
		self.event_bus = EventBus()
		self._clients = {}  # client_id -> {name, type, connected_at, last_seen}
	
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
		
		return {"success": True, "entries": files, "path": path or ".", "project_root": effective_root}
	
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
	
	def append_file(self, path, content, root=None):
		"""Append content to a file."""
		safe_path = self._get_safe_path(path, root=root)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		try:
			os.makedirs(os.path.dirname(safe_path), exist_ok=True)
			with open(safe_path, 'a', encoding='utf-8') as f:
				f.write(content)
			size = os.path.getsize(safe_path)
			return {"success": True, "path": path, "size": size}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def replace_lines(self, path, from_line, to_line, replacement, root=None):
		"""Replace specific line range in a file."""
		safe_path = self._get_safe_path(path, root=root)
		if safe_path is None:
			return {"error": "Access denied", "success": False}
		if not os.path.exists(safe_path):
			return {"error": "File not found", "success": False}
		try:
			with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
				lines = f.readlines()
			total = len(lines)
			f_idx = max(0, from_line - 1)
			t_idx = min(total, to_line)
			new_lines = replacement.split('\n')
			if new_lines and new_lines[-1] == '':
				new_lines = new_lines[:-1]
			result_lines = lines[:f_idx] + [l + '\n' for l in new_lines] + lines[t_idx:]
			with open(safe_path, 'w', encoding='utf-8') as f:
				f.writelines(result_lines)
			return {"success": True, "path": path, "lines_replaced": t_idx - f_idx, "new_total": len(result_lines)}
		except (OSError, IOError) as e:
			return {"error": str(e), "success": False}
	
	def delete_file(self, path, root=None):
		"""Delete a file."""
		safe_path = self._get_safe_path(path, root=root)
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
			return {"success": True, "path": path, "deleted": True}
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

	def register_client(self, client_name="", client_type="unknown"):
		"""Register a new client, returns client_id."""
		client_id = "client_{}".format(uuid.uuid4().hex[:8])
		session_id = "sess_{}".format(uuid.uuid4().hex[:8])
		with self._lock:
			self._clients[client_id] = {
				"name": client_name or client_id,
				"type": client_type,
				"connected_at": time.time(),
				"last_seen": time.time(),
				"session_id": session_id,
			}
		self.event_bus.publish({
			"type": "client_joined",
			"client_id": client_id,
			"client_name": client_name,
			"client_type": client_type,
		})
		return client_id

	def unregister_client(self, client_id):
		"""Remove a client."""
		info = None
		with self._lock:
			info = self._clients.pop(client_id, None)
		self.event_bus.unsubscribe(client_id)
		if info:
			self.event_bus.publish({
				"type": "client_left",
				"client_id": client_id,
				"client_name": info.get("name", client_id),
			})

	def get_clients(self):
		"""Return list of connected clients."""
		with self._lock:
			return dict(self._clients)

	def get_history(self, limit=100):
		"""Return conversation history from Handle."""
		if self.handle is None:
			return []
		msgs = self.handle.hHM.msgs
		result = []
		for msg in msgs[-limit:]:
			entry = {"role": msg.get("role", "unknown")}
			content = msg.get("content", "")
			if isinstance(content, str):
				entry["content"] = content[:2000]
			elif isinstance(content, list):
				entry["content"] = content
			result.append(entry)
		return result
	
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
			resp = {"status": "ok", "project_root": self.ai_server.project_root}
			try:
				from config import Options as _Opts
				resp["version"] = _Opts.get("VERSION", "unknown")
			except Exception:
				pass
			self._send_json(200, resp)
			return
		
		if self.path.startswith('/api/files/list'):
			self._handle_file_list()
			return
		
		if self.path.startswith('/api/files/read'):
			self._handle_file_read()
			return
		
		if self.path.startswith('/events'):
			self._handle_events()
			return
		
		if self.path.startswith('/history'):
			self._handle_history()
			return
		
		if self.path.startswith('/sessions'):
			self._handle_sessions()
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
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Project-Path')
		self.end_headers()
	
	def do_DELETE(self):
		"""Handle DELETE requests."""
		try:
			self._do_DELETE_impl()
		except Exception as e:
			self._log_err("ERROR in do_DELETE: {}".format(e))
			import traceback
			traceback.print_exc(file=sys.stderr)
			try:
				self.send_response(500)
				self.end_headers()
			except:
				pass
	
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
		elif self.path == '/api/files/append':
			self._handle_file_append(data)
		elif self.path == '/api/files/replace':
			self._handle_file_replace(data)
		elif self.path == '/execute':
			self._handle_execute(data)
		elif self.path == '/register':
			self._handle_register(data)
		elif self.path == '/unregister':
			self._handle_unregister(data)
		elif self.path == '/history/clear':
			self._handle_history_clear(data)
		else:
			self._send_json(404, {'error': 'Unknown endpoint'})
	
	def _handle_chat(self, data):
		"""Handle chat requests with SSE streaming."""
		try:
			message = data.get('message', '')
			client_id = data.get('client_id', '')
			if not message:
				self._send_json(400, {'error': 'Missing message'})
				return
			
			# Broadcast chat_started
			if client_id:
				self.ai_server.event_bus.publish({
					"type": "chat_started",
					"client_id": client_id,
					"message": message[:200],
				})
			
			# Stream response
			self._send_sse_stream(message, client_id=client_id)
				
		except Exception as e:
			self._log_err("ERROR in _handle_chat: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_file_write(self, data):
		"""Handle file write requests."""
		try:
			path = data.get('path', '')
			content = data.get('content', '')
			client_id = data.get('client_id', '')
			if not path:
				self._send_json(400, {'error': 'Missing path'})
				return
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.write_file(path, content, root=root_override)
			success = result.get('success', False)

			# Broadcast file_written
			if success and client_id:
				self.ai_server.event_bus.publish({
					"type": "file_written",
					"client_id": client_id,
					"path": path,
					"size": len(content),
				})

			self._send_json(200 if success else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_file_write: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_file_append(self, data):
		"""Handle file append requests."""
		try:
			path = data.get('path', '')
			content = data.get('content', '')
			client_id = data.get('client_id', '')
			if not path:
				self._send_json(400, {'error': 'Missing path'})
				return
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.append_file(path, content, root=root_override)
			success = result.get('success', False)

			if success and client_id:
				self.ai_server.event_bus.publish({
					"type": "file_appended",
					"client_id": client_id,
					"path": path,
					"size": len(content),
				})

			self._send_json(200 if success else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_file_append: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_file_replace(self, data):
		"""Handle line-range replace requests. Accepts both formats:
		  {"path": "...", "from_line": N, "to_line": M, "content": "..."}
		  {"path": "...", "lines": [N, M], "content": "..."}
		"""
		try:
			path = data.get('path', '')
			replacement = data.get('content', '')
			client_id = data.get('client_id', '')
			if not path:
				self._send_json(400, {'error': 'Missing path'})
				return
			# Accept lines array or separate from_line/to_line
			lines = data.get('lines')
			if lines and isinstance(lines, list) and len(lines) >= 2:
				from_line = int(lines[0])
				to_line = int(lines[1])
			else:
				from_line = int(data.get('from_line', 1))
				to_line = int(data.get('to_line', from_line))
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.replace_lines(path, from_line, to_line, replacement, root=root_override)
			success = result.get('success', False)
			# Add operation field for editor compatibility
			if 'success' in result:
				result['operation'] = 'replaced' if success else 'failed'

			if success and client_id:
				self.ai_server.event_bus.publish({
					"type": "file_replaced",
					"client_id": client_id,
					"path": path,
					"from_line": from_line,
					"to_line": to_line,
				})

			self._send_json(200 if success else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_file_replace: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_history_clear(self, data):
		"""Clear conversation history."""
		try:
			if not data.get("confirmed"):
				return self._send_json(400, {'error': 'Confirmation required (confirmed=true)'})
			if self.ai_server.handle:
				self.ai_server.handle.hHM.msgs = []
			self._send_json(200, {"success": True, "message": "History cleared"})
		except Exception as e:
			self._send_json(500, {'error': str(e)})
	
	def _do_DELETE_impl(self):
		"""Handle DELETE requests."""
		if not self._check_auth():
			self._send_json(401, {'error': 'Unauthorized'})
			return
		
		if self.path.startswith('/api/files/delete'):
			self._handle_file_delete()
		else:
			self.send_response(404)
			self.end_headers()
	
	def _handle_file_delete(self):
		"""Handle file delete requests."""
		try:
			from urllib.parse import urlparse, parse_qs
			parsed = urlparse(self.path)
			params = parse_qs(parsed.query)
			path = params.get('path', [''])[0]
			if not path:
				self._send_json(400, {'error': 'Missing path parameter'})
				return
			root_override = self.headers.get('X-Project-Path')
			result = self.ai_server.delete_file(path, root=root_override)
			self._send_json(200 if result.get('success') else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_file_delete: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _handle_execute(self, data):
		"""Handle tool execution requests."""
		try:
			tool_xml = data.get('tool', '')
			client_id = data.get('client_id', '')
			if not tool_xml:
				self._send_json(400, {'error': 'Missing tool XML'})
				return

			# Broadcast tool_started
			if client_id:
				self.ai_server.event_bus.publish({
					"type": "tool_started",
					"client_id": client_id,
					"tool_xml": tool_xml[:500],
				})

			result = self.ai_server.execute_tool(tool_xml)
			success = result.get('success', False)

			# Broadcast tool_completed
			if client_id:
				self.ai_server.event_bus.publish({
					"type": "tool_completed",
					"client_id": client_id,
					"success": success,
				})

			self._send_json(200 if success else 500, result)
		except Exception as e:
			self._log_err("ERROR in _handle_execute: {}".format(e))
			self._send_json(500, {'error': str(e)})
	
	def _send_sse_stream(self, message, client_id=""):
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

		def broadcast_or_sse(event):
			sse_write(event)
			if client_id:
				# Broadcast to other subscribers (not back to sender via bus)
				self.ai_server.event_bus.publish(event)
		
		try:
			with self.ai_server._ai_lock:
				handle.Response('user', {'content': message})
				handle.AI(opts={'stream_callback': broadcast_or_sse})
			sse_write({'type': 'done'})
			if client_id:
				self.ai_server.event_bus.publish({
					"type": "chat_done",
					"client_id": client_id,
				})
		except BrokenPipeError:
			pass
		except Exception as e:
			self._log_err("ERROR in SSE stream: {}".format(e))
			sse_write({'type': 'error', 'message': str(e)})
	
	def _handle_events(self):
		"""Handle persistent SSE event stream for a client."""
		from urllib.parse import urlparse, parse_qs
		parsed = urlparse(self.path)
		params = parse_qs(parsed.query)
		client_id = params.get('client_id', [''])[0]
		
		if not client_id:
			self._send_json(400, {'error': 'Missing client_id parameter'})
			return
		
		# Send headers
		self.send_response(200)
		self.send_header('Content-Type', 'text/event-stream')
		self.send_header('Cache-Control', 'no-cache')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		
		def sse_write(event):
			try:
				self.wfile.write('data: {}\n\n'.format(json.dumps(event)).encode('utf-8'))
				self.wfile.flush()
			except Exception:
				pass
		
		# Subscribe to event bus
		q = self.ai_server.event_bus.subscribe(client_id)
		
		# Send recent history first
		history = self.ai_server.event_bus.get_history(limit=20)
		for event in history:
			sse_write(event)
		
		# Keep connection alive, forwarding events
		try:
			while True:
				try:
					event = q.get(timeout=30)
					sse_write(event)
				except Exception:
					# Send keepalive comment
					self.wfile.write(b': keepalive\n\n')
					self.wfile.flush()
		except (BrokenPipeError, ConnectionResetError):
			pass
		finally:
			self.ai_server.event_bus.unsubscribe(client_id, q)

	def _handle_history(self):
		"""Return conversation history."""
		from urllib.parse import urlparse, parse_qs
		parsed = urlparse(self.path)
		params = parse_qs(parsed.query)
		limit = int(params.get('limit', ['100'])[0])
		offset = int(params.get('offset', ['0'])[0])
		result = self.ai_server.get_history(limit=limit)
		total = len(result)
		# Apply offset
		result = result[offset:offset + limit] if offset else result
		self._send_json(200, {"messages": result, "total": total, "limit": limit, "offset": offset})

	def _handle_sessions(self):
		"""Return active sessions info."""
		clients = self.ai_server.get_clients()
		result = {
			"clients": clients,
			"client_count": len(clients),
			"subscriber_count": self.ai_server.event_bus.get_subscriber_count(),
		}
		self._send_json(200, result)

	def _handle_register(self, data):
		"""Register a new client."""
		client_name = data.get('name', '')
		client_type = data.get('type', 'unknown')
		client_id = self.ai_server.register_client(client_name, client_type)
		client_info = self.ai_server._clients.get(client_id, {})
		self._send_json(200, {
			"client_id": client_id,
			"name": client_name or client_id,
			"type": client_type,
			"session_id": client_info.get("session_id", ""),
		})

	def _handle_unregister(self, data):
		"""Unregister a client."""
		client_id = data.get('client_id', '')
		if not client_id:
			self._send_json(400, {'error': 'Missing client_id'})
			return
		self.ai_server.unregister_client(client_id)
		self._send_json(200, {"status": "unregistered"})
	
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
