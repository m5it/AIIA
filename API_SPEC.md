# AIIA HTTP API Specification

## Overview

The AIIA HTTP server provides a comprehensive REST + SSE API for editor integration, multi-client support, and tool execution. The API uses JSON for all request/response payloads except streaming responses.

---

## Core Endpoints

### 1. Health & Server Info

#### GET /health
Health check endpoint for basic connectivity and server status.

**Request:**
```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:45Z",
  "version": "1.0.0",
  "ai_model": "gemma4:26b",
  "server_mode": "HTTP",
  "features": ["chat", "execute", "files", "events"],
  "connected_clients": 2
}
```

**Error (503 Service Unavailable):**
```json
{
  "status": "error",
  "message": "Ollama server unreachable",
  "timestamp": "2024-01-15T10:30:45Z"
}
```

---

### 2. Client Registration & Management

#### POST /register
Register a new client and get a unique `client_id` for event streaming.

**Request:**
```json
{
  "name": "AIIAEditor-instance-1",
  "type": "editor",
  "project_path": "/home/user/myproject"
}
```

**Response (200 OK):**
```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "AIIAEditor-instance-1",
  "timestamp": "2024-01-15T10:30:45Z",
  "server_time": 1705316445,
  "session_id": "sess_abc123"
}
```

---

#### POST /unregister
Disconnect and clean up client resources.

**Request:**
```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "status": "unregistered",
  "client_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### GET /sessions
List all connected clients/sessions.

**Request:**
```http
GET /sessions
```

**Response (200 OK):**
```json
{
  "clients": [
    {
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "AIIAEditor-instance-1",
      "type": "editor",
      "connected_at": "2024-01-15T10:30:45Z",
      "last_activity": "2024-01-15T10:35:12Z"
    },
    {
      "client_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "terminal-client",
      "type": "terminal",
      "connected_at": "2024-01-15T10:32:10Z",
      "last_activity": "2024-01-15T10:34:50Z"
    }
  ],
  "total": 2
}
```

---

### 3. Chat & Streaming

#### POST /chat
Start a chat session with SSE streaming response.

**Request:**
```json
{
  "message": "What files are in the project?",
  "model": "gemma4:26b",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_path": "/home/user/myproject",
  "temperature": 0.7,
  "context_limit": 8000
}
```

**Response: Server-Sent Events (200 OK)**

Headers:
```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

Events:
```
data: {"type": "thinking", "text": "Let me analyze the project structure..."}
data: {"type": "token", "text": "The project contains"}
data: {"type": "token", "text": " several Python"}
data: {"type": "token", "text": " modules..."}
data: {"type": "tool_start", "tool": "TreeView", "params": {"path": ".", "max_depth": 2}}
data: {"type": "tool_result", "tool": "TreeView", "success": true, "result": "├── src/\n│   ├── main.py\n│   └── utils.py\n└── README.md"}
data: {"type": "done", "finish_reason": "stop", "token_count": {"prompt": 150, "completion": 85}}
```

**Event Types:**
- `thinking`: Model's reasoning (internal)
- `token`: Streamed text token
- `tool_start`: Tool invocation started
- `tool_result`: Tool execution result
- `done`: Chat complete
- `error`: Error occurred

---

#### GET /events?client_id=<id>
Persistent SSE stream for receiving server events (client activity, tool calls from other clients, etc.).

**Request:**
```http
GET /events?client_id=550e8400-e29b-41d4-a716-446655440000
```

**Response: Server-Sent Events (200 OK)**

```
data: {"type": "client_joined", "client_id": "660e8400-e29b-41d4-a716-446655440001", "client_name": "terminal-client", "timestamp": "2024-01-15T10:32:10Z"}
data: {"type": "tool_started", "client_id": "660e8400-e29b-41d4-a716-446655440001", "tool": "WriteFile", "path": "src/new_feature.py"}
data: {"type": "tool_completed", "client_id": "660e8400-e29b-41d4-a716-446655440001", "tool": "WriteFile", "success": true}
```

