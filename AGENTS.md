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

## Text-Based Tool Invocation

The model can invoke tools by outputting `!TOOL ToolName key=value` in responses. All tools in `tools/` are auto-loaded.

**Available tools:**
- `ReadFile` — Read file from `workin/` (params: `fileName`)
- `WriteFile` — Write file to `workout/` (params: `fileName`, `contentOfFile`)
- `AppendFile` — Append to file in `workout/` (params: `fileName`, `contentOfFile`)
- `CreateFile` — Create new file in `workout/` (fails if exists) (params: `fileName`, `content`)
- `List` — List files in a path (params: `path` optional)
- `listTools` — Show all available tools (no params)
- `ExecuteScript` — Run script files `.py`, `.sh`, `.js`, etc. (params: `fileName`, `args` optional)
- `Grep` — Search files by regex pattern (params: `pattern`, `fileName` optional, `recursive` optional)
- `Diff` — Compare two files (params: `file1`, `file2`, `unified` optional)
- `Sed` — Find/replace in files (params: `pattern`, `replacement`, `fileName`, `inplace` optional)
- `Find` — Find files by name pattern (params: `pattern`, `path` optional)
- `Head` — Show first N lines of file (params: `fileName`, `lines` optional)
- `Tail` — Show last N lines of file (params: `fileName`, `lines` optional)
- `Sort` — Sort lines in file (params: `fileName`, `numeric`/`reverse`/`unique` optional)

**Example model output:**
```
!TOOL WriteFile fileName=hello.py contentOfFile="print('Hello World')"
!TOOL ExecuteScript fileName=hello.py
!TOOL Grep pattern="TODO" recursive=true
!TOOL Head fileName=script.py lines=20
!TOOL Diff file1=old.txt file2=new.txt unified=true
```

## Module System

The project uses a custom module loader (`src/functions.py`):
- `importmodule("Name", reload=True, {'path': 'src'})` — imports and optionally reloads modules
- `initmodule(imported, "ClassName", opts)` — instantiates classes with options
- `functions.py` exists in both root and `src/` — `src/functions.py` is the canonical version used by core modules

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
