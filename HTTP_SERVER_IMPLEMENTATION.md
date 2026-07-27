# AIIA HTTP Server Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the HTTP server profile for AIIA. The implementation uses Python's `http.server` module with SSE (Server-Sent Events) streaming for real-time chat responses.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Server (Port 9877)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │  RequestHandler  │  │  ClientRegistry  │              │
│  │  - GET /health   │  │  - Register      │              │
│  │  - POST /chat    │  │  - Unregister    │              │
│  │  - POST /execute │  │  - List sessions │              │
│  │  - GET /events   │  │  - Broadcast     │              │
│  │  - File APIs     │  │                  │              │
│  └──────────────────┘  └──────────────────┘              │
│           │                       │                       │
│           └───────────┬───────────┘                       │
│                       ▼                                   │
│           ┌──────────────────────┐                       │
│           │   Handle (AIIA Core) │                       │
│           │  - Chat loop         │                       │
│           │  - Tool execution    │                       │
│           │  - File I/O          │                       │
│           └──────────────────────┘                       │
│                       │                                   │
│                       ▼                                   │
│           ┌──────────────────────┐                       │
│           │   Ollama (LLM)       │                       │
│           └──────────────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
AIIA/
├── server_profiles/
│   ├── __init__.py
│   ├── _base.py              # Base class for all server profiles
│   └── HTTP.py               # HTTP server implementation
├── src/
│   ├── ServerHTTP.py         # RequestHandler and server logic
│   └── ClientRegistry.py     # Client session management
└── API_SPEC.md               # This spec
```

---

## Step 1: Base Server Class

Create `server_profiles/_base.py`:

```python
"""Base class for server profiles."""

from abc import ABC, abstractmethod


class _ServerBase(ABC):
    """Base class for all server profiles (HTTP, WebSocket, etc.)"""
    
    name = "Base"
    description = "Base server profile"
    default_port = 9877
    
    @classmethod
    def get_info(cls):
        """Return profile metadata."""
        return {
            "name": cls.name,
            "description": cls.description,
            "default_port": cls.default_port
        }
    
    @classmethod
    @abstractmethod
    def create_server(cls, host, port, Options):
        """Create and return a server instance.
        
        Args:
            host: str — bind address (e.g., '0.0.0.0')
            port: int — listen port
            Options: dict — configuration from config.py
        
        Returns:
            Server object with:
            - serve_forever() — blocking call
            - shutdown() — stop server
        """
        raise NotImplementedError
```

---

## Step 2: Client Registry

Create `src/ClientRegistry.py`:

```python
"""Multi-client session management for HTTP server."""

import uuid
import time
import threading
import json
from collections import defaultdict


