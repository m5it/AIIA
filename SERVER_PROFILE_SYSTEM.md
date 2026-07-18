# Server Profile System

## Overview

The server profile system allows AIIA to run different types of servers
from a single entry point (`-S` flag). Each profile is a Python class in
`server_profiles/` that defines how the server starts, which protocols it
speaks, and what endpoints it exposes.

The system mirrors the persona system (`instruct/` classes): profiles are
auto-discovered, loaded dynamically, and selected via CLI or config.

---

## Architecture

```
run.py -S [profile]:host:port
  │
  ├── ServerFactory.resolve_profile_spec()
  │     Parses "http:0.0.0.0:9877" → ("HTTP", "0.0.0.0", 9877)
  │     Falls back to: profile from config, host 127.0.0.1, port 9877
  │
  ├── ServerFactory.create_server("HTTP", "0.0.0.0", 9877)
  │     Loads server_profiles/HTTP.py
  │     Calls HTTP.create_server(host, port, Options)
  │
  └── HTTP.create_server()
        Instantiates OurAIServer
        Initializes Handle (AI engine)
        Starts ThreadedHTTPServer → serve_forever()
```

### File Layout

```
server_profiles/
├── __init__.py          # package marker
├── _ServerBase.py       # abstract base class (ServerProfile)
└── HTTP.py              # HTTP SSE server profile (default)

src/
├── ServerFactory.py     # profile discovery, resolution, creation
└── Server.py            # thin delegator → ServerFactory (backward compat)

config.py                # SERVER_PROFILE, SERVER_HOST, SERVER_PORT, ...
```

---

## Creating a New Profile

### 1. Create the file

```
server_profiles/WS.py
```

### 2. Extend `ServerProfile`

```python
from server_profiles._ServerBase import ServerProfile


class WS(ServerProfile):
	"""WebSocket server — bidirectional streaming chat."""
	
	name = "WS"
	description = "WebSocket server with bidirectional chat streaming"
	default_port = 9878
	
	@classmethod
	def create_server(cls, host, port, Options):
		"""Create and start the server. Must block (serve_forever)."""
		# Initialize your server here
		# Options dict has all config keys (AI_MODEL, INSTRUCT_CLASS, etc.)
		server = MyWebSocketServer(host, port, Options)
		server.start()
		return server
	
	@classmethod
	def get_endpoints(cls):
		"""Return list of endpoint descriptions."""
		return [
			{'method': 'WS',  'path': '/',        'description': 'WebSocket chat endpoint'},
			{'method': 'GET', 'path': '/health',  'description': 'Health check'},
		]
```

The profile class must:
- Extend `ServerProfile`
- Have `name`, `description`, `default_port` class attributes
- Implement `create_server(cls, host, port, Options)` → returns server object with `serve_forever()` and `shutdown()`
- Optionally implement `get_endpoints(cls)` → returns list of `{method, path, description}` dicts

### 3. Use it

```bash
python run.py -S ws:0.0.0.0:9878 -p Developer
```

---

## Profile Resolution Rules

When `-S` is given, `ServerFactory.resolve_profile_spec()` parses the argument:

| Input | Profile | Host | Port |
|-------|---------|------|------|
| (none) | `HTTP` | `127.0.0.1` | `9877` |
| `http` | `HTTP` | `127.0.0.1` | `9877` |
| `0.0.0.0:9877` | `HTTP` | `0.0.0.0` | `9877` |
| `localhost` | `HTTP` | `localhost` | `9877` |
| `http:0.0.0.0:9877` | `HTTP` | `0.0.0.0` | `9877` |
| `ws` | `WS` | `127.0.0.1` | `9878` |
| `v2:0.0.0.0:9000` | `V2` | `0.0.0.0` | `9000` |

**Rule:** If the first colon-separated segment looks like a host (IP, `localhost`, numeric), it's treated as bare `host:port` → default HTTP profile. Otherwise it's a profile name.

---

## Default Server Profile: HTTP

### How to start

