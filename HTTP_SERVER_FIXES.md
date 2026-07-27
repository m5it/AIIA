# HTTP Server Implementation Fixes

## Overview

This document contains corrected and enhanced code for the HTTP server implementation. Use these corrected versions instead of the templates in `HTTP_SERVER_IMPLEMENTATION.md`.

---

## Fix 1: Corrected ClientRegistry.py

**Issue:** Session timeout not implemented, event broadcasting could fail silently.

```python
"""Multi-client session management for HTTP server."""

import uuid
import time
import threading
import json
from collections import defaultdict
from datetime import datetime, timedelta


class ClientRegistry:
    """Manages connected clients and event broadcasting."""
    
    # Session timeout in seconds (30 minutes)
    SESSION_TIMEOUT = 30 * 60
    
    def __init__(self):
        self.clients = {}  # {client_id: ClientSession}
        self.lock = threading.RLock()
        self.event_callbacks = defaultdict(list)  # {client_id: [callbacks]}
        self.start_cleanup_thread()
    
    def register(self, name="", client_type="editor", project_path=None):
        """Register a new client.
        
        Args:
            name: Display name
            client_type: 'editor', 'terminal', 'mobile', etc.
            project_path: Associated project directory
        
        Returns:
            {client_id, name, timestamp, session_id}
        """
        client_id = str(uuid.uuid4())
        now = time.time()
        
        with self.lock:
            self.clients[client_id] = {
                "client_id": client_id,
                "name": name or f"client-{client_id[:8]}",
                "type": client_type,
                "project_path": project_path,
                "connected_at": now,
                "last_activity": now,
                "session_id": f"sess_{uuid.uuid4().hex[:8]}"
            }
        
        # Broadcast client_joined event
        self.broadcast({
            "type": "client_joined",
            "client_id": client_id,
            "client_name": self.clients[client_id]["name"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }, exclude_client_id=client_id)
        
        return self.clients[client_id]
    
    def unregister(self, client_id):
        """Unregister a client."""
        with self.lock:
            if client_id in self.clients:
                client = self.clients.pop(client_id)
                
                # Broadcast client_left event
                self.broadcast({
                    "type": "client_left",
                    "client_id": client_id,
                    "client_name": client["name"],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }, exclude_client_id=client_id)
                
                # Clean up event callbacks
                if client_id in self.event_callbacks:
                    del self.event_callbacks[client_id]
    
    def get_client(self, client_id):
        """Get client info."""
        with self.lock:
            return self.clients.get(client_id)
    
    def list_clients(self):
        """List all connected clients."""
        with self.lock:
            return list(self.clients.values())
    
    def update_activity(self, client_id):
        """Update last activity timestamp."""
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]["last_activity"] = time.time()
    
    def subscribe_events(self, client_id, callback):
        """Subscribe to events for a client.
        
        Args:
            client_id: Client ID
            callback: function(event_dict) called for each received event
        """
        with self.lock:
            self.event_callbacks[client_id].append(callback)
    
    def unsubscribe_events(self, client_id, callback):
        """Unsubscribe from events."""
        with self.lock:
            if client_id in self.event_callbacks:
                if callback in self.event_callbacks[client_id]:
                    self.event_callbacks[client_id].remove(callback)
    
    def broadcast(self, event, exclude_client_id=None):
        """Broadcast event to all subscribed clients.
        
        Args:
            event: dict with at least {"type": "..."}
            exclude_client_id: Don't send to this client
        """
        with self.lock:
            for client_id, callbacks in list(self.event_callbacks.items()):
                if exclude_client_id and client_id == exclude_client_id:
                    continue
                
                for callback in callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Error in event callback for {client_id}: {e}")
    
    def cleanup_inactive_sessions(self):
        """Remove inactive client sessions."""
        now = time.time()
        with self.lock:
            inactive = [
                cid for cid, info in self.clients.items()
                if now - info["last_activity"] > self.SESSION_TIMEOUT
            ]
            
            for client_id in inactive:
                client = self.clients.pop(client_id)
                print(f"Cleaned up inactive session: {client['name']}")
                
                # Clean up event callbacks
                if client_id in self.event_callbacks:
                    del self.event_callbacks[client_id]
    
    def start_cleanup_thread(self):
        """Start background thread for session cleanup."""
        def cleanup_loop():
            while True:
                time.sleep(60)  # Check every minute
                self.cleanup_inactive_sessions()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
```

