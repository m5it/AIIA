# Connection.java JSON Protocol Rewrite Plan

## Problem
`Connection.java:93` sends `message=<xml>` with `Content-Type: text/xml`.
Server expects `{"message":"<xml>"}` JSON.
Editor health check hits `GET /chat`, server has `GET /health`.
SSE parsing doesn't detect `{"type":"done"}`.

## Changes

### 1. Connection.java
- Health check: `GET /chat` → `GET /health`
- POST body: form-encoded → `{"message":"<xml>"}` JSON with Gson
- Content-Type: `text/xml` → `application/json`
- SSE parsing: parse JSON events, dispatch by `type` field
- `{"type":"done"}` detection: break read loop
- Add `sendText()` method for plain chat messages

### 2. MainController.java
- `processServerMessage`: rewrite to handle JSON event types (token/tool/error/done)
- `onFileSelected`: `<path>` → `<fileName>`
- `handleSave`: `<path>+<content>` → `<fileName>+<contentOfFile>`
- Default URL: `http://localhost:8080` → `http://localhost:9877`

### 3. No changes needed
- LogController.java (already supports "tool" type)
- EditorController.java
- FileTreeController.java

## Implementation Order
1. Connection.java — core protocol
2. MainController.java — event handling + param names
3. Maven compile + test

## Test
```bash
# Terminal 1: start server
cd /home/t3ch/adata2/OurAI/OurAI && python run.py -S -p 9877

# Terminal 2: start editor
cd /home/t3ch/adata2/OurAI/OurAIEditor && mvn compile javafx:run
```

## Verification
- Connection indicator turns green
- File tree click → ReadFile reaches server, tokens display in log
- Edit + Save → WriteFile with correct param names
- Disconnect → clean shutdown
