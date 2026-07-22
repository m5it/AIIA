Based on my work on AIIA Editor, here are the instructions for the AIIA Framework team:

---

## Instructions for AIIA Framework Development

### Priority 1: Complete HTTP Server Chat Endpoint

**File:** `server_profiles/HTTP.py`

The basic `do_POST` and `/chat` endpoint was added, but it needs the actual AI integration:

```python
def _send_sse_stream(self, message):
    """Send SSE streaming response using real AI handle."""
    self.send_response(200)
    self.send_header('Content-Type', 'text/event-stream')
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.end_headers()
    
    try:
        handle = self.ai_server.handle
        
        # TODO: Integrate with actual AIIA Handle
        # The handle should have a method to process messages and yield tokens
        # Example:
        # for token in handle.ProcessStream(message):
        #     event = {"type": "token", "text": token}
        #     self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
        #     self.wfile.flush()
        
        # For now, using mock response
        response = f"Hello! You said: '{message}'. AIIA Framework server is working!"
        for word in response.split():
            event = {"type": "token", "text": word + " "}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()
        
        # Send done event
        self.wfile.write(f"data: {json.dumps({'type': 'done'})}\n\n".encode())
        self.wfile.flush()
        
    except Exception as e:
        print(f"ERROR in SSE stream: {e}", file=sys.stderr)
        error_event = {"type": "error", "message": str(e)}
        self.wfile.write(f"data: {json.dumps(error_event)}\n\n".encode())
        self.wfile.flush()
```

**Required Integration:**
1. Connect `OurAIServer.handle` to actual AI processing
2. The Handle should yield tokens as they're generated
3. Support for different models via the Handle

---

### Priority 2: Add Missing File API Endpoints

**File:** `server_profiles/HTTP.py`

Add these endpoints to `_do_POST_impl`:

```python
def _do_POST_impl(self):
    """Handle POST requests."""
    content_len = int(self.headers.get('Content-Length', 0))
    body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
    
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        self._send_json(400, {"error": "Invalid JSON"})
        return
    
    if self.path == "/chat":
        self._handle_chat(data)
    elif self.path == "/api/files/write":
        self._handle_file_write(data)
    elif self.path == "/execute":
        self._handle_execute(data)
    else:
        self._send_json(404, {"error": "Unknown endpoint"})
```

**Implement these methods:**

```python
def _handle_file_write(self, data):
    """Write or overwrite file."""
    try:
        path = data.get("path", "")
        content = data.get("content", "")
        root_override = self.headers.get('X-Project-Path')
        
        if not path:
            self._send_json(400, {"error": "Missing path", "success": False})
            return
        
        result = self.ai_server.write_file(path, content, root=root_override)
        self._send_json(200 if result.get("success") else 500, result)
        
    except Exception as e:
        self._send_json(500, {"error": str(e), "success": False})

def _handle_execute(self, data):
    """Execute tool from XML."""
    try:
        tool_xml = data.get("tool", "")
        # TODO: Integrate with AIIA tool execution
        self._send_json(200, {
            "success": True,
            "result": "Tool execution placeholder",
            "tool": tool_xml[:100]
        })
    except Exception as e:
        self._send_json(500, {"error": str(e), "success": False})
```

---

### Priority 3: Add File Write Method to OurAIServer

**File:** `server_profiles/HTTP.py`

Add this method to the `OurAIServer` class:

```python
def write_file(self, path, content, root=None):
    """Write file content."""
    effective_root = root if root else self.project_root
    
    safe_path = self._get_safe_path(path, root=root)
    if safe_path is None:
        return {"error": "Access denied", "success": False}
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "path": path,
            "size": len(content)
        }
    except Exception as e:
        return {"error": str(e), "success": False}
```

---

### Priority 4: Server Configuration Enhancement

**File:** `config.py` or create `server_config.py`

Add server-specific configuration:

```python
SERVER_CONFIG = {
    "port": 9877,
    "host": "127.0.0.1",
    "cors_enabled": True,
    "auth_enabled": False,
    "max_connections": 10,
    "request_timeout": 120,
    "sse_keepalive": 30,  # Seconds between keepalive messages
}
```

---

### Priority 5: Authentication for Chat Endpoint

**File:** `server_profiles/HTTP.py`

Add authentication check to `_handle_chat`:

```python
def _handle_chat(self, data):
    """Handle chat requests with optional auth."""
    # Check auth if enabled
    if self.ai_server.global_auth_enabled:
        auth_header = self.headers.get('Authorization', '')
        if not self._check_auth(auth_header):
            self._send_json(401, {"error": "Unauthorized"})
            return
    
    # Continue with chat handling...
```

---

### Priority 6: Error Handling & Logging

Add better error logging for all endpoints:

```python
def log_message(self, format, *args):
    """Log requests with timestamps."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {format % args}", file=sys.stderr)
```

---

### Priority 7: Test the Server

Create a test script:

```python
#!/usr/bin/env python3
"""Test AIIA Framework HTTP server."""

import json
import urllib.request

def test_server():
    base_url = "http://127.0.0.1:9877"
    
    # Test health
    resp = urllib.request.urlopen(f"{base_url}/health")
    print("Health:", json.loads(resp.read()))
    
    # Test chat
    req = urllib.request.Request(
        f"{base_url}/chat",
        data=json.dumps({"message": "Hello"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    print("Chat response (first line):", resp.readline().decode().strip())
    
    # Test file list
    resp = urllib.request.urlopen(f"{base_url}/api/files/list")
    print("Files:", json.loads(resp.read())["files"][:3], "...")

if __name__ == "__main__":
    test_server()
```

---

### Connection with AIIA Editor

The AIIA Editor expects these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check server status |
| `/chat` | POST | Send message, receive SSE stream |
| `/api/files/list` | GET | List project files |
| `/api/files/read` | GET | Read file content |
| `/api/files/write` | POST | Write file content |
| `/execute` | POST | Execute tool |

All endpoints should:
- Support `X-Project-Path` header for project root
- Return JSON with `{"success": true/false, ...}`
- Support CORS for browser-based editors
- Stream SSE for `/chat` endpoint

---

### Testing Integration

1. Start AIIA Framework server:
   ```bash
   cd /path/to/AIIA
   python3 run.py --server 127.0.0.1:9877
   ```

2. Test with AIIA Editor:
   - Set connection to `127.0.0.1:9877`
   - Send chat message
   - Should see streaming response

---

### Key Integration Points

- The Handle must yield tokens for SSE streaming
- File operations must respect `X-Project-Path` header
- All JSON responses must include `success` field
- CORS headers must be present for browser compatibility

---

## Notes from AIIA Editor Development

The AIIA Editor was updated to:

1. Detect limited servers (servers that respond to `/health` but not `/chat`)
2. Show helpful warnings when chat is unavailable
3. Provide a built-in mock server for testing
4. Support resizable panels with sash positions saved to config
5. Save all settings to `~/.config/AIIAEditor/config.json`

Once the AIIA Framework server fully implements the endpoints above, the editor will connect seamlessly without showing the HTTP 501 warning.

---

**Next Steps for Framework Team:**

1. Implement real AI token streaming in `_send_sse_stream`
2. Add `/api/files/write` and `/execute` endpoints
3. Add `write_file` method to `OurAIServer`
4. Test with the provided test script
5. Coordinate with AIIA Editor team for integration testing