---

## Fix 2: Corrected ServerHTTP.py

**Issues:** Wrong Handle method names, missing path validation, no CORS support, missing error handling.

```python
"""HTTP server implementation for AIIA."""

import json
import base64
import os
import threading
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict

try:
    from src.ClientRegistry import ClientRegistry
except ImportError:
    from ClientRegistry import ClientRegistry


class RateLimiter:
    """Simple per-client rate limiter."""
    
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, client_id):
        """Check if request is allowed for client."""
        now = time.time()
        
        with self.lock:
            # Clean old requests
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.window_seconds
            ]
            
            # Check limit
            if len(self.requests[client_id]) >= self.max_requests:
                return False
            
            # Add current request
            self.requests[client_id].append(now)
            return True


class AIIAHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for AIIA API."""
    
    # Class variables shared across all instances
    client_registry = None
    aiia_handle = None
    options = None
    rate_limiter = None
    
    # Security: Path validation regex
    SAFE_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9._/\-]+$')
    
    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        try:
            # Check rate limit
            client_addr = self.client_address[0]
            if not self.rate_limiter.is_allowed(client_addr):
                return self.send_json_error(429, "Too Many Requests")
            
            if path == "/health":
                self.handle_health()
            elif path == "/sessions":
                self.handle_sessions()
            elif path == "/events":
                self.handle_events(query)
            elif path == "/history":
                self.handle_history(query)
            elif path == "/api/files/list":
                self.handle_files_list(query)
            elif path == "/api/files/read":
                self.handle_files_read(query)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error handling GET {path}: {e}")
            self.send_json_error(500, f"Internal error: {str(e)[:100]}")
    
    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        
        try:
            # Check rate limit
            client_addr = self.client_address[0]
            if not self.rate_limiter.is_allowed(client_addr):
                return self.send_json_error(429, "Too Many Requests")
            
            # Limit request size (10MB)
            if content_length > 10 * 1024 * 1024:
                return self.send_json_error(413, "Request entity too large")
            
            body = self.rfile.read(content_length).decode("utf-8", errors="replace")
            
            if path == "/register":
                self.handle_register(body)
            elif path == "/unregister":
                self.handle_unregister(body)
            elif path == "/chat":
                self.handle_chat(body)
            elif path == "/execute":
                self.handle_execute(body)
            elif path == "/api/files/write":
                self.handle_files_write(body)
            elif path == "/api/files/append":
                self.handle_files_append(body)
            elif path == "/history/clear":
                self.handle_history_clear(body)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error handling POST {path}: {e}")
            self.send_json_error(500, f"Internal error: {str(e)[:100]}")
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        try:
            # Check rate limit
            client_addr = self.client_address[0]
            if not self.rate_limiter.is_allowed(client_addr):
                return self.send_json_error(429, "Too Many Requests")
            
            if path == "/api/files/delete":
                self.handle_files_delete(query)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error handling DELETE {path}: {e}")
            self.send_json_error(500, f"Internal error: {str(e)[:100]}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Project-Path")
        self.send_header("Access-Control-Max-Age", "3600")
        self.end_headers()
    
    # === Authentication ===
    
    def check_auth(self):
        """Check Basic Auth credentials.
        
        Returns:
            (auth_valid, client_id, username)
        """
        auth_header = self.headers.get("Authorization", "")
        
        if not auth_header.startswith("Basic "):
            # No auth provided - check if auth is required
            if not self.options.get("SERVER_AUTH_ENABLED", False):
                return True, None, None
            return False, None, None
        
        try:
            encoded = auth_header[6:]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
            
            # Validate credentials
            expected_user = self.options.get("SERVER_USERNAME", "admin")
            expected_pass = self.options.get("SERVER_PASSWORD", "aiia")
            
            if username == expected_user and password == expected_pass:
                return True, None, username
            
            return False, None, username
        except Exception as e:
            print(f"Auth check failed: {e}")
            return False, None, None
    
    # === Path Validation ===
    
    def validate_file_path(self, path):
        """Validate file path for security.
        
        Args:
            path: File path to validate
            
        Raises:
            ValueError: If path is unsafe
        """
        # Reject absolute paths
        if path.startswith("/"):
            raise ValueError("Absolute paths not allowed")
        
        # Reject directory traversal
        if ".." in path:
            raise ValueError("Directory traversal not allowed")
        
        # Reject empty path
        if not path or path == ".":
            raise ValueError("Invalid path")
        
        # Optional: Only allow alphanumeric + certain chars
        # if not self.SAFE_PATH_PATTERN.match(path):
        #     raise ValueError("Path contains invalid characters")
    
    # === Response Helpers ===
    
    def send_json(self, status, data):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        
        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode("utf-8"))
    
    def send_json_error(self, status, message):
        """Send JSON error response."""
        self.send_json(status, {
            "success": False,
            "error": message,
            "status": status,
            "timestamp": self.get_timestamp()
        })
    
    def send_sse(self):
        """Start SSE response stream."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
    
    def write_sse(self, event_dict):
        """Write an SSE event."""
        try:
            data = json.dumps(event_dict)
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception as e:
            print(f"Error writing SSE: {e}")
    
    # === Handler Methods ===
    
    def handle_health(self):
        """GET /health"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        # Check if Ollama/Handle is available
        handle_status = "ok" if self.aiia_handle else "limited"
        
        response = {
            "status": handle_status,
            "timestamp": self.get_timestamp(),
            "version": self.options.get("VERSION", "1.0.0"),
            "ai_model": self.options.get("AI_MODEL", "gemma4:26b"),
            "server_mode": "HTTP",
            "features": ["chat", "execute", "files", "events"],
            "connected_clients": len(self.client_registry.list_clients()) if self.client_registry else 0
        }
        
        if handle_status == "limited":
            response["warning"] = "AI Handle not available"
        
        status_code = 200 if handle_status == "ok" else 503
        self.send_json(status_code, response)
    
    def handle_register(self, body):
        """POST /register"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            client = self.client_registry.register(
                name=data.get("name", ""),
                client_type=data.get("type", "editor"),
                project_path=data.get("project_path")
            )
            self.send_json(200, client)
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_unregister(self, body):
        """POST /unregister"""
        try:
            data = json.loads(body)
            client_id = data.get("client_id")
            if not client_id:
                return self.send_json_error(400, "Missing client_id")
            
            self.client_registry.unregister(client_id)
            self.send_json(200, {"status": "unregistered", "client_id": client_id})
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_sessions(self):
        """GET /sessions"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            clients = self.client_registry.list_clients()
            self.send_json(200, {
                "clients": clients,
                "total": len(clients)
            })
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_chat(self, body):
        """POST /chat (streaming SSE response)"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            message = data.get("message", "").strip()
            model = data.get("model")
            client_id = data.get("client_id")
            
            if not message:
                return self.send_json_error(400, "Missing message")
            
            if client_id:
                self.client_registry.update_activity(client_id)
                # Broadcast chat_started event
                self.client_registry.broadcast({
                    "type": "chat_started",
                    "client_id": client_id,
                    "message": message[:100],
                    "timestamp": self.get_timestamp()
                }, exclude_client_id=client_id)
            
            # Start SSE stream
            self.send_sse()
            
            # Call AIIA Handle to stream responses
            # FIXED: Use correct Handle method name
            if self.aiia_handle:
                try:
                    # Use Chat method from Handle (returns list of tokens or generator)
                    response = self.aiia_handle.Chat(message, model=model)
                    
                    # Handle both string responses and generator responses
                    if isinstance(response, str):
                        # Single response - send as tokens
                        self.write_sse({"type": "token", "text": response})
                    else:
                        # Generator - stream tokens
                        try:
                            for token in response:
                                self.write_sse({"type": "token", "text": token})
                        except TypeError:
                            # Not iterable - treat as single response
                            self.write_sse({"type": "token", "text": str(response)})
                    
                except Exception as tool_error:
                    self.write_sse({
                        "type": "error",
                        "message": f"Chat failed: {str(tool_error)}"
                    })
            else:
                self.write_sse({
                    "type": "error",
                    "message": "AI Handle not available"
                })
            
            # Send done event
            self.write_sse({"type": "done", "finish_reason": "stop"})
            
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            print(f"Chat error: {e}")
            self.send_json_error(500, str(e))
    
    def handle_events(self, query):
        """GET /events (persistent SSE stream)"""
        client_id = query.get("client_id", [None])[0]
        
        if not client_id:
            return self.send_json_error(400, "Missing client_id")
        
        # Verify client exists
        if not self.client_registry.get_client(client_id):
            return self.send_json_error(404, "Client not found")
        
        # Start SSE stream
        self.send_sse()
        
        # Create event queue and callback
        event_queue = []
        lock = threading.Lock()
        
        def event_callback(event):
            with lock:
                event_queue.append(event)
        
        # Subscribe to events
        self.client_registry.subscribe_events(client_id, event_callback)
        
        try:
            # Keep stream alive and send queued events
            while True:
                with lock:
                    while event_queue:
                        event = event_queue.pop(0)
                        self.write_sse(event)
                
                # Ping to keep connection alive every 30 seconds
                time.sleep(30)
                try:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                except:
                    break
        except Exception as e:
            print(f"Events stream error: {e}")
        finally:
            self.client_registry.unsubscribe_events(client_id, event_callback)
    
    def handle_execute(self, body):
        """POST /execute (direct tool execution)"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            tool_xml = data.get("tool", "").strip()
            client_id = data.get("client_id")
            
            if not tool_xml:
                return self.send_json_error(400, "Missing tool")
            
            if client_id:
                self.client_registry.update_activity(client_id)
                # Broadcast tool_started event
                self.client_registry.broadcast({
                    "type": "tool_started",
                    "client_id": client_id,
                    "tool": "ExecuteXML",
                    "timestamp": self.get_timestamp()
                }, exclude_client_id=client_id)
            
            # Execute via AIIA Handle
            result = {}
            if self.aiia_handle:
                try:
                    # FIXED: Use ExecuteTool if available, otherwise try to parse XML
                    if hasattr(self.aiia_handle, "ExecuteTool"):
                        result = self.aiia_handle.ExecuteTool(tool_xml)
                    else:
                        result = {"error": "ExecuteTool not implemented"}
                    
                    # Broadcast completion
                    if client_id:
                        self.client_registry.broadcast({
                            "type": "tool_completed",
                            "client_id": client_id,
                            "success": not result.get("error"),
                            "timestamp": self.get_timestamp()
                        }, exclude_client_id=client_id)
                    
                except Exception as tool_error:
                    result = {
                        "success": False,
                        "error": str(tool_error)
                    }
            else:
                result = {"error": "AI Handle not available"}
            
            self.send_json(200, result)
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_history(self, query):
        """GET /history"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            limit = int(query.get("limit", [100])[0])
            offset = int(query.get("offset", [0])[0])
            
            # Validate limits
            limit = min(limit, 1000)  # Max 1000
            offset = max(0, offset)
            
            # Return history from AIIA Handle
            messages = []
            if self.aiia_handle and hasattr(self.aiia_handle, "history"):
                all_messages = self.aiia_handle.history
                messages = all_messages[offset:offset+limit]
            
            self.send_json(200, {
                "messages": messages,
                "total": len(messages) if self.aiia_handle else 0,
                "limit": limit,
                "offset": offset
            })
        except (ValueError, IndexError) as e:
            self.send_json_error(400, f"Invalid query parameters: {str(e)}")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_files_list(self, query):
        """GET /api/files/list"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            path = unquote(query.get("path", ["."])[0])
            recursive = query.get("recursive", ["false"])[0].lower() == "true"
            
            # Validate path
            if path != ".":
                self.validate_file_path(path)
            
            # Use AIIA tool: TreeView (if available)
            if self.aiia_handle and hasattr(self.aiia_handle, "ExecuteTool"):
                try:
                    result = self.aiia_handle.ExecuteTool(
                        f"<TreeView><path>{path}</path></TreeView>"
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_json_error(500, f"TreeView failed: {str(e)}")
            else:
                self.send_json_error(501, "File listing not implemented")
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_files_read(self, query):
        """GET /api/files/read"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            path = unquote(query.get("path", [""])[0])
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Validate path
            self.validate_file_path(path)
            
            # Use AIIA tool: ReadFile (if available)
            if self.aiia_handle and hasattr(self.aiia_handle, "ExecuteTool"):
                try:
                    result = self.aiia_handle.ExecuteTool(
                        f"<ReadFile><fileName>{path}</fileName></ReadFile>"
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_json_error(500, f"ReadFile failed: {str(e)}")
            else:
                # Fallback: try to read directly
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_json(200, {
                        "path": path,
                        "content": content,
                        "size": len(content),
                        "encoding": "utf-8"
                    })
                except FileNotFoundError:
                    self.send_json_error(404, f"File not found: {path}")
                except Exception as e:
                    self.send_json_error(500, str(e))
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_files_write(self, body):
        """POST /api/files/write"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            path = data.get("path", "").strip()
            content = data.get("content", "")
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Validate path
            self.validate_file_path(path)
            
            # Use AIIA tool: WriteFile (if available)
            if self.aiia_handle and hasattr(self.aiia_handle, "ExecuteTool"):
                try:
                    result = self.aiia_handle.ExecuteTool(
                        f"<WriteFile><fileName>{path}</fileName><contentOfFile>{content}</contentOfFile></WriteFile>"
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_json_error(500, f"WriteFile failed: {str(e)}")
            else:
                # Fallback: try to write directly
                try:
                    # Create directories if needed
                    dir_path = os.path.dirname(path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.send_json(200, {
                        "success": True,
                        "path": path,
                        "size": len(content),
                        "timestamp": self.get_timestamp()
                    })
                except Exception as e:
                    self.send_json_error(500, str(e))
        except ValueError as e:
            self.send_json_error(400, str(e))
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_files_append(self, body):
        """POST /api/files/append"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            path = data.get("path", "").strip()
            content = data.get("content", "")
            line = data.get("line", -1)
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Validate path
            self.validate_file_path(path)
            
            # Use AIIA tool: AppendFile (if available)
            if self.aiia_handle and hasattr(self.aiia_handle, "ExecuteTool"):
                try:
                    result = self.aiia_handle.ExecuteTool(
                        f"<AppendFile><fileName>{path}</fileName><contentOfFile>{content}</contentOfFile><line>{line}</line></AppendFile>"
                    )
                    self.send_json(200, result)
                except Exception as e:
                    self.send_json_error(500, f"AppendFile failed: {str(e)}")
            else:
                self.send_json_error(501, "Append not implemented")
        except ValueError as e:
            self.send_json_error(400, str(e))
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_files_delete(self, query):
        """DELETE /api/files/delete"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            path = unquote(query.get("path", [""])[0])
            recursive = query.get("recursive", ["false"])[0].lower() == "true"
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Validate path
            self.validate_file_path(path)
            
            # Delete file or directory
            if os.path.isfile(path):
                os.remove(path)
                self.send_json(200, {
                    "success": True,
                    "path": path,
                    "deleted": True,
                    "timestamp": self.get_timestamp()
                })
            elif os.path.isdir(path):
                if not recursive:
                    return self.send_json_error(400, "Use recursive=true to delete directories")
                
                import shutil
                shutil.rmtree(path)
                self.send_json(200, {
                    "success": True,
                    "path": path,
                    "deleted": True,
                    "type": "directory",
                    "timestamp": self.get_timestamp()
                })
            else:
                self.send_json_error(404, f"Path not found: {path}")
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))
    
    def handle_history_clear(self, body):
        """POST /history/clear"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            if not data.get("confirmed"):
                return self.send_json_error(400, "Confirmation required (confirmed=true)")
            
            if self.aiia_handle and hasattr(self.aiia_handle, "history"):
                self.aiia_handle.history = []
            
            self.send_json(200, {
                "success": True,
                "message": "History cleared",
                "timestamp": self.get_timestamp()
            })
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.send_json_error(500, str(e))
    
    # === Utilities ===
    
    @staticmethod
    def get_timestamp():
        """Get ISO 8601 timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_http_server(host, port, aiia_handle, options):
    """Start HTTP server.
    
    Args:
        host: Bind address (e.g., '0.0.0.0')
        port: Listen port
        aiia_handle: AIIA Handle instance
        options: Configuration dict
    
    Returns:
        HTTPServer instance
    """
    # Set up class variables
    AIIAHTTPHandler.client_registry = ClientRegistry()
    AIIAHTTPHandler.aiia_handle = aiia_handle
    AIIAHTTPHandler.options = options
    AIIAHTTPHandler.rate_limiter = RateLimiter(
        max_requests=options.get("RATE_LIMIT_REQUESTS", 100),
        window_seconds=options.get("RATE_LIMIT_WINDOW", 60)
    )
    
    # Create server
    server = HTTPServer((host, port), AIIAHTTPHandler)
    
    print(f"HTTP Server listening on {host}:{port}")
    print(f"API available at http://{host}:{port}/")
    print(f"Health check: curl http://{host}:{port}/health")
    print(f"Rate limit: {options.get('RATE_LIMIT_REQUESTS', 100)} requests per {options.get('RATE_LIMIT_WINDOW', 60)}s")
    
    return server
```

