# Threading & Queue Support Notes

## Current State: 100% Sequential

All tool execution is strictly sequential. The critical choke point is:

- **`src/ToolParser.py:453`** — `for inv in tool_invocations:` loop processes tools one at a time
- **`src/Handle.py:1484-1486`** — `client.chat(**chat_params)` blocks the entire AI loop for 2-60s per iteration while Ollama generates

Every tool result is immediately appended to history (`ToolParser.py:561-566`) before the next tool starts. No parallelism exists.

### Only existing queue:
- `OrchestraDirector.msg_queue` (`queue.Queue`) in `OrchestraDirector.py:13` — collects TCP messages from remote worker threads

### Only existing threads:
| Thread | Location | Purpose |
|--------|----------|---------|
| Koslenium daemon | `Handle.py:121` | Background browser server for WWW/WWWExec |
| Server HTTP threads | `Server.py:9` | ThreadingMixIn for SSE HTTP server (serialized by lock at `Server.py:42`) |
| Worker handler threads | `OrchestraDirector.py:49-101` | One thread per connected remote worker |

## Key Choke Points

| Phase | Time | File:Line | Problem |
|-------|------|-----------|---------|
| Ollama API call | 2-60s | `Handle.py:1484-1486` | Blocks entire loop, streaming makes async complex |
| Sequential tool loop | 0.01-300s per tool × N | `ToolParser.py:453` | Even independent tools run one-by-one |
| Heavy tools | 1-300s each | Various | WWW (300s), GenerateImage (120s+), Terminal/ExecuteScript (30s each) |
| Context summarization | 2-10s | `Handle.py:1153-1160` | Blocking Ollama call, runs before model calls |

## Heavy Tools (good threading candidates)

| Tool | Typical latency | File |
|------|----------------|------|
| WWW | 1-300s | `tools/tool_WWW.py` |
| WWWExec | 1-300s | `tools/tool_WWWExec.py` |
| ExecuteScript | 0.1-30s | `tools/tool_ExecuteScript.py` |
| Terminal | 0.1-30s | `tools/tool_Terminal.py` |
| GenerateImage | 5-120+ s | `tools/tool_GenerateImage.py` |
| ReadImage | 0.1-5s | `tools/tool_ReadImage.py` |
| ImageTransform | 0.1-3s | `tools/tool_ImageTransform.py` |
| Grep | 0.1-10s | `tools/tool_Grep.py` |
| Diff | 0.1-5s | `tools/tool_Diff.py` |
| Sed | 0.1-5s | `tools/tool_Sed.py` |
| Find | 0.1-5s | `tools/tool_Find.py` |

## Light Tools (threading less critical)

ReadFile, WriteFile, AppendFile, CreateFile, ReplaceLine, List, TreeView, Head, Tail, Sort, listTools, CurrentTime, SaveTip, GetTip, ListTips, DeleteTip, ReinsertTip — all < 0.1s each.

## Queue/Thread Architecture Options

### Option A: ThreadPoolExecutor for tools
- **Effort:** ~2hr
- **Impact:** Medium
- **Change:** Replace `ToolParser.py:453` sequential loop with `ThreadPoolExecutor(max_workers=4)`
- **Classification:** Tools marked as "independent" (read-only, or writes to different files) run in parallel; dependent tools (`createTask` → `nextTask`) serialized
- **Thread safety:** `_current_handle` (class-level var at `ToolParser.py:14`) must be made thread-local or passed per-tool
- **Result order:** Must collect and append to history in original invocation order

### Option B: Tool result queue
- **Effort:** ~1hr
- **Impact:** Low-Medium
- **Change:** Results go into `queue.Queue` instead of directly to `self.handle.Response()`. Collector thread drains queue and appends to `hHM.msgs` in order.
- **Benefit:** Decouples tool execution from history writing. Foundation for future parallelism.

### Option C: Background worker queue
- **Effort:** ~4hr
- **Impact:** High for slow tools
- **Change:** Expand Orchestra socket protocol. Heavy tools dispatched to remote workers for parallel execution.
- **Existing infra:** `OrchestraDirector.dispatch_task()` (line 215), workers run `Handle.AI()` locally

### Option D: Priority dispatch queue
- **Effort:** ~3hr
- **Impact:** Medium
- **Change:** Parse all tools in response → build dependency DAG → schedule optimally using queue
- **Benefit:** Correct ordering + maximal parallelism

### Option E: Async pipeline (asyncio)
- **Effort:** ~8hr
- **Impact:** High
- **Change:** Full async rewrite of tool dispatch + streaming. `Handle.AI()` loop from while-iteration → async event-driven.
- **Note:** Largest refactor. Would need to change everything from Ollama client calls through tool dispatch.

## Thread Safety Concerns

If implementing parallel tool execution:

1. **`ToolParser._current_handle`** (line 14, also set at line 384) — class-level variable set before `h.run()`. Must become `threading.local()` or passed as parameter.
2. **`self.handle.Response()`** — appends to `hHM.msgs` (list) and writes to disk. Must be protected with lock for parallel execution.
3. **`self.handle.Options`** — dict reads/writes from multiple threads. Needs care.
4. **`h.run(**params)`** — most tools are stateless (no shared state), but some use module-level caches (e.g., `GenerateImage` caches pipeline at module level). Thread safety varies per tool.

## Orchestra Queue Architecture (Existing)

```
Director                                    Worker(s)
  |                                           |
  |-- TCP connect + register(name,model) ---->|
  |<-- ready ---------------------------------|
  |                                           |
  |-- assign(taskId, instruction) ----------->|-- Response('user', instruction)
  |                                           |-- AI() [full model+tool loop]
  |<-- progress(taskId, log) -----------------|
  |<-- complete(taskId, result) --------------|
  |<-- ready ---------------------------------|
```

- Protocol: Newline-delimited JSON over TCP
- Director `msg_queue` (`queue.Queue`): collects messages from worker handler threads
- `dispatch_task()` (line 215): finds first idle worker, sends `assign`
- `route_to_plan_worker()` (line 115): blocking poll up to 300s for plan result
- `enter_dispatch_mode()` (line 237): iterates plan tasks, dispatches to workers, spins until all done

## Tool Class Interface

```python
class ToolName():
    def __init__(self):
        self.info = { "name": "...", "description": "...", "parameters": {...} }
    def run(self, param1, param2=default) -> str:
        # Do work, return result string or "Error: ..."
```

Optional: `cache_ttl = N` (seconds). No required base class. No timeout mechanism at framework level.

## Tool Result → History Flow

```
Model output → Parse() → FireToolInvocation()
                            ↓
              for each tool invocation:
                ExecuteTextTool(name, params)
                → h.run(**params)           [BLOCKING, synchronous]
                → Response('tool', result)  [appends to hHM.msgs + disk]
                            ↓
              AI() loop continues with updated hHM.msgs
```

## Code Reference

| Component | File | Lines |
|-----------|------|-------|
| Tool dispatch loop | `src/ToolParser.py` | 435-592 |
| Tool execution | `src/ToolParser.py` | 245-416 |
| AI main loop | `src/Handle.py` | 1372-1626 |
| Model call (blocking) | `src/Handle.py` | 1484-1486 |
| Parse & detect tools | `src/Handle.py` | 503-683 |
| History append | `src/Handle.py` | 241-317 |
| Context summarization | `src/Handle.py` | 1153-1160 |
| Orchestra director | `src/OrchestraDirector.py` | 1-314 |
| Orchestra worker | `src/OrchestraWorker.py` | 1-149 |
| Server lock | `src/Server.py` | 42 |
| Koslenium daemon | `src/Handle.py` | 121 |
