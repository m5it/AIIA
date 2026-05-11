# OurAI — AI Interactive Agent

**Version 0.3** | Terminal-based AI agent powered by Ollama, featuring dynamic XML tool invocation, plan/build mode system, secure command execution, and persistent session management.

## Features

- **Interactive AI Chat** — Terminal-based interface for conversing with local LLMs via Ollama (streaming response with thinking support)
- **XML Tool System** — AI invokes tools by writing XML blocks; tools are dynamically loaded Python classes with hot-reload
- **Plan / Build Modes** — structured workflow: plan mode for architecting tasks, build mode for executing them
- **Plan Manager** — Create plans, split into tasks, track progress, auto-continue on restart (`-c` flag)
- **Secure Terminal Tool** — Allowlist-based command execution with audit logging and 30s timeout
- **Persistent Sessions** — Chat history saved per session in `history/`; session ID tracked in `sessid.aiia`
- **Actions System** — Dynamically loaded action modules for reusable task sequences
- **Continue Support** — `-c` flag loads last unfinished plan from `PLAN.md` and resumes where you left off

---

## Table of Contents

- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Plan & Build System](#plan--build-system)
- [XML Tools Reference](#xml-tools-reference)
- [Terminal Commands](#terminal-commands)
- [Sessions & History](#sessions--history)
- [Custom Module Loader](#custom-module-loader)
- [Development](#development)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [License](#license)

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) server running (default: `localhost:11434`)
- A model pulled (tested with `gemma3:12b`, `gemma4:26b`, `qwen3-coder`)

### Installation

```bash
git clone <repo-url>
cd OurAI

python3 -m venv .venv
source .venv/bin/activate

pip install ollama
```

### Run (from any directory)

**Install globally (one-time):**
```bash
sudo ./OurAI -l    # Creates /usr/local/bin/ourai → start.sh
```

Now run `ourai` from **any** directory:
```bash
ourai                    # Start interactive session
ourai -m gemma3:12b      # Use specific model
ourai -c                 # Continue last unfinished plan
ourai -Y "List all Python files"  # Single request
ourai -d                 # Enable debug output
ourai -T 0.8             # Set temperature
ourai -h                 # Show help
```

**Uninstall:**
```bash
sudo ./OurAI -u    # Removes /usr/local/bin/ourai
```

**Without installing**, run directly:
```bash
source .venv/bin/activate
python run.py              # or ./start.sh
python run.py -m gemma3:12b -c
```

The `start.sh`/`ourai` script auto-detects the project root, sets `OURAI_PROJECT_DIR`, creates required directories, activates the venv, and passes all flags to `run.py`.

---

## Usage

### Basic Workflow

1. **Start a session**: `python run.py`
2. **Talk to the AI** — type any message, the AI responds with streaming output
3. **AI uses XML tools** automatically — you'll see tool invocations in the output
4. **Use `!` commands** for session management (see [Terminal Commands](#terminal-commands))
5. **Exit**: `CTRL+C` or type `!QUIT`

### Plan / Build Workflow

A structured two-phase workflow for complex tasks:

```
Phase 1: PLAN MODE  →  Create plan & tasks (architect)
Phase 2: BUILD MODE →  Execute tasks step by step (builder)
```

**Step-by-step:**

```
1. !MODE plan                   → Enter plan mode
2. AI creates plan & tasks      → Uses XML: <createPlan>, <createTask>
3. !MODE build                  → Switch to build mode
4. AI executes tasks one by one → Uses <nextTask>completed</nextTask>
5. AI calls <jobDone/>          → When all tasks complete
```

See [Plan & Build System](#plan--build-system) for full details.

---

## Configuration

All configuration lives in `config.py`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AI_MODEL` | str | `gemma4:26b` | Ollama model name |
| `MODE` | str | `build` | Initial mode: `plan` or `build` |
| `CONTINUE` | bool | `false` | Resume last plan on start |
| `DEBUG` | bool | `false` | Enable verbose debug output |
| `QUIET` | bool | `false` | Suppress all non-essential output |
| `AI_TEMPERATURE` | float | `0.7` | Model temperature |
| `AI_MAX_CONTENT_LEN` | int | `20000` | Max chars per response |
| `AI_MAX_SESSION_LEN` | int | `200000` | Max total session context |
| `working_dir` | str | `$OURAI_PROJECT_DIR` | Project working directory |
| `plans_path` | str | `plans/` | Directory for JSON plan files |
| `history_path` | str | `history/` | Directory for session history |
| `tools_path` | str | `tools/` | Directory for tool modules |
| `actions_path` | str | `actions/` | Directory for action modules |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `localhost:11434` | Ollama server address |
| `OURAI_PROJECT_DIR` | project root | Used as `working_dir` for PLAN.md/HISTORY.md |

---

## Architecture

```
OurAI/
├── run.py                        # Entry point — CLI flag parsing, main loop
├── config.py                     # All configuration & system prompts
├── start.sh                      # Startup script (auto-setup, path resolution)
├── AGENTS.md                     # Development notes & conventions
├── PLAN.md                       # Current/active plan (working dir only)
├── HISTORY.md                    # Session transcript (working dir only)
├── sessid.aiia                   # Session counter file
│
├── src/
│   ├── Handle.py                 # Core orchestrator — chat loop, response, streaming
│   ├── ToolParser.py             # XML tool parser, router, plan tool handlers
│   ├── Commands.py               # !-prefixed terminal commands (20+ commands)
│   ├── PlanManager.py            # PlanBase, Plan, PlanTask, TaskLog classes
│   ├── PlanSaver.py              # PLAN.md / HISTORY.md persistence
│   ├── HistoryManager.py         # Session history load/save
│   ├── functions.py              # Custom module loader, utilities
│   ├── Prepare.py                # Session init, mode instructions
│   ├── ToolChooser.py            # Tool management & selection
│   ├── Actions.py                # Action module management
│   ├── Log.py                    # Terminal output logging
│   └── Speak.py                  # Text-to-speech (experimental)
│
├── tools/                        # XML-invokable tool modules (17 files)
│   ├── tool_Terminal.py          # Secure terminal execution
│   ├── tool_ReadFile.py          # Read file content
│   ├── tool_WriteFile.py         # Write/overwrite files
│   ├── tool_AppendFile.py        # Append or insert at line
│   ├── tool_CreateFile.py        # Create file (fails if exists)
│   ├── tool_List.py              # List directory contents
│   ├── tool_listTools.py         # List all available tools
│   ├── tool_ExecuteScript.py     # Run scripts (.py/.sh/.js...)
│   ├── tool_Grep.py              # Regex search in files
│   ├── tool_Diff.py              # Compare two files
│   ├── tool_Sed.py               # Find/replace in files
│   ├── tool_Find.py              # Find files by name pattern
│   ├── tool_Head.py              # First N lines of file
│   ├── tool_Tail.py              # Last N lines of file
│   ├── tool_Sort.py              # Sort file lines
│   └── create_file.py            # Utility function
│
├── actions/                      # Reusable action modules
│   ├── example_rest.py           # REST API example action
│   ├── grandekos_createpage.py   # Page creation action
│   └── grandekos_viewpaths.py    # Path viewer action
│
├── history/                      # Session chat history (gitignored)
├── plans/                        # JSON plan files (gitignored)
│
├── test/                         # Test scripts
│   ├── test_all_tools.sh
│   ├── test_full_flow.py
│   ├── test_terminal.sh
│   ├── test_writefile.py
│   └── test_writefile_issue.py
│
└── .venv/                        # Python virtual environment
```

### Core Components

| Component | File | Role |
|-----------|------|------|
| **Handle** | `src/Handle.py` | Main class — `Chat()` loop, `Response()` for history, `Stream()` for AI output, `Parse()` for tool extraction, `AI()` for model calls |
| **ToolParser** | `src/ToolParser.py` | Parses XML from AI responses, routes to plan or regular tools, handles all tool types |
| **Commands** | `src/Commands.py` | `!`-prefixed terminal commands — mode switching, session control, plan viewing |
| **PlanManager** | `src/PlanManager.py` | `PlanBase` (class-level state), `Plan` (per-plan), `PlanTask` (per-task), `TaskLog` (per-log-entry) |
| **PlanSaver** | `src/PlanSaver.py` | Saves/loads `PLAN.md` and `HISTORY.md` to working directory |
| **HistoryManager** | `src/HistoryManager.py` | Manages session history files (`history/` directory) |
| **functions** | `src/functions.py` | Custom module loader (`importmodule`, `initmodule`), file I/O, regex helpers |
| **Prepare** | `src/Prepare.py` | Session ID generation, file name updates, mode instruction injection |

---

## Plan & Build System

### Overview

The plan/build system lets you break complex tasks into structured, trackable steps.

- **Plan Mode** (`!MODE plan`): AI acts as architect — thinking enabled, creates plans and tasks using XML tools
- **Build Mode** (`!MODE build`): AI acts as builder — thinking disabled, executes tasks, reports progress

### Plan Management

Plans persist as JSON files in `plans/` and as Markdown in `PLAN.md` (working directory).

#### XML Tools (Plan Mode)

| Tool | XML | Description |
|------|-----|-------------|
| **createPlan** | `<createPlan><title>...</title><instructions>...</instructions></createPlan>` | Create a new plan (must be called first) |
| **createTask** | `<createTask><title>...</title><instruction>...</instruction></createTask>` | Add a task to the current plan |
| **updateTask** | `<updateTask><id>...</id><status>pending|completed|blocked</status></updateTask>` | Update task status |
| **deleteTask** | `<deleteTask><id>...</id></deleteTask>` | Remove a specific task |
| **deletePlan** | `<deletePlan><id>...</id></deletePlan>` | Delete a specific plan by ID |
| **deleteDraft** | `<deleteDraft/>` | Delete the current draft plan |
| **deleteAllPlans** | `<deleteAllPlans/>` | Delete all saved plans |
| **viewTask** | `<viewTask/>` or `<viewTask><id>...</id></viewTask>` | View plan or specific task |
| **listTasks** | `<listTasks/>` | List all tasks in current plan |

#### XML Tools (Build Mode)

| Tool | XML | Description |
|------|-----|-------------|
| **nextTask** | `<nextTask>completed</nextTask>` or `<nextTask>blocked</nextTask>` | Mark current task and get next one |
| **LogProgress** | `<LogProgress><taskId>...</taskId><whatWasDone>...</whatWasDone></LogProgress>` | Log progress on current task |
| **jobDone** | `<jobDone/>` | Finish the plan (all tasks done) |
| **startBuild** | `<startBuild/>` or `<startBuild><planId>...</planId></startBuild>` | Start build mode with optional plan ID |

Build mode also includes all plan management tools (createTask, viewTask, etc.).

### Plan Flow

```
         !MODE plan
              │
              ▼
    ┌─────────────────┐
    │  createPlan     │  AI creates plan
    │  createTask x N │  AI adds tasks
    └────────┬────────┘
             │
             ▼
         !MODE build
             │
             ▼
    ┌─────────────────┐
    │  Execute task   │  AI works on current task
    │  nextTask(ok)   │  Mark done, get next
    │  ...repeat...   │
    │  jobDone()      │  All tasks complete
    └────────┬────────┘
             │
             ▼
        Plan finished
```

### Continue Mode

When you run with `-c`:

```
python run.py -c
```

1. The system reads `PLAN.md` from the working directory
2. Loads the most recent unfinished plan
3. Finds the task marked `in_progress`
4. Presents it to the AI to continue working

### Plan Classes

```
PlanBase (class-level state)
├── draft — current working plan (Plan instance or None)
├── done — dict of completed plans {id: Plan}
│
├── Create(title, instructions, path) → Plan
├── Delete(id, path) → result
├── View(id) → dict
├── List(path) → list
└── LoadAll(path) → loads JSON files into done

Plan (per-plan)
├── id, title, instructions
├── startTimestamp, endTimestamp
├── tasks — dict of {task_id: PlanTask}
│
├── createTask(instruction, title) → PlanTask
├── nextTask(handle, status) → dict (includes next instruction)
├── jobDone(handle) → marks complete
├── save(path) → JSON file
└── load(id, path) → Plan

PlanTask (per-task)
├── id, title, instruction
├── status: pending | in_progress | completed | blocked
├── startTimestamp, endTimestamp
├── log — list of TaskLog entries
│
├── view() → dict
├── update(status) → dict
└── delete() → dict

TaskLog
├── timestamp
└── text
```

---

## XML Tools Reference

The AI invokes tools by writing XML blocks in its response. All 15 tools are auto-discovered and loaded on first use.

### File Tools

#### ReadFile
```xml
<ReadFile>
<fileName>path/to/file.txt</fileName>
</ReadFile>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | Path to file |

#### WriteFile
```xml
<WriteFile>
<fileName>path/to/output.txt</fileName>
<contentOfFile>File content here</contentOfFile>
</WriteFile>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | Output file path |
| `contentOfFile` | string | yes | Content to write (overwrites if exists) |

Creates parent directories automatically.

#### AppendFile
```xml
<AppendFile>
<fileName>path/to/file.txt</fileName>
<contentOfFile>Line to append</contentOfFile>
<fromLineNumber>1</fromLineNumber>
</AppendFile>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | File path |
| `contentOfFile` | string | yes | Content to append |
| `fromLineNumber` | int | no | `0`=prepend, `-1`=append (default), N=insert at line N |

#### CreateFile
```xml
<CreateFile>
<fileName>path/to/newfile.txt</fileName>
<contentOfFile>File content</contentOfFile>
</CreateFile>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | New file path |
| `contentOfFile` | string | yes | Initial content |

Fails if file already exists (use WriteFile to overwrite).

### Search & Process Tools

#### Grep
```xml
<Grep>
<pattern>search_term</pattern>
<fileName>file.txt</fileName>
<recursive>true</recursive>
</Grep>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | yes | Regex pattern |
| `fileName` | string | no | File to search (omitted = search all) |
| `recursive` | string | no | "true" to search recursively |

#### Diff
```xml
<Diff>
<file1>original.txt</file1>
<file2>modified.txt</file2>
<unified>3</unified>
</Diff>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `file1` | string | yes | First file |
| `file2` | string | yes | Second file |
| `unified` | int | no | Context lines (default: 3) |

#### Sed
```xml
<Sed>
<pattern>old_text</pattern>
<replacement>new_text</replacement>
<fileName>file.txt</fileName>
<inplace>true</inplace>
</Sed>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | yes | Regex to find |
| `replacement` | string | yes | Replacement text |
| `fileName` | string | yes | File to edit |
| `inplace` | string | no | "true" to edit in place |

#### Find
```xml
<Find>
<pattern>*.py</pattern>
<path>.</path>
</Find>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | yes | Glob pattern |
| `path` | string | no | Directory to search (default: `.`) |

#### Head
```xml
<Head>
<fileName>file.txt</fileName>
<lines>10</lines>
</Head>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | File path |
| `lines` | int | no | Number of lines (default: 10) |

#### Tail
```xml
<Tail>
<fileName>file.txt</fileName>
<lines>10</lines>
</Tail>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | File path |
| `lines` | int | no | Number of lines (default: 10) |

#### Sort
```xml
<Sort>
<fileName>file.txt</fileName>
<numeric>true</numeric>
<reverse>true</reverse>
<unique>true</unique>
</Sort>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | File path |
| `numeric` | bool | no | Numeric sort |
| `reverse` | bool | no | Reverse sort |
| `unique` | bool | no | Unique lines only |

### Execution Tools

#### Terminal
```xml
<Terminal>
<arg1>ls</arg1>
<arg2>-la</arg2>
<arg3>src/</arg3>
</Terminal>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `arg1` | string | yes | Program/command (must be in allowlist) |
| `arg2`-`arg5` | string | no | Up to 4 additional arguments |

**Security features:**
- Allowlist of ~40 approved programs only
- `shell=False` prevents command injection
- 30-second timeout on all executions
- All commands logged to `terminal_audit.log`

**Allowed programs:** `ls`, `dir`, `cat`, `echo`, `pwd`, `whoami`, `date`, `id`, `grep`, `find`, `sort`, `head`, `tail`, `wc`, `awk`, `sed`, `bash`, `sh`, `python3`, `python`, `node`, `perl`, `ruby`, `git`, `make`, `cmake`, `gcc`, `g++`, `ping`, `curl`, `wget`, `netstat`, `ss`, `ps`, `top`, `df`, `du`, `free`, `mkdir`, `cp`, `mv`, `touch`, `chmod`, `chown`

#### ExecuteScript
```xml
<ExecuteScript>
<fileName>script.sh</fileName>
<args>-x -v</args>
</ExecuteScript>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | yes | Script file (.py, .sh, .js, etc.) |
| `args` | string | no | Arguments (space-separated or JSON array) |

**Automatic routing:** If `fileName` is a non-script binary (e.g., `ls`, `git`), the call is automatically routed to the Terminal tool.

#### listTools
```xml
<listTools/>
```

No parameters. Lists all available tools with their descriptions and parameters.

#### List
```xml
<List>
<path>.</path>
</List>
```
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | no | Directory path (default: `.`) |

---

## Terminal Commands

All commands start with `!` (case-sensitive). The following are available:

### Session Commands

| Command | Description |
|---------|-------------|
| `!MODE [plan\|build]` | Switch between plan and build mode. Shows current mode if no argument. |
| `!NEW_SESSION` | Start a new session (resets context). |
| `!BREAK_SESSION` | Start a new history file for the session. |
| `!QUIT` | Exit the program. |
| `!UPDATE_HANDLE` | Reload the Handle class (hot-reload). |

### Plan Commands

| Command | Description |
|---------|-------------|
| `!PLAN [PREVIEW\|VIEW\|TASKS\|STATUS] [task_id]` | View plan status, tasks, and progress. |
| `!START_BUILD [planId]` | Start build mode from current draft or specific plan by ID. |

### Memory & History Commands

| Command | Description |
|---------|-------------|
| `!PH` | Preview current chat history. |
| `!PM` | Preview memorized messages. |
| `!MAH` | Load all history into memory. |
| `!MS [num]` | Load specific history file. |
| `!ML` | Load last assistant message from memory. |
| `!MDR [num]` | Delete specific memory row. |
| `!MDA` | Delete all memory rows. |

### Stats & Tools Commands

| Command | Description |
|---------|-------------|
| `!STATS` | Display program statistics. |
| `!TOOLS` | List and choose which tools to load. |
| `!CT` | Clear all loaded tools. |

### Action Commands

| Command | Description |
|---------|-------------|
| `!AO [num]` or `!AO [num].SET.[key]=[value]` or `!AO [num].GET.[key]` | Configure action options. |
| `!AOS [num]` | Save action options. |
| `!AOL` | List action options. |
| `!IA` | Import actions from files. |
| `!PA` | Preview imported actions. |
| `!EA [num]` | Execute a specific action. |

### Other Commands

| Command | Description |
|---------|-------------|
| `!HELP` | Show help. |
| `!LOAD [file]` | Load file content into context. |

---

## Sessions & History

### How Session Tracking Works

1. **`sessid.aiia`** (in project root) stores a counter integer
2. Each session increments the counter and creates:
   - `history/{session_id}.dbk` — raw JSON chat history
   - `history/{session_id}.user.dbk` — user-only messages
3. At startup, the last session's history is loaded if `AI_FILE_LOAD_HISTORY` is true

### History Files

- **`history/*.dbk`** — Full session transcripts (JSON lines, one message per line)
- **`HISTORY.md`** — Human-readable session log saved to working directory
- **`PLAN.md`** — Current plan status saved to working directory

### Continue Mode (`-c`)

```
python run.py -c
```

1. Reads `PLAN.md` from working directory
2. Finds the newest unfinished plan
3. Loads it as the current draft
4. AI resumes working on the in-progress task

---

## Custom Module Loader

The project uses a custom module system (`src/functions.py`) instead of standard Python imports for tools, actions, and core modules:

```python
from src.functions import importmodule, initmodule

# Import with hot-reload support
mod = importmodule("Handle", reload=True, {'path': 'src'})

# Instantiate a class from the module
obj = initmodule(mod, "Handle", options)
```

### Why?

- **Hot-reload**: Modules in `tools/` and `actions/` are reloaded on every use — changes take effect immediately without restart
- **Dynamic discovery**: Tools are found and loaded based on XML invocation, not pre-configured
- **Path resolution**: The `path` option lets you resolve modules relative to project directories

### Helper Functions in functions.py

| Function | Description |
|----------|-------------|
| `importmodule(name, reload, opts)` | Import/reload a module by name, with optional path prefix |
| `initmodule(module, classname, opts)` | Instantiate a named class with constructor args |
| `splitFileNameExtension(text)` | Split filename into `{name, extension}` dict |
| `user_input(opts)` | Read stdin character by character |
| `rmatch(input, regex)` | Regex match, returns match object or False |
| `pmatch(input, regex)` | Regex match, returns captured groups as list |
| `fread(filename)` | Read entire file as string |
| `fwrite(filename, data, overwrite)` | Write/append to file |
| `crc32b(text)` | CRC32 hash as hex string |
| `urlencode(text)` | URL-encode a string |

---

## Development

### Adding a New Tool

1. Create `tools/tool_YourTool.py`:

```python
class YourTool():
	def __init__(self):
		self.info = {
			"name":"YourTool",
			"description":"Description of your tool.",
			"parameters":{
				"returnType":"string",
				"required":["param1"],
				"properties":{
					"param1":{
						"type":"string",
						"description":"Description of param1."
					}
				}
			}
		}
	
	def run(self, param1="", **kwargs):
		# Tool logic here
		return "result"
```

2. The tool is auto-discovered when the AI invokes `<YourTool><param1>value</param1></YourTool>` in its response.

### Adding a New Action

1. Create `actions/your_action.py`:

```python
class Action():
	def __init__(self, opts):
		self.name = "your_action"
		self.description = "Description of your action"
		self.options = {'key': 'default_value'}
	
	def Exec(self, args={}):
		# Action logic
		return "result"
	
	def Test(self):
		return True
```

2. Use `!IA` to import, then `!EA [num]` to execute.

### Adding a New Terminal Command

Add an entry to the `self.cmds` dictionary in `src/Commands.py`:

```python
"YOUR_COMMAND":{
	"name"       :"Your Command",
	"description":"What your command does.",
	"regex"      :r"^!YOUR_COMMAND(\s+\w+)?$",
	"usage"      :"!YOUR_COMMAND [optional_arg]",
	"func"       :self.CMD_YOUR_COMMAND,
},
```

Then implement `CMD_YOUR_COMMAND(self, inp="")` method.

### Code Conventions

- **Indentation**: Tabs, not spaces
- **No comments**: Avoid adding comments
- **Dynamic reload**: Changes to tools/actions take effect immediately (no restart needed)
- **No linter/formatter**: No pre-configured linting or formatting

### Testing

```bash
# Test Terminal tool directly
python3 -c "from tools.tool_Terminal import Terminal; t = Terminal(); print(t.run(arg1='ls', arg2='-la'))"

# Run full flow test
python3 test/test_full_flow.py

# Run with debug output
python run.py -d

# Check terminal audit log
cat terminal_audit.log
```

---

## FAQ & Troubleshooting

### "ollama library not found"

Install it:
```bash
source .venv/bin/activate
pip install ollama
```

### "Connection refused" when starting

Make sure Ollama is running:
```bash
ollama serve           # Start Ollama server
ollama list            # Check available models
ollama pull gemma3:12b # Pull a model if needed
```

### AI is not using tools

- Check the system prompt in `config.py` (`MODE_INSTRUCTIONS_BUILD` or `MODE_INSTRUCTIONS_PLAN`)
- Make sure the AI is in the correct mode (`!MODE plan` for plan tools, `!MODE build` for execution)
- Some models need explicit prompting to use XML tools

### AI calling the same tool repeatedly

This is usually a model behavior issue, not a code bug. Try:
- Using a different model (`-m qwen3-coder:30b`)
- The AI loop has a 5-iteration maximum to prevent infinite loops
- Check if the tool result contains useful information

### Plan not continuing after restart

- Run with `-c` flag: `python run.py -c`
- Verify `PLAN.md` exists in your working directory
- The plan must have status `in_progress` (not `completed`)

### "File already exists" from CreateFile

Use `WriteFile` instead — it overwrites existing files. `CreateFile` intentionally fails if the target exists.

---

## License

Copyright 2026 Blaz Kos

Licensed under the Modified Apache License, Version 2.0.
See [LICENSE](LICENSE) for full terms including notification and payment obligations for commercial use.

**Key terms:**
- Commercial use requires written notification to w4d4f4k@gmail.com within 30 days
- Commercial use requires payment of a license fee as determined by the Licensor
- The Licensor reserves audit rights
- Governing law: Spain (Canary Islands) / Slovenia (for Slovenian consumers)

---

## Project Status

**Version 0.3** — Active development. The core architecture is stable. New features include the plan/build mode system, plan management, and continue support.