**Timeout:** Streams until client disconnects (keep-alive: 30s ping)

---

### 4. Tool Execution

#### POST /execute
Execute an XML tool directly without chat interaction.

**Request:**
```json
{
  "tool": "<TreeView><path>.</path><max_depth>2</max_depth></TreeView>",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_path": "/home/user/myproject"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "tool": "TreeView",
  "result": "├── src/\n│   ├── main.py\n│   └── utils.py\n└── README.md",
  "duration_ms": 42,
  "timestamp": "2024-01-15T10:35:12Z"
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "tool": "TreeView",
  "error": "Invalid path: /nonexistent",
  "timestamp": "2024-01-15T10:35:12Z"
}
```

---

### 5. File Operations

#### GET /api/files/list
List files in project directory (tree view).

**Request:**
```http
GET /api/files/list?path=src&recursive=false
```

**Query Parameters:**
- `path`: Relative path in project (default: `.`)
- `recursive`: Include subdirectories (default: `false`)

**Response (200 OK):**
```json
{
  "path": "src",
  "items": [
    {
      "name": "main.py",
      "type": "file",
      "size": 2048,
      "modified": "2024-01-15T09:20:00Z",
      "permissions": "rw-r--r--"
    },
    {
      "name": "utils.py",
      "type": "file",
      "size": 1024,
      "modified": "2024-01-15T08:45:00Z",
      "permissions": "rw-r--r--"
    },
    {
      "name": "__pycache__",
      "type": "directory",
      "size": 4096,
      "modified": "2024-01-15T09:15:00Z",
      "permissions": "rwxr-xr-x"
    }
  ],
  "total": 3,
  "project_root": "/home/user/myproject"
}
```

---

#### GET /api/files/read
Read file content with syntax highlighting metadata.

**Request:**
```http
GET /api/files/read?path=src/main.py
```

**Query Parameters:**
- `path`: Relative path to file (required)
- `encoding`: Text encoding (default: `utf-8`)

**Response (200 OK):**
```json
{
  "path": "src/main.py",
  "content": "#!/usr/bin/env python3\n...",
  "size": 2048,
  "modified": "2024-01-15T09:20:00Z",
  "encoding": "utf-8",
  "language": "python",
  "line_count": 45,
  "absolute_path": "/home/user/myproject/src/main.py"
}
```

**Response (404 Not Found):**
```json
{
  "success": false,
  "error": "File not found",
  "path": "src/missing.py"
}
```

---

#### POST /api/files/write
Write or overwrite file content.

**Request:**
```json
{
  "path": "src/new_file.py",
  "content": "#!/usr/bin/env python3\nprint('Hello')\n",
  "encoding": "utf-8",
  "create_dirs": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "path": "src/new_file.py",
  "size": 42,
  "created": false,
  "modified": "2024-01-15T10:35:12Z",
  "absolute_path": "/home/user/myproject/src/new_file.py",
  "message": "File written successfully"
}
```

---

#### POST /api/files/append
Append or insert content at specific line.

**Request:**
```json
{
  "path": "src/main.py",
  "content": "\n# New comment\n",
  "line": 10
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "path": "src/main.py",
  "operation": "inserted",
  "line": 10,
  "size": 2090,
  "modified": "2024-01-15T10:36:00Z"
}
```

---

#### POST /api/files/replace
Replace specific line(s) in a file.

**Request:**
```json
{
  "path": "src/main.py",
  "lines": [10, 15],
  "content": "# Updated code block\nprint('new version')\n"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "path": "src/main.py",
  "operation": "replaced",
  "lines_affected": 6,
  "size": 2045,
  "modified": "2024-01-15T10:36:15Z"
}
```

---

#### DELETE /api/files/delete
Delete a file or directory.

**Request:**
```http
DELETE /api/files/delete?path=src/old_file.py&recursive=false
```

