# AIIA - AI Interactive Assistant

AIIA is a terminal-based AI assistant powered by Ollama, featuring dynamic tool loading, secure terminal command execution, and a flexible mode system (plan/build) for controlling AI behavior.

## Features

- **Interactive AI Chat**: Terminal-based interface for conversing with local LLMs via Ollama
- **Dynamic Tool System**: XML-based tool invocation with automatic tool loading
- **Secure Terminal Tool**: Execute terminal commands with allowlist-based security and audit logging
- **Mode System**: Switch between "plan" (read-only) and "build" (full access) modes
- **Modular Architecture**: Tools and actions are dynamically loaded Python modules
- **Session Management**: Persistent chat history with session-based tracking
- **Custom Module Loader**: Hot-reloadable modules with `importmodule()` and `initmodule()`

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) server running (default: `localhost:11434`)
- Virtual environment at `.venv/`

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd OurAI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # if available, or install ollama Python package
```

### Configuration

Edit `run.py` to configure:
- `AI_MODEL`: Model to use (default: `gemma3:12b`)
- `AI_TEMPERATURE`: Temperature for generation (default: `0.7`)
- `MODE`: Initial mode - `plan` or `build` (default: `build`)
- `OLLAMA_HOST`: Ollama server address (or set environment variable)

### Running

```bash
# Activate virtual environment
source .venv/bin/activate

# Start interactive session (default model: gemma3:12b)
python run.py

# Use specific model
python run.py -m qwen3-coder:30b

# Single request, no interactive session
python run.py -Y "your prompt here"

# Enable debug output
python run.py -d

# Set temperature
python run.py -T 0.8
```

## Tools

Tools are Python classes in the `tools/` directory that the AI can invoke using XML syntax. All tools now use the `work/` directory for both input and output.

### Available Tools

| Tool | Description | Parameters |
|------|-------------|-------------|
| **Terminal** | Execute terminal commands securely | `arg1`, `arg2`, ... (dynamic args) |
| **ReadFile** | Read file from `work/` | `fileName` |
| **WriteFile** | Write file to `work/` | `fileName`, `contentOfFile` |
| **AppendFile** | Append to file in `work/` | `fileName`, `contentOfFile` |
| **CreateFile** | Create new file in `work/` (fails if exists) | `fileName`, `content` |
| **List** | List files in a path | `path` (optional) |
| **listTools** | Show all available tools | (none) |
| **ExecuteScript** | Run script (.py, .sh, .js, etc.) | `fileName`, `args` (optional) |
| **Grep** | Search files by regex pattern | `pattern`, `fileName`, `recursive` (optional) |
| **Diff** | Compare two files | `file1`, `file2`, `unified` (optional) |
| **Sed** | Find/replace in files | `pattern`, `replacement`, `fileName`, `inplace` (optional) |
| **Find** | Find files by name pattern | `pattern`, `path` (optional) |
| **Head** | Show first N lines of file | `fileName`, `lines` (optional) |
| **Tail** | Show last N lines of file | `fileName`, `lines` (optional) |
| **Sort** | Sort lines in file | `fileName`, `numeric`, `reverse`, `unique` (optional) |

### Terminal Tool Security

The Terminal tool (`tools/tool_Terminal.py`) provides secure command execution:

- **Allowlist**: Only pre-approved programs can be executed
- **Audit Logging**: All commands are logged to `work/terminal_audit.log`
- **Timeout**: Commands have a 30-second timeout
- **Shell Security**: Uses `shell=False` to prevent command injection

Default allowed programs: `ls`, `dir`, `cat`, `echo`, `pwd`, `whoami`, `date`, `id`, `grep`, `find`, `sort`, `head`, `tail`, `wc`, `awk`, `sed`, `bash`, `sh`, `python3`, `python`, `node`, `perl`, `ruby`, `git`, `make`, `cmake`, `gcc`, `g++`, `ping`, `curl`, `wget`, `netstat`, `ss`, `ps`, `top`, `df`, `du`, `free`, `mkdir`, `cp`, `mv`, `touch`, `chmod`, `chown`

### Tool Invocation (XML Syntax)

The AI invokes tools using XML blocks:

```xml
<ReadFile>
<fileName>test.txt</fileName>
</ReadFile>

<WriteFile>
<fileName>output.txt</fileName>
<contentOfFile>Hello World</contentOfFile>
</WriteFile>