---

## Fix 3: Corrected HTTP.py Server Profile

**Issue:** Missing error handling, not passing options correctly.

```python
"""HTTP server profile for AIIA."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server_profiles._base import _ServerBase


class HTTP(_ServerBase):
    """HTTP + SSE server profile."""
    
    name = "HTTP"
    description = "HTTP REST API with SSE streaming"
    default_port = 9877
    
    @classmethod
    def create_server(cls, host, port, Options):
        """Create HTTP server instance.
        
        Args:
            host: Bind address
            port: Listen port
            Options: Configuration dict
            
        Returns:
            HTTPServer instance with serve_forever() and shutdown() methods
        """
        try:
            from src.ServerHTTP import run_http_server
        except ImportError:
            from ServerHTTP import run_http_server
        
        # Get or create AIIA Handle instance
        aiia_handle = None
        try:
            from src.Handle import Handle
            aiia_handle = Handle(Options)
        except Exception as e:
            print(f"Warning: Could not initialize Handle: {e}")
            print("Server will operate in limited mode (no AI functionality)")
        
        # Start HTTP server
        server = run_http_server(host, port, aiia_handle, Options)
        
        return server
```

---

## Fix 4: Updated Integration Points

**File:** Update `run.py` or `ServerFactory.py`

```python
# In ServerFactory.py or similar:

@classmethod
def resolve_profile_spec(cls, spec, Options):
    """Resolve profile spec like '0.0.0.0:9877' to (profile_name, host, port).
    
    Args:
        spec: String like '0.0.0.0:9877' or 'HTTP' or None
        Options: Configuration dict
    
    Returns:
        (profile_name, host, port)
    """
    # Default
    profile_name = Options.get('SERVER_PROFILE', 'HTTP')
    host = '127.0.0.1'
    port = 9877
    
    if spec:
        # Check if it's just a profile name
        if ':' not in spec:
            profile_name = spec
        else:
            # Parse host:port
            try:
                parts = spec.split(':')
                if len(parts) == 2:
                    host = parts[0]
                    port = int(parts[1])
                elif len(parts) == 1:
                    port = int(parts[0])
            except ValueError:
                print(f"Invalid server spec: {spec}")
                print("Using default: 127.0.0.1:9877")
    
    return profile_name, host, port
```