**Query Parameters:**
- `path`: File/directory path
- `recursive`: Delete directory and contents (default: `false`)

**Response (200 OK):**
```json
{
  "success": true,
  "path": "src/old_file.py",
  "deleted": true,
  "timestamp": "2024-01-15T10:37:00Z"
}
```

---

### 6. History & Context

#### GET /history
Retrieve conversation history for a session.

**Request:**
```http
GET /history?limit=100&offset=0
```

**Query Parameters:**
- `limit`: Max items (default: 100, max: 1000)
- `offset`: Skip N items (default: 0)

**Response (200 OK):**
```json
{
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "What files are in the project?",
      "timestamp": "2024-01-15T10:30:00Z",
      "model": "gemma4:26b"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "The project contains...",
      "timestamp": "2024-01-15T10:30:05Z",
      "tokens": {"prompt": 150, "completion": 85}
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

---

#### POST /history/clear
Clear conversation history.

**Request:**
```json
{
  "confirmed": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "History cleared",
  "timestamp": "2024-01-15T10:37:30Z"
}
```

---

## Authentication

### Basic Auth (Optional)

When `SERVER_AUTH_ENABLED = true` in config:

```http
Authorization: Basic base64(username:password)
X-Project-Path: /path/to/project
```

Example:
```python
import base64
credentials = base64.b64encode(b"admin:password").decode('utf-8')
headers = {"Authorization": f"Basic {credentials}"}
```

### Per-Project Auth

If `.aiia/auth.json` exists in project:
```json
{
  "enabled": true,
  "username": "project_user",
  "password": "project_password"
}
```

Headers required:
```http
Authorization: Basic base64(project_user:project_password)
X-Project-Path: /home/user/myproject
```

---

## Error Handling

### Standard Error Response

```json
{
  "success": false,
  "error": "Tool not found",
  "error_code": "TOOL_NOT_FOUND",
  "status": 404,
  "timestamp": "2024-01-15T10:38:00Z",
  "request_id": "req_xyz789"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid params) |
| 401 | Unauthorized (auth failed) |
| 403 | Forbidden (no permission) |
| 404 | Not Found |
| 409 | Conflict (file exists, etc.) |
| 500 | Server Error |
| 501 | Not Implemented |
| 503 | Service Unavailable (Ollama down) |

---

## Client Implementation Example

### Python Client (aiia_client.py)

```python
from aiia_client import AIIAClient

# Connect
client = AIIAClient(host="127.0.0.1", port=9877, 
                    username="admin", password="secret")

# Health check
health = client.health()

# Register
reg = client.register(name="MyEditor", client_type="editor")
client_id = reg["client_id"]

# Chat with streaming
for event in client.chat("List all Python files"):
    if event["type"] == "token":
        print(event["text"], end="", flush=True)
    elif event["type"] == "tool_result":
        print(f"\n[Tool: {event['tool']}] {event['result']}\n")

# File operations
files = client.list_files(path="src")
content = client.read_file(path="src/main.py")
client.write_file(path="src/new.py", content="# new file\n")

# Events stream (background)
client.events_connect(callback=lambda e: print(f"Event: {e['type']}"))

# Cleanup
client.events_disconnect()
client.unregister()
```

---

## Rate Limiting & Quotas

- **Chat:** 10 requests/sec per client
- **File ops:** 100 requests/sec per client
- **Tool execute:** 50 requests/sec per client
- **Events stream:** 1 per client (concurrent)

Rate limit headers:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1705316505
```

---

## WebSocket Support (Future)

Alternative to SSE for lower-latency bi-directional communication. Endpoints will be available at:
- `ws://host:port/ws/chat`
- `ws://host:port/ws/events`

---

## Version & Compatibility

- **API Version:** 1.0.0
- **Server:** AIIA 1.0.0+
- **Client:** AIIAEditor 1.0.0+

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