```bash
python run.py -S                           # 127.0.0.1:9877, HTTP profile
python run.py -S 0.0.0.0:9877              # same, all interfaces
python run.py -S http:0.0.0.0:9877         # explicit profile name
python run.py -S -p Developer -m gemma3:12b # with persona & model
python run.py -S -Q -p Developer            # quick mode, no prompts
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API index with version, profile info, and endpoint listing |
| `GET` | `/health` | Health check — returns `{"status":"ok"}` |
| `POST` | `/chat` | Send message, receive SSE stream of AI tokens |
| `POST` | `/execute` | Direct tool execution (no AI), accepts XML tool calls |

### API Details

**GET /health**

Response:
```json
{"status": "ok"}
```

**GET /** — API Index

Response:
```json
{
  "service": "AIIA Agentic AI",
  "version": "1.0.0",
  "profile": "HTTP",
  "endpoints": [
    {"method": "GET",  "path": "/",         "description": "This index"},
    {"method": "GET",  "path": "/health",   "description": "Health check"},
    {"method": "POST", "path": "/chat",     "description": "Send message, receive SSE stream of AI tokens"},
    {"method": "POST", "path": "/execute",  "description": "Direct tool execution (no AI)"}
  ],
  "links": {
    "chat":    "POST /chat    {\"message\":\"your text\"}",
    "execute": "POST /execute {\"tool\":\"<ToolName>...</ToolName>\"}"
  }
}
```

**POST /chat** — SSE Streaming

Request:
```bash
curl -N -X POST http://localhost:9877/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a hello world script"}'
```

Response (SSE stream):
```
data: {"type":"token","text":"I'll"}
data: {"type":"token","text":" create"}
data: {"type":"token","text":" a"}
data: {"type":"token","text":" Python"}
data: {"type":"token","text":" script"}
data: {"type":"tool","tool":"WriteFile","params":{"result":"Created hello.py"}}
data: {"type":"done"}
```

Event types:
- `token` — streaming text tokens
- `tool` — tool invocation results
- `error` — error messages
- `done` — end of stream
- `interrupt` — AI loop interrupted (Ctrl+D)
- `abort` — stream aborted (plan mode blocked tool)

**POST /execute** — Direct Tool Execution

Request:
```bash
curl -X POST http://localhost:9877/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "<ReadFile><fileName>workin/config.json</fileName></ReadFile>"}'
```

Response:
```json
{
  "success": true,
  "tool": "ReadFile",
  "result": "file contents..."
}
```

### Client Usage

```bash
# Terminal client
python run.py --connect localhost:9877
# or
python run.py -C localhost:9877
```

Any HTTP client (curl, Python requests, Android app, tkinter editor) can
connect to the server for AI-powered features.

---

## Config Options

Added to `config.py`:

| Key | Default | Description |
|-----|---------|-------------|
| `SERVER_PROFILE` | `"HTTP"` | Default profile name |
| `SERVER_HOST` | `"127.0.0.1"` | Default bind address |
| `SERVER_PORT` | `9877` | Default port |
| `SERVER_PROFILES_PATH` | `"server_profiles"` | Path to profile modules |
| `SERVER_TLS_CERT` | `None` | Path to TLS cert (for HTTPS profile) |
| `SERVER_TLS_KEY` | `None` | Path to TLS key (for HTTPS profile) |

Override in `aiia.json`:
```json
{
  "SERVER_PROFILE": "HTTP",
  "SERVER_HOST": "0.0.0.0",
  "SERVER_PORT": 9877
}
```

---

## Profile Factory API

### `ServerFactory(Options)`

```python
from src.ServerFactory import ServerFactory

factory = ServerFactory(Options)

# List available profiles
profiles = factory.list_profiles()
# [{'name': 'HTTP', 'description': '...', 'default_port': 9877, 'endpoints': [...]}]

# Get a profile by name
http_cls = factory.get_profile('HTTP')

# Create and start a server
server = factory.create_server('HTTP', '127.0.0.1', 9877)
```

### `ServerFactory.resolve_profile_spec(spec, Options)`

```python
from src.ServerFactory import ServerFactory

profile, host, port = ServerFactory.resolve_profile_spec('ws', Options)
# → ('WS', '127.0.0.1', 9878)

profile, host, port = ServerFactory.resolve_profile_spec('0.0.0.0:9877', Options)
# → ('HTTP', '0.0.0.0', 9877)
```

---

## Planned Profiles

| Profile | Protocol | Port | Status |
|---------|----------|------|--------|
| `HTTP` | HTTP SSE | 9877 | ✅ Implemented |
| `HTTPS` | HTTP + TLS | 9877 | 🔲 Planned |
| `WS` | WebSocket | 9878 | 🔲 Planned |
| `V1` | API v1 | 9877 | 🔲 Planned (alias for HTTP with explicit versioning) |
| `V2` | OpenAI-compatible API | 9877 | 🔲 Planned (`/v1/chat/completions`) |

---

---

## Client Request/Response Flow

### The Wire Protocol (HTTP SSE)

A client sends a simple JSON POST and receives a stream of newline-delimited
SSE events. Here's the exact flow:

**1. Client sends a question**

```
POST /chat HTTP/1.1
Host: localhost:9877
Content-Type: application/json

{"message": "what is 2+2?"}
```

**2. Server streams back events**

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
Access-Control-Allow-Origin: *
X-Accel-Buffering: no

data: {"type":"token","text":"2"}
data: {"type":"token","text":" + "}
data: {"type":"token","text":"2"}
data: {"type":"token","text":" = "}
data: {"type":"token","text":"4"}
data: {"type":"done"}
```

**3. Client reads line by line**, parsing each `data: ` line as JSON.

---

### Client Implementation Examples

#### Python (minimal, stdlib only)