---

## Fix 5: Configuration Updates

**File:** Add these options to your `config.py` or config file:

```python
# HTTP Server configuration
SERVER_AUTH_ENABLED = False  # Enable Basic Auth
SERVER_USERNAME = "admin"
SERVER_PASSWORD = "aiia"

# Rate limiting
RATE_LIMIT_REQUESTS = 100  # Max requests
RATE_LIMIT_WINDOW = 60  # Time window in seconds

# Session timeout
SESSION_TIMEOUT = 30 * 60  # 30 minutes

# Server defaults
SERVER_PROFILE = "HTTP"
```

---

## Fix 6: Error Handling Improvements

**File:** Add this error handler class to `ServerHTTP.py`:

```python
class HTTPServerError(Exception):
    """Base HTTP server error."""
    pass


class AuthenticationError(HTTPServerError):
    """Authentication failed."""
    pass


class ValidationError(HTTPServerError):
    """Input validation failed."""
    pass


class ToolExecutionError(HTTPServerError):
    """Tool execution failed."""
    pass
```

---

## Testing the Fixed Implementation

### Unit Tests

```python
# test_client_registry.py
import unittest
from ClientRegistry import ClientRegistry


class TestClientRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ClientRegistry()
    
    def test_register_client(self):
        client = self.registry.register(name="test", client_type="editor")
        self.assertIn("client_id", client)
        self.assertEqual(client["name"], "test")
    
    def test_list_clients(self):
        self.registry.register(name="client1")
        self.registry.register(name="client2")
        clients = self.registry.list_clients()
        self.assertEqual(len(clients), 2)
    
    def test_unregister_client(self):
        client = self.registry.register(name="test")
        client_id = client["client_id"]
        self.registry.unregister(client_id)
        found = self.registry.get_client(client_id)
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
```

