# AGENTS.md

## Commands

```bash
source .venv/bin/activate       # activate virtual environment (Python 3.10)
python run.py                    # start AIIA interactive session
python run.py -m gemma3:12b     # specify model (default: gemma3:12b)
python run.py -Y "prompt"        # single request, no interactive session
python run.py -d                 # enable debug output
python run.py -T 0.8             # set temperature
```

## Architecture

- **Entry point**: `run.py` → initializes `Handle` class from `src/Handle.py`
- **Core modules**: all in `src/` — `Handle.py` orchestrates chat, tools, actions, history
- **Tools**: `tools/` directory — dynamically loaded Python classes that the AI can call via `!TOOL` syntax
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

**Available tools (15 total):**
- `ReadFile` — Read from `workin/` (params: `<fileName>`)
- `WriteFile` — Write to `workout/` (params: `<fileName>`, `<contentOfFile>`)
- `AppendFile` — Append in `workout/` (params: `<fileName>`, `<contentOfFile>`)
- `CreateFile` — Create new file in `workout/` (fails if exists) (params: `<fileName>`, `<content>`)
- `List` — List files (params: `<path>` optional)
- `listTools` — Show all tools (no params)
- `ExecuteScript` — Run `.py`, `.sh`, `.js` scripts (params: `<fileName>`, `<args>` optional)
- `Grep` — Regex search (params: `<pattern>`, `<fileName>` optional, `<recursive>` optional)
- `Diff` — Compare files (params: `<file1>`, `<file2>`, `<unified>` optional)
- `Sed` — Find/replace (params: `<pattern>`, `<replacement>`, `<fileName>`, `<inplace>` optional)
- `Find` — Find files by name (params: `<pattern>`, `<path>` optional)
- `Head` — First N lines (params: `<fileName>`, `<lines>` optional)
- `Tail` — Last N lines (params: `<fileName>`, `<lines>` optional)
- `Sort` — Sort lines (params: `<fileName>`, `<numeric>/<reverse>/<unique>` optional)
- `WWW` — Fetch a web page via the Java web client (params: `<url>`) — also invocable as `<www>`

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

## Module System

The project uses a custom module loader (`src/functions.py`):
- `importmodule("Name", reload=True, {'path': 'src'})` — imports and optionally reloads modules
- `initmodule(imported, "ClassName", opts)` — instantiates classes with options
- `functions.py` exists in both root and `src/` — `src/functions.py` is the canonical version used by core modules

## Instructions System

Mode instructions (system prompts for plan/build modes) live in `instruct/` as persona classes:
- `instruct/Developer.py` — default persona, provides `plan()` and `build()` methods
- Switch persona via `config.py`: `INSTRUCT_CLASS` option (e.g., `"Developer"`)
- The `--#BUILD_THINKING_DISABLED#--` placeholder in build text is replaced at runtime based on `BUILD_THINKING_DISABLED` option
- Create new personas by adding files to `instruct/` with the same `plan()`/`build()` interface

## Runtime Requirements

- Ollama server running (default: `localhost:11434`, override via `OLLAMA_HOST` env var)
- Virtual environment at `.venv/` (Python 3.10.12)
- Default model: `gemma3:12b` — change with `-m` flag
- LM Studio SDK in `package.json` but not used by Python code (Node deps appear unused)

## Quirks

- **Indentation**: code uses tabs (not spaces) despite being Python
- **Dynamic reload**: tools/actions are reloaded on each use via custom import system — changes take effect immediately
- **Session state**: `sessid.aiia` tracks session counter; history files named `{session_id}.dbk` and `{session_id}.user.dbk`
- **No tests**: no test framework or test files configured
- **No linting**: no linter, formatter, or typechecker configured