```python
import json, http.client

def ask_server(host, port, message):
	conn = http.client.HTTPConnection(host, port, timeout=120)
	body = json.dumps({'message': message})
	conn.request('POST', '/chat', body, {'Content-Type': 'application/json'})
	resp = conn.getresponse()
	
	result = ""
	for line in resp:
		line = line.decode('utf-8').strip()
		if not line.startswith('data: '):
			continue
		event = json.loads(line[6:])
		t = event.get('type')
		if t == 'token':
			result += event['text']
		elif t == 'tool':
			print("\n[Tool: {}]".format(event['tool']))
		elif t == 'error':
			print("\n[Error: {}]".format(event['message']))
		elif t == 'done':
			break
	conn.close()
	return result

answer = ask_server('localhost', 9877, 'what is 2+2?')
print(answer)
```

#### curl (command line)

```bash
curl -N -X POST http://localhost:9877/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "write a python script"}'
```

Add `-s` to suppress progress and `2>/dev/null` to hide stderr.

#### tkinter (threaded SSE reader)

```python
import json, threading, http.client
from queue import Queue

class AIIAClient:
	def __init__(self, host='localhost', port=9877):
		self.host = host
		self.port = port
		self.queue = Queue()
	
	def ask(self, message, on_token=None, on_done=None):
		"""Non-blocking: spawns a thread, returns immediately."""
		t = threading.Thread(
			target=self._stream,
			args=(message, on_token, on_done),
			daemon=True
		)
		t.start()
	
	def _stream(self, message, on_token, on_done):
		conn = http.client.HTTPConnection(self.host, self.port, timeout=120)
		conn.request('POST', '/chat',
			json.dumps({'message': message}),
			{'Content-Type': 'application/json'})
		resp = conn.getresponse()
		for line in resp:
			text = line.decode('utf-8').strip()
			if not text.startswith('data: '):
				continue
			event = json.loads(text[6:])
			t = event.get('type')
			if t == 'token' and on_token:
				on_token(event['text'])
			elif t == 'done':
				if on_done:
					on_done()
				break
		conn.close()
```

Usage in tkinter:
```python
def update_text(token):
	text_widget.insert('end', token)
	text_widget.see('end')

def on_complete():
	text_widget.insert('end', '\n[DONE]\n')

client = AIIAClient('localhost', 9877)
client.ask("explain recursion", on_token=update_text, on_done=on_complete)
```

#### Android (Java)

```java
// Using OkHttp for SSE streaming
OkHttpClient client = new OkHttpClient.Builder()
    .readTimeout(120, TimeUnit.SECONDS)
    .build();

String json = new JSONObject().put("message", "hello").toString();
Request request = new Request.Builder()
    .url("http://10.0.2.2:9877/chat")
    .post(RequestBody.create(MediaType.parse("application/json"), json))
    .build();

try (Response response = client.newCall(request).execute()) {
    BufferedReader reader = new BufferedReader(
        new InputStreamReader(response.body().byteStream()));
    String line;
    while ((line = reader.readLine()) != null) {
        if (line.startsWith("data: ")) {
            JSONObject event = new JSONObject(line.substring(6));
            String type = event.getString("type");
            if ("token".equals(type)) {
                // append event.getString("text") to UI
            } else if ("done".equals(type)) {
                break;
            }
        }
    }
}
```

---

### SSE Event Types (complete reference)

| Type | Fields | When |
|------|--------|------|
| `token` | `text` (string) | Streaming AI text output |
| `tool` | `tool` (name), `params` (object) | Tool was invoked by AI |
| `error` | `message` (string) | Error occurred |
| `done` | *(none)* | Stream complete |
| `interrupt` | `reason` (string) | AI loop interrupted (Ctrl+D) |
| `abort` | `reason` (string) | Stream aborted (plan mode blocked tool) |

### Special Client Messages

The client can send these `!commands` as the message:

| Message | Effect |
|---------|--------|
| `"!MODE plan"` | Switch to plan mode |
| `"!MODE build"` | Switch to build mode |
| `"!NEW SESSION"` | Reset session (re-initializes Handle) |
| `"!HELP"` | Returns list of commands |
| `"!STATS"` | Token usage stats |
| `"!MODEL llama3:70b"` | Switch model mid-session |
| `any other text"` | Sent to AI as a normal prompt |

### Direct Tool Execution (no AI)

Clients can also call tools directly without involving the AI:

```
POST /execute HTTP/1.1
Content-Type: application/json

{"tool": "<ReadFile><fileName>workin/config.json</fileName></ReadFile>"}
```

Response:
```json
{"success": true, "tool": "ReadFile", "result": "file contents..."}
```

This is useful for editor clients that need to read/write files, search
code, or run shell commands without waiting for the AI to respond.

---

## Backward Compatibility

The original `src/Server.py` still exists and works. It's been refactored to
delegate to `ServerFactory`:

```python
from src.Server import start_server
start_server('127.0.0.1', 9877, Options)
# Equivalent to:
# ServerFactory(Options).create_server('HTTP', '127.0.0.1', 9877)
```

Existing code using `from src.Server import start_server` or
`from src.Server import OurAIServer` will need to update to the new structure.
`start_server()` still works as before. Direct `OurAIServer` import is
deprecated — use `ServerFactory` or profile classes directly.

The old `-S host:port` format (without profile) continues to work via
auto-detection: bare host:port strings are resolved as HTTP profile.