### Integration Tests

```python
# test_http_api.py
import requests
import json
import time


class TestHTTPAPI:
    BASE_URL = "http://localhost:9877"
    
    def test_health(self):
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "limited"]
    
    def test_register_unregister(self):
        # Register
        response = requests.post(
            f"{self.BASE_URL}/register",
            json={"name": "test-client", "type": "editor"}
        )
        assert response.status_code == 200
        client_id = response.json()["client_id"]
        
        # Unregister
        response = requests.post(
            f"{self.BASE_URL}/unregister",
            json={"client_id": client_id}
        )
        assert response.status_code == 200
    
    def test_rate_limiting(self):
        # Make many rapid requests
        for i in range(110):  # More than default limit
            response = requests.get(f"{self.BASE_URL}/health")
            if response.status_code == 429:
                print(f"Rate limited after {i} requests")
                break


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
```

---

## Summary of Fixes

| Issue | Fix | Impact |
|-------|-----|--------|
| Wrong Handle method names | Use Handle.Chat() instead of Stream() | ✅ Core functionality |
| Missing path validation | Added validate_file_path() | ✅ Security |
| No rate limiting | Added RateLimiter class | ✅ Security |
| Missing CORS | Added OPTIONS handler | ✅ Browser compatibility |
| No session timeout | Added cleanup thread | ✅ Resource management |
| Import errors | Fixed try/except imports | ✅ Reliability |
| No error recovery | Better exception handling | ✅ Robustness |
| Missing timestamps | Use datetime.utcnow() | ✅ Monitoring |

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