class ClientRegistry:
    """Manages connected clients and event broadcasting."""
    
    def __init__(self):
        self.clients = {}  # {client_id: ClientSession}
        self.lock = threading.RLock()
        self.event_callbacks = defaultdict(list)  # {client_id: [callbacks]}
    
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        })
        
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
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
    
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
            callback: function(event_dict) called for each event
        """
        with self.lock:
            self.event_callbacks[client_id].append(callback)
    
    def unsubscribe_events(self, client_id, callback):
        """Unsubscribe from events."""
        with self.lock:
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
                        print(f"Error in event callback: {e}")
```

---

## Step 3: HTTP Request Handler

Create `src/ServerHTTP.py`:

```python
"""HTTP server implementation for AIIA."""

import json
import base64
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from io import BytesIO

from ClientRegistry import ClientRegistry


class AIIAHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for AIIA API."""
    
    # Class variables shared across all instances
    client_registry = None
    aiia_handle = None
    options = None
    
    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        try:
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
            self.send_json_error(500, f"Internal error: {e}")
    
    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace")
        
        try:
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
            self.send_json_error(500, f"Internal error: {e}")
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        try:
            if path == "/api/files/delete":
                self.handle_files_delete(query)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            self.send_json_error(500, f"Internal error: {e}")
    
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
            
            # Validate credentials (compare with config)
            expected_user = self.options.get("SERVER_USERNAME", "admin")
            expected_pass = self.options.get("SERVER_PASSWORD", "aiia")
            
            if username == expected_user and password == expected_pass:
                return True, None, username
            
            return False, None, username
        except Exception:
            return False, None, None
    
    # === Response Helpers ===
    
    def send_json(self, status, data):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode("utf-8"))
    
    def send_json_error(self, status, message):
        """Send JSON error response."""
        self.send_json(status, {
            "success": False,
            "error": message,
            "status": status
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
        data = json.dumps(event_dict)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()
    
    # === Handler Methods ===
    
    def handle_health(self):
        """GET /health"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        response = {
            "status": "ok",
            "timestamp": self.get_timestamp(),
            "version": self.options.get("VERSION", "1.0.0"),
            "ai_model": self.options.get("AI_MODEL", "gemma4:26b"),
            "server_mode": "HTTP",
            "features": ["chat", "execute", "files", "events"],
            "connected_clients": len(self.client_registry.list_clients())
        }
        
        self.send_json(200, response)
    
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
    
    def handle_unregister(self, body):
        """POST /unregister"""
        try:
            data = json.loads(body)
            client_id = data.get("client_id")
            self.client_registry.unregister(client_id)
            self.send_json(200, {"status": "unregistered", "client_id": client_id})
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
    
    def handle_sessions(self):
        """GET /sessions"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        clients = self.client_registry.list_clients()
        self.send_json(200, {
            "clients": clients,
            "total": len(clients)
        })
    
    def handle_chat(self, body):
        """POST /chat (streaming SSE response)"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            message = data.get("message", "")
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
            
            # Call AIIA Handle.AI() and stream responses
            if self.aiia_handle:
                for token in self.aiia_handle.Stream(message, model=model):
                    self.write_sse({"type": "token", "text": token})
            
            # Send done event
            self.write_sse({"type": "done", "finish_reason": "stop"})
            
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
        except Exception as e:
            self.write_sse({"type": "error", "message": str(e)})
    
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
            import time
            while True:
                with lock:
                    while event_queue:
                        event = event_queue.pop(0)
                        self.write_sse(event)
                
                # Ping to keep connection alive
                time.sleep(30)
                try:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                except:
                    break
        finally:
            self.client_registry.unsubscribe_events(client_id, event_callback)
    
    def handle_execute(self, body):
        """POST /execute (direct tool execution)"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            tool_xml = data.get("tool", "")
            client_id = data.get("client_id")
            
            if not tool_xml:
                return self.send_json_error(400, "Missing tool")
            
            if client_id:
                self.client_registry.update_activity(client_id)
            
            # Execute via AIIA Handle.ExecuteTool()
            result = {}
            if self.aiia_handle:
                result = self.aiia_handle.ExecuteTool(tool_xml)
            
            self.send_json(200, result)
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
    
    def handle_history(self, query):
        """GET /history"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        limit = int(query.get("limit", [100])[0])
        offset = int(query.get("offset", [0])[0])
        
        # Return history from AIIA Handle
        messages = []
        if self.aiia_handle and hasattr(self.aiia_handle, "history"):
            messages = self.aiia_handle.history[offset:offset+limit]
        
        self.send_json(200, {
            "messages": messages,
            "total": len(messages) if self.aiia_handle else 0,
            "limit": limit,
            "offset": offset
        })
    
    def handle_files_list(self, query):
        """GET /api/files/list"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        path = unquote(query.get("path", ["."])[0])
        recursive = query.get("recursive", ["false"])[0].lower() == "true"
        
        # Use AIIA tool: TreeView
        if self.aiia_handle:
            result = self.aiia_handle.ExecuteTool(
                f"<TreeView><path>{path}</path></TreeView>"
            )
            self.send_json(200, result)
        else:
            self.send_json_error(501, "Not implemented")
    
    def handle_files_read(self, query):
        """GET /api/files/read"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        path = unquote(query.get("path", [""])[0])
        
        if not path:
            return self.send_json_error(400, "Missing path")
        
        # Use AIIA tool: ReadFile
        if self.aiia_handle:
            result = self.aiia_handle.ExecuteTool(
                f"<ReadFile><fileName>{path}</fileName></ReadFile>"
            )
            self.send_json(200, result)
        else:
            self.send_json_error(501, "Not implemented")
    
    def handle_files_write(self, body):
        """POST /api/files/write"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            path = data.get("path", "")
            content = data.get("content", "")
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Use AIIA tool: WriteFile
            if self.aiia_handle:
                result = self.aiia_handle.ExecuteTool(
                    f"<WriteFile><fileName>{path}</fileName><contentOfFile>{content}</contentOfFile></WriteFile>"
                )
                self.send_json(200, result)
            else:
                self.send_json_error(501, "Not implemented")
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
    
    def handle_files_append(self, body):
        """POST /api/files/append"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        try:
            data = json.loads(body)
            path = data.get("path", "")
            content = data.get("content", "")
            line = data.get("line", -1)
            
            if not path:
                return self.send_json_error(400, "Missing path")
            
            # Use AIIA tool: AppendFile
            if self.aiia_handle:
                result = self.aiia_handle.ExecuteTool(
                    f"<AppendFile><fileName>{path}</fileName><contentOfFile>{content}</contentOfFile><line>{line}</line></AppendFile>"
                )
                self.send_json(200, result)
            else:
                self.send_json_error(501, "Not implemented")
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
    
    def handle_files_delete(self, query):
        """DELETE /api/files/delete"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        path = unquote(query.get("path", [""])[0])
        
        if not path:
            return self.send_json_error(400, "Missing path")
        
        # Delete file logic
        try:
            os.remove(path)
            self.send_json(200, {
                "success": True,
                "path": path,
                "deleted": True
            })
        except FileNotFoundError:
            self.send_json_error(404, f"File not found: {path}")
        except Exception as e:
            self.send_json_error(500, f"Delete failed: {e}")
    
    def handle_history_clear(self, body):
        """POST /history/clear"""
        auth_ok, _, _ = self.check_auth()
        if not auth_ok:
            return self.send_json_error(401, "Unauthorized")
        
        if self.aiia_handle:
            self.aiia_handle.history = []
        
        self.send_json(200, {"success": True, "message": "History cleared"})
    
    # === Utilities ===
    
    @staticmethod
    def get_timestamp():
        """Get ISO 8601 timestamp."""
        import time
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
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
    
    # Create server
    server = HTTPServer((host, port), AIIAHTTPHandler)
    
    print(f"HTTP Server listening on {host}:{port}")
    print(f"API available at http://{host}:{port}/")
    print(f"Health check: curl http://{host}:{port}/health")
    
    return server
```

---

## Step 4: HTTP Server Profile

Create `server_profiles/HTTP.py`:

```python
"""HTTP server profile for AIIA."""

from http.server import HTTPServer
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server_profiles._base import _ServerBase
from src.ServerHTTP import run_http_server


class HTTP(_ServerBase):
    """HTTP + SSE server profile."""
    
    name = "HTTP"
    description = "HTTP REST API with SSE streaming"
    default_port = 9877
    
    @classmethod
    def create_server(cls, host, port, Options):
        """Create HTTP server instance."""
        # Import here to avoid circular imports
        from src.Handle import Handle
        
        # Create AIIA Handle instance
        aiia_handle = Handle(Options)
        
        # Start HTTP server
        server = run_http_server(host, port, aiia_handle, Options)
        
        return server
```

---

## Step 5: Integration with run.py

Update `run.py` to use the HTTP server profile:

```python
# In the -S/--server handling section (around line 374):

if '--server' in argv or '-S' in argv:
    opt = '--server' if '--server' in argv else '-S'
    idx = argv.index(opt)
    _spec = argv[idx + 1] if len(argv) > idx + 1 and not argv[idx + 1].startswith('-') else None
    
    from src.ServerFactory import ServerFactory
    profile_name, host, port = ServerFactory.resolve_profile_spec(_spec, Options)
    
    from src.Server import start_server
    Options['AI_LIVE'] = False
    start_server(host, port, Options, profile=profile_name)
    sys.exit(0)
```

---

## Step 6: Testing the API

### Test Health Endpoint

```bash
curl http://localhost:9877/health
```

### Test Chat (Streaming)

```bash
curl -X POST http://localhost:9877/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?", "model": "gemma4:26b"}'
```

### Test File Operations

```bash
# List files
curl "http://localhost:9877/api/files/list?path=."

# Read file
curl "http://localhost:9877/api/files/read?path=README.md"

# Write file
curl -X POST http://localhost:9877/api/files/write \
  -H "Content-Type: application/json" \
  -d '{"path": "test.txt", "content": "Hello World"}'
```

### Test Tool Execution

```bash
curl -X POST http://localhost:9877/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "<listTools/>"}'
```

---

## Step 7: Running the Server

```bash
# Start AIIA HTTP server
python run.py -S 0.0.0.0:9877

# Or with specific model
python run.py -S 0.0.0.0:9877 -m gemma4:26b -p Developer
```

---

## Error Handling

All errors return JSON with consistent format:

```json
{
  "success": false,
  "error": "Error description",
  "status": 400,
  "timestamp": "2024-01-15T10:38:00Z"
}
```

---

## Security Considerations

1. **Authentication:** Use Basic Auth for production
   ```python
   SERVER_AUTH_ENABLED = True
   SERVER_USERNAME = "admin"
   SERVER_PASSWORD = "secure_password"
   ```

2. **CORS:** Add CORS headers for cross-origin requests
   ```python
   self.send_header("Access-Control-Allow-Origin", "*")
   ```

3. **Input Validation:** Always validate path parameters to prevent directory traversal
   ```python
   if ".." in path or path.startswith("/"):
       return error  # Reject unsafe paths
   ```

4. **Rate Limiting:** Implement per-client rate limits
   ```python
   RATE_LIMITS = {
       "chat": 10,      # requests/sec
       "files": 100,    # requests/sec
       "execute": 50    # requests/sec
   }
   ```

---

## Performance Optimization

1. **Connection Pooling:** Reuse connections for persistent clients
2. **Response Caching:** Cache file listings and tool results
3. **Streaming:** Use SSE for long-running operations
4. **Threading:** Use thread pools for concurrent requests

---

## Future Enhancements

1. **WebSocket Support:** Lower-latency bi-directional communication
2. **GraphQL API:** Alternative query language for complex scenarios
3. **OpenAPI/Swagger:** Auto-generated API documentation
4. **API Versioning:** Support multiple API versions (v1, v2, etc.)
5. **Metrics & Monitoring:** Prometheus-style metrics export

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
