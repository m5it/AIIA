# AGENTS.md

## Commands

```bash
source .venv/bin/activate       # activate virtual environment (Python 3.10)
python run.py                    # start AIIA interactive session
python run.py -m gemma3:12b     # specify model (default: gemma3:12b)
python run.py -p MediaAnalyst   # use MediaAnalyst persona (image/video analysis)
python run.py -Y "prompt"        # single request, no interactive session
python run.py -d                 # enable debug output
python run.py -T 0.8             # set temperature

python run_orchestra.py --port 9876        # start orchestra director
python run_worker.py --connect localhost:9876 --name w1 -m gemma3:12b  # start worker
```

## User Commands

| Command | Description |
|---------|-------------|
| `!MODE [plan\|build]` | Switch modes |
| `!MODELS` | List Ollama models (used ones starred) |
| `!MODEL <name>` | Switch AI model mid-session |
| `!PLAN [PREVIEW\|VIEW\|TASKS\|STATUS]` | View plan status |
| `!HELP` | Show all commands |
| `!STATS` | Token counts |
| `!NEW SESSION` | Full reset |

## Architecture

- **Entry point**: `run.py` → initializes `Handle` class from `src/Handle.py`
- **Orchestra entry points**: `run_orchestra.py` (director), `run_worker.py` (worker)
- **Core modules**: all in `src/` — `Handle.py` orchestrates chat, tools, actions, history
- **Personas**: `instruct/` directory — personality classes with plan/build system prompts, optional model override
- **Tools**: `tools/` directory — dynamically loaded Python classes that the AI invokes via `<ToolName>` XML syntax
- **Actions**: `actions/` directory — dynamically loaded action modules for specific tasks
- **History**: `history/` (gitignored) — session-based chat history, session ID tracked in `sessid.aiia`
- **Working dirs**: `workin/` (input for tools), `workout/` (output) — both gitignored

## XML Tool Invocation

The model invokes tools by writing XML blocks. Tools load dynamically when first invoked — no pre-loading needed.

**BASIC FORMAT:**
```xml
<ToolName>
<param1>value1</param1>
<param2>value2</param2>
</ToolName>
```

**Available tools (25 total):**
- `ReadFile` — Read from `workin/` (params: `<fileName>`)
- `WriteFile` — Write to `workout/` (params: `<fileName>`, `<contentOfFile>`)
- `AppendFile` — Append in `workout/` (params: `<fileName>`, `<contentOfFile>`)
- `CreateFile` — Create new file in `workout/` (fails if exists) (params: `<fileName>`, `<content>`)
- `ReplaceLine` — Replace specific line(s) in a file (params: `<fileName>`, `<fromLine>`, `<toLine>` optional, `<replacement>`)
- `ReadImage` — Read an image file, inject into conversation (params: `<fileName>`, `<prompt>` optional)
- `ImageTransform` — Transform images (resize, crop, convert, flip, rotate) (params: `<fileName>`, `<operation>`, `<params>` optional, `<output>` optional)
- `TreeView` — ASCII tree view of directory structure (params: `<path>` optional, `<depth>` default 3, `<pattern>` optional, `<showHidden>` optional)
- `List` — List files (params: `<path>` optional)
- `listTools` — Show all tools (no params, cached 10 min)
- `ExecuteScript` — Run `.py`, `.sh`, `.js` scripts (params: `<fileName>`, `<args>` optional)
- `Grep` — Regex search (params: `<pattern>`, `<fileName>` optional, `<recursive>` optional)
- `Diff` — Compare files (params: `<file1>`, `<file2>`, `<unified>` optional)
- `Sed` — Find/replace (params: `<pattern>`, `<replacement>`, `<fileName>`, `<inplace>` optional)
- `Find` — Find files by name (params: `<pattern>`, `<path>` optional)
- `Head` — First N lines (params: `<fileName>`, `<lines>` optional)
- `Tail` — Last N lines (params: `<fileName>`, `<lines>` optional)
- `Sort` — Sort lines (params: `<fileName>`, `<numeric>/<reverse>/<unique>` optional)
- `WWW` — Fetch a web page via the Java web client (params: `<url>`) — also invocable as `<www>`
- `SaveTip` — Save a tip with title and content to model storage (params: `<title>`, `<content>`)
- `GetTip` — Retrieve a saved tip by title (params: `<title>`, `<source>` optional)
- `ListTips` — List all saved tips (params: `<source>` optional)
- `DeleteTip` — Delete a tip by title (params: `<title>`, `<source>` optional)
- `ReinsertTip` — Reinsert a saved tip's entries into current chat history (params: `<title>`)

