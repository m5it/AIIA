# AIIA — AI Interactive Agent

**Version 1.1.6** | Terminal-based AI agent powered by Ollama or any OpenAI-compatible server (e.g. vLLM), featuring dynamic XML tool invocation, plan/build mode system, secure command execution, HTTP SSE server for editor integration, persistent session management, and an opt-in aiia_work marketplace client.

[![codecov](https://codecov.io/gh/m5it/OurAI/branch/main/graph/badge.svg)](https://codecov.io/gh/m5it/OurAI)

> **Recent updates:** v1.1.6 — new `aiia_work` marketplace client (`python run.py --work` / `!WORK` commands), Ctrl+D "Stop AI" no longer disables plan auto-continue, and a round of Handle/Commands/backends refactors. See [CHANGELOG.md](CHANGELOG.md) for details.

## Features

- **Ctrl+D AI Loop Interrupt** — Press Ctrl+D during AI iteration to pause and show a menu: continue, return to chat prompt, or cancel session. "Stop AI" only ends the current round — plan auto-continue stays enabled (toggle deliberately with `!AUTO true|false`)
- **aiia_work Marketplace Client** — Opt-in client (`python run.py --work`) for the aiia_work marketplace: generate/manage API keys, create & browse projects, apply to projects, and accept/decline workers via `!WORK` commands
- **Auto-Versioning** — Git pre-commit hook auto-increments `AUTOVERSION.py` and prepends entry to `CHANGELOG.md` on every commit
- **Interchangeable AI Models** — Switch models mid-session with `!MODEL <name>`; list available models with `!MODELS`; model usage tracked across sessions
- **Pluggable LLM Backends** — Run on **Ollama** (default) or any **OpenAI-compatible server** like **vLLM**; switch with `-b vllm` at startup or `!BACKEND vllm` mid-session (see [Using vLLM instead of Ollama](#using-vllm-instead-of-ollama))
- **Interactive AI Chat** — Terminal-based interface for conversing with local LLMs via Ollama or vLLM (streaming response with thinking support)
- **XML Tool System** — AI invokes tools by writing XML blocks; tools are dynamically loaded Python classes with hot-reload; 25+ tools including file I/O, search, processing, terminal, tips, and tree view
- **Plan / Build Modes** — structured workflow: plan mode for architecting tasks, build mode for executing them
- **Plan Manager** — Create plans, split into tasks, track progress, auto-continue on restart (`-c` flag)
- **Secure Terminal Tool** — Allowlist-based command execution with audit logging and 30s timeout; also allows user-created scripts via `./` or `/` paths
- **Persistent Sessions** — Chat history saved per session in `history/`; session ID tracked in `sessid.aiia`
- **Image/Video Analysis** — `ReadImage` tool injects images into conversation for vision model analysis; `ImageTransform` handles local transformations (resize, crop, convert, flip, rotate); `GenerateImage` creates images from text using Ollama diffusion models (x/flux2-klein, x/z-image-turbo), a vLLM-Omni server, or local diffusers (see `AI_IMAGE_BACKEND`); `MediaAnalyst` persona pre-configured with vision model defaults and ffmpeg-based video frame extraction workflow
- **ReplaceLine Tool** — Targeted line edits without rewriting entire files; supports single line or range replacement; pairs with AppendFile for precise, surgical file modifications
- **Continue Support** — `-c` flag loads last session's `HISTORY.md` and `PLAN.md` from working directory, resumes chat and plan where you left off
- **Project History** — Each project directory gets a `HISTORY.md` with human-readable markdown + embedded JSON for machine parsing; fully round-trip compatible
- **Instruct Persona System** — Dynamic persona classes in `instruct/` (Developer, Friend, SysAdmin, Researcher, MediaAnalyst, DataCollector, Generalist, TechTalker, Scrapper); switch mid-session with `!INSTRUCT_SWITCH`; each persona specifies its own model, system prompt, and toolset
- **Token Tracking** — Per-turn and cumulative token counts displayed in `!STATS`
- **TreeView Tool** — ASCII directory tree visualization with depth control, glob filtering, and hidden-file toggling; cached for 5 minutes
- **Tips System** — Save, view, reinsert, and manage conversation snippets as JSON tips (`!TS`, `!TL`, `!TV`, `!TR`, `!TD`, `!TDR`, `!TDA`)
- **Auto Tip Summary** — Every user message gets an automatic summary of available tips injected before sending to the AI
- **Tool Result Caching** — Tools with `cache_ttl` class attribute (e.g., listTools=600s, TreeView=300s) cache results to files; `!CACHE_CLEAR` to flush all caches; global TTL in config
- **Terminal Improvements** — `rm`/`rmdir`/`ln`/`install` added to allowlist; `./` and `/` paths bypass allowlist for user scripts; argument-smash detection returns specific XML correction error
- **Orchestra System** — Multi-agent task distribution: one director process dispatches tasks to any number of worker processes over TCP; each worker has its own model, persona, and tools; planning can be delegated to a designated worker
- **Session Management** — `!CLEAR` to clear chat history (keep persona), `!RH <row>` or `!RH <from> <to>` to remove rows, `!SAVE_HISTORY [file]` to export history, `!NEW SESSION` for a full reset
- **Factory Reset** — `-R` flag resets all state (history, plans, session ID, tips, cookies) to factory defaults with confirmation prompt

---

## Table of Contents

- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Using vLLM instead of Ollama](#using-vllm-instead-of-ollama)
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
- [Ollama](https://ollama.com) server running (default: `localhost:11434`) — **or** a [vLLM](https://docs.vllm.ai) / OpenAI-compatible server (see [Using vLLM instead of Ollama](#using-vllm-instead-of-ollama))
- A model pulled (tested with `qwen3:latest`, `gemma3:12b`, `gemma4:26b`, `qwen3-coder:latest`, `nemotron-3-nano:latest` but best works with `kimi-k2.5:cloud` or `kimi-k2.7-code:cloud` )

### Installation

```bash
git clone <repo-url>
cd AIIA

git clone https://github.com/m5it/AIIA.git
cd AIIA
git clone https://github.com/m5it/koslenium_driver.git tools/koslenium_driver
git clone https://github.com/m5it/koslenium_www.git tools/koslenium_driver/www
./tools/koslenium_driver/build.sh

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-ollama.txt   # default backend (Ollama)
# or, for a vLLM / OpenAI-compatible server instead:
pip install -r requirements-vllm.txt
# optional GPU deps for image generation / MediaAnalyst persona:
pip install -r requirements-gpu.txt
# optional aiia_work marketplace client (python run.py --work):
pip install -r requirements-marketplace.txt
```

### Run (from any directory)

**Install globally (one-time):**
```bash
sudo ./install.sh -l    # Creates /usr/local/bin/aiia → start.sh
```

Now run `aiia` from **any** directory:
```bash
aiia                    # Start interactive session
aiia -m gemma3:12b      # Use specific model
aiia -b vllm -m Qwen/Qwen2.5-7B-Instruct  # Use vLLM backend instead of Ollama
aiia -c                 # Continue last session from HISTORY.md
aiia -R                 # Factory reset (clear all state)
aiia -Q -p Developer    # Quick mode (skip interactive prompts)
aiia -P "You are a coding assistant"  # Custom system message prefix
aiia -Y "List all Python files"  # Single request
aiia -d                 # Enable debug output
aiia -T 0.8             # Set temperature
aiia -S 0.0.0.0:9877    # Server mode (auto-quick)
aiia -h                 # Show help
```

**Uninstall:**
```bash
sudo ./install.sh -u    # Removes /usr/local/bin/aiia
```

**Without installing**, run directly:
```bash
source .venv/bin/activate
python run.py              # or ./start.sh
python run.py -m gemma3:12b -c
```

The `start.sh`/`aiia` script auto-detects the project root, sets `AIIA_PROJECT_DIR`, creates required directories, activates the venv, and passes all flags to `run.py`.

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
3. !START_BUILD                 → Switch to build mode and start executing tasks
4. AI executes tasks one by one → Uses <nextTask>completed</nextTask>
5. AI calls <jobDone/>          → When all tasks complete
```

See [Plan & Build System](#plan--build-system) for full details.

### Instruct Personas

Switch between specialized personas that define the AI's system prompt, toolset, and model:

```
1. !INSTRUCT_LIST                → See available personas
2. !INSTRUCT_SWITCH Researcher    → Switch to Researcher persona
3. !INSTRUCT_SWITCH MediaAnalyst  → Switch to image/video analysis persona
4. !MODEL qwen3-vl:latest         → Switch to a vision-capable model
```

Personas live in `instruct/` as Python classes. Each can specify a `model` attribute to override `AI_MODEL`:

```python
class Friend():
    name = "Friend"
    description = "Friendly chat companion — casual, warm, conversational"
    model = "llama3.2:3b"   # optional, overrides AI_MODEL when selected

class MediaAnalyst():
    name = "MediaAnalyst"
    description = "Visual media analyst — analyzes images/videos, extracts info, transforms media"
    model = "qwen3-vl:latest"  # vision model for image analysis
```

Use `-p` flag to set persona on startup:
```bash
python run.py -p Friend
python run.py -p Researcher -m gemma3:12b
python run.py -p MediaAnalyst   # image/video analysis with vision model
```

### Tips System

Save and replay useful conversation exchanges:

```
!TS setup_guide           → Save the last exchange as tip "setup_guide"
!TS 3 install_deps        → Save history row #3 as tip "install_deps"
!TL                        → List all tips
!TV setup_guide           → View saved tip entries
!TR setup_guide           → Reinsert saved messages into current chat
!TD setup_guide           → Delete tip
!TDA                       → Delete all tips
```

### Orchestra — Multi-Agent Task Distribution

Run a director that distributes plan tasks to worker agents over TCP:

```
Terminal 1 (Director):
  python run_orchestra.py --port 9876

Terminal 2 (Worker — planning):
  python run_worker.py --connect localhost:9876 --name big-worker -m gemma3:12b -p Developer

Terminal 3 (Worker — execution):
  python run_worker.py --connect localhost:9876 --name fast-worker -m nemotron-3-nano:latest -p Developer
```

**Workflow:**

```
1. !PLAN_WORKER big-worker     → Set big-worker as planner
2. "Build a CLI calculator"    → Director routes plan request to big-worker
   big-worker creates plan with tasks via its AI
   Plan data sent back, loaded into director
3. !MODE build                  → Switch to build mode
4. Tasks auto-dispatch to idle workers
   Each worker executes using its own model + tools
   Progress displayed in real-time
5. All tasks complete → back to normal prompt
```

**Worker flags:**

| Flag | Description |
|------|-------------|
| `--connect HOST:PORT` | Director address (required) |
| `--name NAME` | Worker name (default: hostname) |
| `-m MODEL` | Worker's model |
| `-p PERSONA` | Worker's persona |
| `-d` | Debug output |

**Director flags:**

| Flag | Description |
|------|-------------|
| `--port PORT` | Listen port (default: 9876) |
| `-m MODEL` | Director's own model (for local planning) |
| `-p PERSONA` | Director's own persona |

### aiia_work Marketplace Client

Separate, opt-in client for the aiia_work marketplace (`python run.py --work`). Isolated from the normal chat session — no XML/AI tools, only `!WORK` commands. Lives in the standalone `aiia_work/` package (no `src/` deps) plus the `run_work.py` entry point, wired into `run.py`'s subcommand routing.

```bash
pip install -r requirements-marketplace.txt
python run.py --work --base-url http://localhost:8006/rest/aiia_work   # local dev server
```

**API key resolution** (priority order): env `AIIA_WORK_API_KEY` > config `AIIA_WORK_API_KEY` > stored key file `~/.config/aiia/aiia_work.json` (created automatically after `!WORK KEYGEN`). `!WORK KEYGEN` needs an SSO bearer token (`--sso-token` / `AIIA_WORK_SSO_TOKEN`).

**`!WORK` commands:**

| Command | Description |
|---------|-------------|
| `HELP` | Show all marketplace commands |
| `KEYGEN [label] [role]` | Generate a new API key (role: `giver` \| `worker` \| `both`) |
| `KEYS` | List existing API keys |
| `KEYREVOKE <id>` | Revoke an API key |
| `CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]` | Create a project |
| `LIST` | List projects |
| `SHOW <id>` | Show a project's details and requests |
| `STATUS <id> <open\|in_progress\|completed\|closed>` | Change project status |
| `APPLY <project_id> <msg>` | Apply as a worker to a project |
| `MY` | List my requests |
| `ACCEPT <rid>` | Accept a worker request |
| `DECLINE <rid>` | Decline a worker request |
| `CMD <name> [json]` | Framework bridge (server-side commands) |
| `QUIT` | Exit the marketplace client |

**Config keys:** `AIIA_WORK_BASE_URL` (default `https://apis.aiia-frame.work/rest/aiia_work`), `AIIA_WORK_API_KEY`, `AIIA_WORK_SSO_TOKEN`, `AIIA_WORK_KEY_FILE`, `AIIA_WORK_ROLE`, `AIIA_WORK_TIMEOUT`, `AIIA_WORK_RETRIES`.

---

## Configuration

All configuration lives in `config.py`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `AI_MODEL` | str | `kimi-k2.5:cloud` | Model name (Ollama tag or vLLM/HF model id) |
| `AI_BACKEND` | str | `ollama` | LLM backend: `ollama` or `vllm` (OpenAI-compatible) |
| `VLLM_HOST` | str | `http://localhost:8000/v1` | vLLM OpenAI-compatible base URL |
| `VLLM_API_KEY` | str | (empty) | Optional API key for the vLLM server |
| `VLLM_TIMEOUT` | int | `120` | vLLM request timeout in seconds |
| `AI_IMAGE_BACKEND` | str | `auto` | Image generation backend: `auto` (follow `AI_BACKEND`), `ollama`, `vllm`, or `local` (diffusers) |
| `MODE` | str | `build` | Initial mode: `plan` or `build` |
| `CONTINUE` | bool | `false` | Resume last plan on start |
| `DEBUG` | bool | `false` | Enable verbose debug output |
| `QUIET` | bool | `false` | Suppress all non-essential output |
| `AI_TEMPERATURE` | float | `0.7` | Model temperature |
| `AI_MAX_CONTENT_LEN` | int | `20000` | Max chars per response |
| `AI_MAX_SESSION_LEN` | int | `200000` | Max total session context |
| `INSTRUCT_CLASS` | str | `Developer` | Default persona class |
| `INSTRUCT_PATH` | str | `instruct/` | Persona class directory |
| `AI_MODEL_TIMEOUT` | int | `120` | Seconds before model API call times out (`0` = no timeout) |
| `AI_MODEL_RETRIES` | int | `3` | Max retries on failed model calls before recommending switch |
| `BUILD_THINKING_DISABLED` | bool | `false` | Disable thinking in build mode |
| `AUTO_CONTINUE_TASKS` | bool | `true` | Auto-advance to next task in build mode after tool usage |
| `AUTO_CONTINUE_ALL_TASKS` | bool | `true` | Re-enter AI loop until all plan tasks are completed |
| `AUTO_CONTINUE_REMIND_AFTER` | int | `20` | Remind model to call `<nextTask>` after N tool iterations without one |
| `TOOL_TRAINING` | bool | `true` | On fresh sessions, let AI demonstrate tool usage once before user input |
| `PLAN_WORKER` | str/None | `None` | Worker name for delegated planning |
| `NUM_PROMPT_TOKENS` | int | `0` | Cumulative prompt tokens |
| `NUM_RESPONSE_TOKENS` | int | `0` | Cumulative response tokens |
| `NUM_LAST_PROMPT_TOKENS` | int | `0` | Last-turn prompt tokens |
| `NUM_LAST_RESPONSE_TOKENS` | int | `0` | Last-turn response tokens |
| `TIPS_PATH` | str | `~/.config/ourai/tips` | Tips storage directory (also used for tool cache) |
| `TOOL_CACHE_TTL` | int | `86400` | Default cache TTL in seconds (1 day) |
| `TOOL_CACHE_ENABLED` | bool | `true` | Enable/disable tool result caching globally |
| `REPLACELINE_ZERO_INDEXED` | bool | `false` | ReplaceLine uses 0-indexed lines when `true` (default: 1-indexed) |
| `COOKIE_FILE` | str/None | `None` | Shared cookie file for WWW tools |
| `WWW_SOURCE_MAX_SIZE` | int | `80000` | Max chars for `<source>true</source>` before saving to disk |
| `working_dir` | str | `$OURAI_PROJECT_DIR` | Project working directory |
| `plans_path` | str | `plans/` | Directory for JSON plan files |
| `history_path` | str | `history/` | Directory for session history |
| `tools_path` | str | `tools/` | Directory for tool modules |
| `SERVER_AUTH_ENABLED` | bool | `false` | Enable global Basic Auth for HTTP server |
| `SERVER_USERNAME` | str | `admin` | Global auth username (fallback) |
| `SERVER_PASSWORD` | str | `aiia` | Global auth password (fallback) |
| `AIIA_WORK_BASE_URL` | str | `https://apis.aiia-frame.work/rest/aiia_work` | aiia_work marketplace API base URL (local dev: `http://localhost:8006/rest/aiia_work`) |
| `AIIA_WORK_API_KEY` | str | (empty) | Marketplace API key (`X-Api-Key`). Priority: env > config > stored key file |
| `AIIA_WORK_SSO_TOKEN` | str | (empty) | SSO bearer token (required for `!WORK KEYGEN`) |
| `AIIA_WORK_KEY_FILE` | str/None | `None` | Stored API key file (default `~/.config/aiia/aiia_work.json`) |
| `AIIA_WORK_ROLE` | str | `both` | Default keygen role: `giver` \| `worker` \| `both` |
| `AIIA_WORK_TIMEOUT` | int | `30` | HTTP timeout (seconds) |
| `AIIA_WORK_RETRIES` | int | `2` | Retries on transient 500s / network errors |

### Per-Project Config (`aiia.json`)

Place an `aiia.json` file in the project directory (CWD when you run `aiia`) to override global defaults without editing `config.py`:

```json
{
  "AI_MODEL": "gemma3:12b",
  "AI_OPTIONS": {
    "temperature": 0.8,
    "num_ctx": 65536
  },
  "MODE": "build",
  "AI_MAX_ITERATIONS": 20
}
```

**Override priority** (highest to lowest): CLI flags > `aiia.json` > `config.py` defaults. Dict options (like `AI_OPTIONS`) are deep-merged — individual keys update rather than replacing the entire dict.

### Per-Project Authentication (Server Mode)

When running AIIA in HTTP server mode (`-S` flag), each project can have its own authentication credentials stored in `.aiia/auth.json`:

**Auth file location:** `<project_root>/.aiia/auth.json`

**File format:**
```json
{
  "enabled": true,
  "username": "project_user",
  "password": "secure_password"
}
```

**Client request headers:**
```http
Authorization: Basic base64(username:password)
X-Project-Path: /path/to/project
```

**How it works:**
1. Client sends `Authorization` header with Basic Auth credentials
2. Client sends `X-Project-Path` header identifying the project
3. Server loads `.aiia/auth.json` from the specified project path
4. Server validates credentials against project-specific username/password
5. If no auth file exists, falls back to global `SERVER_AUTH_*` settings from `config.py`

**To disable project auth:**
```json
{
  "enabled": false
}
```

**Security notes:**
- Auth file should have restricted permissions (`chmod 600 .aiia/auth.json`)
- Passwords are compared using constant-time comparison to prevent timing attacks
- Global fallback auth can be disabled by setting `SERVER_AUTH_ENABLED: false` in `config.py`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `localhost:11434` | Ollama server address |
| `AIIA_PROJECT_DIR` | project root | Used as `working_dir` for PLAN.md/HISTORY.md |
| `OURAI_PROJECT_DIR` | (deprecated) | Legacy fallback, same as `AIIA_PROJECT_DIR` |

---

## Using vLLM instead of Ollama

AIIA runs on **Ollama by default**, but every chat request goes through a pluggable backend layer (`src/LLMBackends/`), so you can point it at any **OpenAI-compatible server** — most notably [vLLM](https://docs.vllm.ai). Everything else (XML tools, plan/build modes, personas, history, streaming, thinking) works exactly the same.

### 1. Start a vLLM server

```bash
# Install vLLM in its own environment (needs a GPU for real use)
pip install vllm

# Serve a model on the OpenAI-compatible API (default port 8000)
vllm serve Qwen/Qwen2.5-7B-Instruct

# Or with options:
vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000 --api-key mysecret
```

Any other OpenAI-compatible server (llama.cpp server, LM Studio, TGI, SGLang, ...) works the same way — just point `VLLM_HOST` at it.

### 2. Point AIIA at the server

Three ways, pick one:

**a) CLI flag (per run):**
```bash
aiia -b vllm -m Qwen/Qwen2.5-7B-Instruct
```

**b) Mid-session command:**
```
!BACKEND vllm            → switch to vLLM (validates connectivity, lists models)
!MODELS                  → list models served by the active backend
!MODEL Qwen/Qwen2.5-7B-Instruct
!BACKEND ollama          → switch back anytime
```

**c) Config (persistent):** set in `config.py` or per-project `aiia.json`:
```json
{
  "AI_BACKEND": "vllm",
  "AI_MODEL": "Qwen/Qwen2.5-7B-Instruct",
  "VLLM_HOST": "http://localhost:8000/v1",
  "VLLM_API_KEY": "mysecret"
}
```

If the server runs on another machine, set `VLLM_HOST` accordingly, e.g. `http://192.168.0.170:8000/v1`.

### 3. Notes & differences vs Ollama

| Topic | Behavior on vLLM |
|-------|------------------|
| Model names | Use the name the server reports (usually the HF id, e.g. `Qwen/Qwen2.5-7B-Instruct`) — check with `!MODELS` |
| Streaming & thinking | Supported; reasoning models stream `reasoning_content` as thinking |
| Options mapping | `num_predict` → `max_tokens`; `top_k` sent via `extra_body`; `num_ctx` is ignored (vLLM manages context) |
| Vision models | Supported — images are converted to OpenAI `image_url` content automatically |
| `GenerateImage` tool | Backend-agnostic: uses Ollama, vLLM-Omni (`POST {VLLM_HOST}/images/generations`), or local diffusers — see `AI_IMAGE_BACKEND` (default `auto` follows `AI_BACKEND`) |
| `!MODEL` GPU freeing | `ollama stop` cleanup is skipped on vLLM (vLLM manages its own GPU memory) |
| Auth | Set `VLLM_API_KEY` if the server was started with `--api-key`; it is masked in `!STATS`/`!GET` output |
| Persistence | The active backend is saved to `state.aiia` and restored on `-c` continue |
| Dependencies | Uses the `openai` python package (in `requirements-vllm.txt`); the `ollama` package is not required for vLLM-only installs |

---

## Architecture

```
AIIA/
├── run.py                         # Thin entry — CLI parsing, factory reset, persona resolution
├── run_orchestra.py               # Orchestra director — multi-agent task dispatcher
├── run_worker.py                  # Orchestra worker — connects to director, executes tasks
├── run_work.py                    # aiia_work marketplace client (python run.py --work)
├── config.py                      # All configuration & system prompts
├── AUTOVERSION.py                 # Auto-incremented version (git pre-commit hook)
├── install.sh                     # Install script — sudo ./install.sh -l to install globally
├── start.sh                       # Startup script (auto-setup, path resolution)
├── exports.sh                     # Ollama env vars (OLLAMA_KEEP_ALIVE, OLLAMA_HOST)
├── requirements.txt               # Common core dependencies
├── requirements-ollama.txt        # Default backend (Ollama)
├── requirements-vllm.txt          # vLLM backend (OpenAI-compatible)
├── requirements-gpu.txt           # Optional GPU deps (torch, diffusers, etc.)
├── requirements-marketplace.txt   # Optional aiia_work marketplace client deps
├── AGENTS.md                      # Development notes & conventions
├── PLAN.md                        # Current/active plan (working dir only)
├── HISTORY.md                     # Session transcript (working dir only)
├── sessid.aiia                    # Session counter file
│
├── src/
│   ├── Handle.py                  # Core orchestrator — composes 5 mixins (Chat, Response, AI…)
│   ├── HandleChat.py              # Handle mixin — Chat() loop, AI() model calls
│   ├── HandleParse.py             # Handle mixin — XML tool extraction from responses
│   ├── HandleStream.py            # Handle mixin — streaming output handling
│   ├── HandleContext.py           # Handle mixin — context summarization
│   ├── HandleState.py             # Handle mixin — state persistence
│   ├── Commands.py                # !-prefixed terminal commands — composes 8 mixins
│   ├── CommandsConfig.py          # Commands mixin — !GET/!SET/!MODEL/!BACKEND…
│   ├── CommandsSession.py         # Commands mixin — session control
│   ├── CommandsPersona.py         # Commands mixin — persona switching
│   ├── CommandsTips.py            # Commands mixin — tip management
│   ├── CommandsTimers.py          # Commands mixin — timer loops
│   ├── CommandsSites.py           # Commands mixin — website JS support scripts
│   ├── CommandsPlan.py            # Commands mixin — plan/view commands
│   ├── CommandsWorkers.py         # Commands mixin — orchestra workers
│   ├── commands_registry.py       # Command registry builder
│   ├── ToolParser.py              # XML tool parser coordinator — composes 3 mixins
│   ├── ToolXmlParser.py           # ToolParser mixin — XML parsing
│   ├── ToolExecutor.py            # ToolParser mixin — tool execution, caching, guards
│   ├── PlanToolHandler.py         # ToolParser mixin — plan XML tool dispatch
│   ├── cli.py                     # CLI argument parsing
│   ├── FactoryReset.py            # Factory reset utility
│   ├── PersonaResolver.py         # Persona resolution
│   ├── PlanManager.py             # PlanBase, Plan, PlanTask, TaskLog classes
│   ├── PlanSaver.py               # PLAN.md / HISTORY.md persistence
│   ├── HistoryManager.py          # Session history load/save
│   ├── functions.py               # Custom module loader, utilities
│   ├── Prepare.py                 # Session init, mode instructions
│   ├── ToolChooser.py             # Tool management & selection
│   ├── Log.py                     # Terminal output logging
│   ├── Speak.py                   # Text-to-speech (experimental)
│   ├── InstructManager.py         # Persona discovery and selection
│   ├── ImageGenBackends.py        # Image generation backends (ollama/vllm/diffusers)
│   ├── LLMBackends/               # Pluggable LLM backends (BaseBackend, OllamaBackend, VLLMBackend)
│   ├── MediaHelper.py             # Image/video encode/decode/info utilities
│   ├── ModelRegistry.py           # Per-model capability database (context size, vision, think)
│   ├── TipManager.py              # Conversation tip save/replay
│   ├── TimerManager.py            # Timer loop scheduling
│   ├── EventBus.py                # Event publish/subscribe
│   ├── PathApprover.py            # Path approval/sandbox checks
│   ├── DependencyChecker.py       # Per-persona dependency checking
│   ├── DependencyInstaller.py     # Per-persona dependency installer (isolated venvs)
│   ├── Server.py                  # HTTP server
│   ├── ServerFactory.py           # Server profile resolution
│   ├── Client.py                  # Client connection handling
│   ├── OrchestraDirector.py       # Orchestra TCP server, worker registry, task dispatch
│   └── OrchestraWorker.py         # Orchestra TCP client, headless task execution
│
├── instruct/                     # Persona classes (plan/build system prompts)
│   ├── Developer.py              # Software development persona
│   ├── DeveloperV2.py            # Developer variant (explicit STOP, clearer mode transitions)
│   ├── DeveloperV3.py            # DeveloperV2 + framework-awareness
│   ├── Friend.py                 # Casual chat persona
│   ├── MediaAnalyst.py           # Image/video analysis persona (vision model)
│   ├── SysAdmin.py               # System administration persona
│   ├── Researcher.py             # Web research and data extraction persona
│   ├── DataCollector.py          # Data collection/testing persona
│   ├── Generalist.py             # General-purpose assistant
│   ├── TechTalker.py             # Technical casual chat persona
│   ├── Scrapper.py               # Web scraping persona
│   ├── BookSmith.py              # Literary assistant (book analysis & writing)
│   ├── BookSmithV2.py            # BookSmith variant (analysis/writing split)
│   ├── BookSmithV3.py            # BookSmithV2 + long-context handling
│   ├── BookSmithAnalyst.py       # Literary/critical analysis specialist
│   ├── BookSmithNovelist.py      # Fiction writing specialist
│   ├── BookSmithPoet.py          # Poetry specialist
│   ├── BookSmithEditor.py        # Editing & revision specialist
│   └── __init__.py
│
├── tools/                        # XML-invokable tool modules (33 tools)
│   ├── _koslenium_server.py      # Local HTML-rendering proxy for WWW/WWWExec
│   ├── _site_script_resolver.py  # Per-website JS support script resolver
│   ├── koslenium_driver/         # Java web client (build.sh, www jar)
│   ├── tool_Terminal.py          # Secure terminal execution (ollama allowed)
│   ├── tool_ReadFile.py          # Read file content
│   ├── tool_WriteFile.py         # Write/overwrite files
│   ├── tool_AppendFile.py        # Append or insert at line
│   ├── tool_CreateFile.py        # Create file (fails if exists)
│   ├── tool_ReplaceLine.py       # Replace specific line(s) in a file
│   ├── tool_ReadImage.py         # Read image, inject into conversation
│   ├── tool_ImageTransform.py    # Transform images (resize, crop, convert...)
│   ├── tool_GenerateImage.py     # Generate images via diffusion models
│   ├── tool_ReadPDF.py           # Extract text/metadata from PDFs
│   ├── tool_TreeView.py          # ASCII tree view of directory structure
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
│   ├── tool_CurrentTime.py       # Get current date/time
│   ├── tool_WWW.py               # Web fetcher (JS/no-JS, browser, cookies, screenshots)
│   ├── tool_WWWExec.py           # Execute JS on the loaded page
│   ├── tool_WWWJS.py             # WWW alias with JS rendering
│   ├── tool_ParsePage.py         # Parse cached HTML locally with BeautifulSoup
│   ├── tool_SiteScript.py        # Discover/execute per-site JS support scripts
│   ├── tool_UpdateSiteScript.py  # Create/update per-site JS support scripts
│   ├── tool_SaveTip.py           # Save conversation tip
│   ├── tool_GetTip.py            # Retrieve saved tip
│   ├── tool_ListTips.py          # List all saved tips
│   ├── tool_DeleteTip.py         # Delete a tip
│   └── tool_ReinsertTip.py       # Reinsert tip into chat
│
├── aiia_work/                     # Standalone aiia_work marketplace client (no src/ deps)
│   ├── client.py                  # WorkClient — HTTP client for the marketplace API
│   └── console.py                 # WorkConsole — interactive !WORK command loop
│
├── wwwurljssupport/              # Per-website JS support scripts
│
├── history/                      # Session chat history (gitignored)
├── plans/                        # JSON plan files (gitignored)
├── workout/                      # Tool output directory (gitignored)
│
├── tests/                        # pytest suite (pytest -q)
│   ├── test_core_modules.py      # Module import/smoke + helper unit tests
│   ├── test_config.py
│   ├── test_functions.py
│   ├── test_backends.py
│   ├── test_generateimage.py
│   ├── test_all_tools.sh
│   ├── test_terminal.sh
│   └── old_*.py                  # Legacy standalone scripts (not collected)
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
| **InstructManager** | `src/InstructManager.py` | Persona discovery, interactive chooser, persona model override |
| **TipManager** | `src/TipManager.py` | Save/view/reinsert/delete conversation tips as JSON files |
| **OrchestraDirector** | `src/OrchestraDirector.py` | TCP server thread, worker registry, task dispatch, plan routing |
| **OrchestraWorker** | `src/OrchestraWorker.py` | TCP client, register with director, headless task execution via Handle.AI() |

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
| **planDone** | `<planDone/>` | Mark plan as complete (replaces `!MODE build`) |

#### XML Tools (Build Mode)

| Tool | XML | Description |
|------|-----|-------------|
| **nextTask** | `<nextTask>completed</nextTask>` or `<nextTask>blocked</nextTask>` | Mark current task and get next one |
| **LogProgress** | `<LogProgress><taskId>...</taskId><whatWasDone>...</whatWasDone></LogProgress>` | Log progress on current task |
| **jobDone** | `<jobDone/>` | Finish the plan (all tasks done) |
| **startBuild** | `<startBuild/>` or `<startBuild><planId>...</planId></startBuild>` | Start build mode with optional plan ID (in PLAN mode shows 1-4 menu) |

Build mode also includes all plan management tools (createTask, viewTask, planDone, etc.).

### Plan Flow

```
         !MODE plan  or  <planDone/>
              │
              ▼
    ┌─────────────────┐
    │  createPlan     │  AI creates plan
    │  createTask x N │  AI adds tasks
    │  planDone       │  Signals planning complete
    └────────┬────────┘
             │
             ▼
    !MODE build  or  <startBuild/>
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

The AI invokes tools by writing XML blocks in its response. All tools are auto-discovered and loaded on first use.

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
<contentOfFile>File content here