<Terminal>
<arg1>ls</arg1>
<arg2>-la</arg2>
<arg3>work/</arg3>
</Terminal>
```

### Automatic Routing

When the AI uses `ExecuteScript` with a non-script file (e.g., `ls`, `grep`), AIIA automatically routes the call to the Terminal tool.

## Modes

AIIA has a mode system controlled by the `!MODE` command:

### Plan Mode (`!MODE 0`)
- Read-only mode
- AI can read files and analyze code
- Cannot make changes (write files, execute modifying commands)
- Useful for code review and analysis

### Build Mode (`!MODE 1`)
- Full access mode (default)
- AI can read, write, and execute commands
- Suitable for development tasks

### Mode Commands

```
!MODE       # Show current mode
!MODE 0     # Switch to plan mode
!MODE 1     # Switch to build mode
```

## Commands Reference

Commands start with `!` and are processed by the `Handle.Commands` class:

| Command | Description |
|---------|-------------|
| `!MODE [0\|1]` | Switch between plan (0) and build (1) mode |
| `!NEW SESSION` | Start a new session (like restarting) |
| `!BREAK SESSION` | Start new history |
| `!STATS` | Display program statistics |
| `!TOOLS` | Choose tools to use |
| `!CT` | Clear loaded tools |
| `!PH` | Preview current chat history |
| `!PM` | Preview memorized messages |
| `!ML` | Memory last assistant message |
| `!MDR [num]` | Delete specific memory row |
| `!MDA` | Delete all memory rows |
| `!AO [num]` | List action options |
| `!IA` | Import actions from classes |
| `!PA` | Preview imported actions |
| `!EA [num]` | Execute specific action |
| `!LOAD file` | Load file content into context |

## Architecture

```
OurAI/
├── run.py                    # Entry point
├── src/
│   ├── Handle.py             # Core chat logic, tool execution, commands
│   ├── functions.py         # Custom module loader (importmodule, initmodule)
│   ├── ToolChooser.py       # Tool selection and management
│   ├── ActionChooser.py     # Action selection and management
│   ├── HistoryManager.py    # Chat history persistence
│   └── Log.py               # Logging utilities
├── tools/                   # Dynamically loaded tools
│   ├── tool_Terminal.py     # Secure terminal execution
│   ├── tool_ReadFile.py     # Read files
│   ├── tool_WriteFile.py    # Write files
│   └── ...                 # Other tools
├── actions/                 # Dynamically loaded actions
├── work/                    # Working directory (input/output for tools)
├── history/                 # Session-based chat history (gitignored)
└── .venv/                  # Python virtual environment
```

### Core Components

- **Handle**: Main class orchestrating chat, tools, actions, and history
- **Commands**: Inner class handling `!` commands
- **ToolChooser**: Manages available and loaded tools
- **ActionChooser**: Manages available and loaded actions
- **HistoryManager**: Persistent chat history with session tracking
- **Module Loader** (`functions.py`): Custom import system with hot-reload support

### Module System

AIIA uses a custom module loader (`src/functions.py`):

```python
# Import and optionally reload a module
mod = importmodule("Handle", reload=True, {'path': 'src'})

# Initialize a class from the module
obj = initmodule(mod, "Handle", options)
```

Modules in `tools/` and `actions/` are automatically reloaded on each use, so changes take effect immediately.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server address | `localhost:11434` |

## Working Directories

- `work/`: Unified directory for tool input/output (replaces old `workin/` and `workout/`)
- `history/`: Session-based chat history (gitignored)
- `work/terminal_audit.log`: Audit log for all Terminal tool executions

## Development

### Code Style

- **Indentation**: Tabs (not spaces) despite being Python
- **Dynamic Reload**: Tools/actions are reloaded on each use via custom import system
- **No Comments**: Avoid adding comments unless explicitly requested

### Adding a New Tool

1. Create `tools/tool_YourTool.py`:

```python
class YourTool():
    def __init__(self):
        self.info = {
            "name":"YourTool",
            "description":"Description of your tool.",
            "parameters":{
                "returnType":"string",  # or "object"
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

2. The tool will be automatically discovered and loaded when invoked via XML

### Testing

```bash
# Test Terminal tool directly
python3 -c "from tools.tool_Terminal import Terminal; t = Terminal(); print(t.run(arg1='ls', arg2='-la'))"

# Check audit log
cat work/terminal_audit.log

# Run with debug output
python run.py -d
```

## Known Quirks

- **No Tests**: No test framework or test files configured
- **No Linting**: No linter, formatter, or typechecker configured
- **Indentation**: Code uses tabs (not spaces)
- **Dynamic Reload**: Tools/actions reload on each use - changes take effect immediately
- **Session State**: `sessid.aiia` tracks session counter; history files named `{session_id}.dbk` and `{session_id}.user.dbk`

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

## Issues

Report issues at: [github-repo-url]/issues