**Tool result caching:** Tools with a `cache_ttl` class attribute (e.g., listTools=600s, TreeView=300s) automatically cache results. Cache entries stored under `~/.config/ourai/tips/_cache/{toolname}/{key_hash}.json`. Cache invalidates on TTL expiry, tool file mtime change, `!CACHE_CLEAR`, `!NEW SESSION`, or `!UPDATE HANDLE`. Global default TTL: 86400s (1 day) via `TOOL_CACHE_TTL` in config.

**Example model output:**
```xml
<WriteFile>
<fileName>hello.sh</fileName>
<contentOfFile>echo "Hello World"</contentOfFile>
</WriteFile>

<ExecuteScript>
<fileName>hello.sh</fileName>
</ExecuteScript>
```

**Tip tool examples:**
```xml
<SaveTip>
<title>debug_command</title>
<content>strace -p PID -f -e trace=open,read</content>
</SaveTip>

<GetTip>
<title>debug_command</title>
</GetTip>

<ReinsertTip>
<title>debug_command</title>
</ReinsertTip>
```

## Module System

The project uses a custom module loader (`src/functions.py`):
- `importmodule("Name", reload=True, {'path': 'src'})` — imports and optionally reloads modules
- `initmodule(imported, "ClassName", opts)` — instantiates classes with options
- `functions.py` exists in both root and `src/` — `src/functions.py` is the canonical version used by core modules

## Instructions System

Mode instructions (system prompts for plan/build modes) live in `instruct/` as persona classes:
- `instruct/Developer.py` — default persona, provides `plan()` and `build()` methods
- `instruct/MediaAnalyst.py` — image/video analysis persona (default model: qwen3-vl:latest)
- Switch persona via `config.py`: `INSTRUCT_CLASS` option (e.g., `"Developer"`)
- The `[--#THINKING#--ID1--]` placeholder in both plan and build text is replaced at runtime based on mode and `BUILD_THINKING_DISABLED` option
- Create new personas by adding files to `instruct/` with the same `plan()`/`build()` interface

## Runtime Requirements

- Ollama server running (default: `localhost:11434`, override via `OLLAMA_HOST` env var)
- Virtual environment at `.venv/` (Python 3.10.12)
- Default model: `gemma3:12b` — change with `-m` flag
- LM Studio SDK in `package.json` but not used by Python code (Node deps appear unused)

## Cookie Sharing

The model can use a shared cookie file so `WWW` and `WWWJS` tools stay logged in across calls.

**Setup in `config.py`:**
```python
"COOKIE_FILE" : "tools/cookies.json",  # relative to project root, or absolute path
```

**Usage flow:**

1. Prepare cookies once (solve captcha / accept consent):
   ```xml
   <WWWJS>
   <url>https://google.com</url>
   <browser>true</browser>
   </WWWJS>
   ```
   Close the browser window when done — cookies auto-save to `COOKIE_FILE`.

2. Both tools now reuse those cookies automatically:
   ```xml
   <WWW>
   <url>https://google.com/search?q=test</url>
   <text>true</text>
   </WWW>
   ```
   Or with JS rendering:
   ```xml
   <WWWJS>
   <url>https://google.com/search?q=test</url>
   <text>true</text>
   </WWWJS>
   ```

When `COOKIE_FILE` is `None` (default), the tools work as before without cookies.

## Quirks

- **Indentation**: code uses tabs (not spaces) despite being Python
- **Dynamic reload**: tools/actions are reloaded on each use via custom import system — changes take effect immediately
- **Session state**: `sessid.aiia` tracks session counter; history files named `{session_id}.dbk` and `{session_id}.user.dbk`
- **No tests**: no test framework or test files configured
- **No linting**: no linter, formatter, or typechecker configured
