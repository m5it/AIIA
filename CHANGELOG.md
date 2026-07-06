# Changelog

## 2026-07-06

### Fixed: Token counts reset to zero on `-c` continue

Token counts (`NUM_PROMPT_TOKENS`, `NUM_RESPONSE_TOKENS`, `NUM_LAST_*`) were never persisted to disk. On `-c` continue, a fresh process loaded history messages but had no way to recover the accumulated counts, so `!STATS` always showed zero.

**Two mechanisms added:**

1. **Per-message persistence** — Each assistant message now stores its `prompt_tokens` and `response_tokens` in the message dict before it's written to history. On continue, the recalculation loop sums up per-message values from all loaded assistant messages. This is the primary recovery path for sessions started after this change.

2. **`tokens.aiia` file** — Cumulative token counts are saved to `tokens.aiia` after every assistant response. On continue, if the per-message scan finds no data (old history files predating this change), it falls back to loading from `tokens.aiia`. This ensures existing sessions also get correct counts after their first continue restart.

**Files:** `config.py`, `src/Handle.py`, `.gitignore`, `CHANGELOG.md`

### Added: Image/vision support — ReadImage, ImageTransform, MediaAnalyst persona

New image analysis pipeline:
- **ReadImage tool** (`tools/tool_ReadImage.py`) — Reads an image file, provides metadata (dimensions, format, size), encodes to base64, and injects it into the conversation for vision models to analyze. The AI sees the image content in subsequent responses.
- **ImageTransform tool** (`tools/tool_ImageTransform.py`) — Local image transformations without AI: resize, crop, convert format, rotate, flip. Operates on `workin/` files, saves to `workout/`.
- **MediaHelper** (`src/MediaHelper.py`) — Shared utility: encode/decode images to/from base64, resize with aspect ratio preservation, get image metadata.
- **MediaAnalyst persona** (`instruct/MediaAnalyst.py`) — New instruction class specialized for visual media analysis. Default model: `qwen3-vl:latest`. Includes detailed instructions for ReadImage, ImageTransform, and ffmpeg-based video frame extraction.
- **Vision config** — `AI_VISION_ENABLED`, `AI_MAX_IMAGE_SIZE` (10MB), `AI_VISION_NOTE` in `config.py`
- **Handle.Response()** — Now accepts `images` parameter to attach base64-encoded images to user messages
- **Binary I/O** — `fread_binary()` / `fwrite_binary()` in `src/functions.py` for raw file reads
- **Dependencies** — `Pillow>=10.0.0` added to `requirements.txt`
- **Persona update** — `Developer.py` tool list updated with ReadImage and ImageTransform

**Files:** `config.py`, `src/Handle.py`, `src/functions.py`, `src/MediaHelper.py`, `tools/tool_ReadImage.py`, `tools/tool_ImageTransform.py`, `instruct/MediaAnalyst.py`, `instruct/Developer.py`, `requirements.txt`, `CHANGELOG.md`, `README.md`

### Added: `!MODELS` and `!MODEL` commands + used-models tracking

Two new session commands:
- **`!MODELS`** — Lists all available Ollama models with previously used ones starred at the top
- **`!MODEL <model_name>`** — Switch the active AI model mid-session (no restart needed). Shows current model if no argument.

Model usage is persisted to `used_models.aiia` (alongside `mode.aiia` and `sessid.aiia`). The current model is tracked automatically at startup; `!MODEL` switches append to the list. `!MODELS` displays starred used models at top, then all available models below.

**Files:** `config.py`, `src/Handle.py`, `src/Commands.py`, `CHANGELOG.md`, `README.md`

### Added: Early stream abort for PLAN-mode blocked tools

`Stream()` now checks each token as it arrives and aborts immediately if the model starts writing a blocked tool (`WriteFile`, `CreateFile`, etc.) while in PLAN mode — no need to wait for the full XML to parse. The partial content is still recorded in history so the model sees what it started writing.

This saves tokens and response time: instead of streaming the entire misguided invocation, the stream cuts off on the opening tag, and the model retries on the next iteration.

**Files:** `src/Handle.py`

### Simplified: Auto-continue guard

Removed the `LogProgress` requirement from the auto-continue guard. The condition is now simpler: auto-advance fires when the model made tool calls AND the last tool call did not return an error. The error guard (A1) is preserved so failed tool attempts don't skip tasks.

**Files:** `src/Handle.py`

## 2026-07-05

### Fixed: Auto-continue advancing tasks on tool errors

The auto-continue feature (`AUTO_CONTINUE_TASKS`) was advancing to the next task when the model's last tool call was an error. This caused tasks to be skipped without being completed — the model would create a file, then fail 3× on testing, and auto-continue would mark the task done and move on.

**Changes in `src/Handle.py` (`AI()` method):**

Added two guards before auto-continue fires:
- **A1 — Last tool error check:** If the last tool call in the current turn returned an error, auto-continue is blocked. The model retries in the next turn instead of advancing to a new task.
- **A2 — LogProgress requirement:** Auto-continue only fires when the model explicitly called `<LogProgress>` in the current AI turn. This ensures the model signals meaningful progress before the system advances to the next task. The LogProgress flag, once set, persists across iterations within the same AI turn, so the model can LogProgress in one iteration and do more tool work in the next.

Tracking variables (`_tools_last_error`, `_tools_log_progress`) are reset on each AI() call and after a successful auto-continue.

### Fixed: Error recovery guidance in persona instructions

Added to `instruct/DataCollector.py` and `instruct/Developer.py` (TOOL USAGE RULES):

> "If a tool returns an error with a 'Usage:' example, the error message shows the correct parameter names. Copy them exactly — don't guess."

This addresses the pattern where the model repeatedly tried wrong parameter names (`<content>` instead of `<contentOfFile>`) even after seeing the correct usage in the error message.

### Added: Persist MODE across sessions (`mode.aiia`)

The current mode (plan/build) is now saved to `mode.aiia` on every `!MODE` switch and on clean exit. When continuing with `-c`, the saved mode is restored — no need to re-`!MODE build` after restart.

**Save triggers:**
- `!MODE plan|build` command — writes immediately
- `cleanup()` on program exit — safety net for any mode switch not caught above

**Restore:** `_load_continue_session()` reads `mode.aiia` and sets `Options['MODE']` before the mode-mismatch check, so persona instructions are selected correctly.

**Factory reset:** `reset_to_factory()` writes `plan` to `mode.aiia`.

**Files:** `config.py`, `src/Handle.py`, `src/Commands.py`, `run.py`, `.gitignore`

### Added: Path sandbox guard — restrict file access to approved directories

### Added: PLAN-mode tool guard — block write/execute tools

New safety mechanism prevents the model from executing write/execute tools (`WriteFile`, `CreateFile`, `AppendFile`, `ReplaceLine`, `Sed`, `Sort`, `Terminal`, `ExecuteScript`, `WWW`, `WWWExec`, `WWWJS`) while in PLAN mode. If the model attempts any of these, an error is returned telling the user to switch to BUILD mode with `!MODE build`.

**Plan-mode allowed tools:**
- Plan management: `createPlan`, `createTask`, `updateTask`, `deleteTask`, `viewTask`, `listTasks`, `deletePlan`, `deleteDraft`, `deleteAllPlans`, `planDone`, `nextTask`, `jobDone`, `startBuild`, `LogProgress`
- Read-only tools: `ReadFile`, `TreeView`, `List`, `Find`, `Head`, `Tail`, `Grep`, `Diff`
- Info: `listTools`
- Tips: `SaveTip`, `GetTip`, `ListTips`, `DeleteTip`, `ReinsertTip`

The guard is positioned after the file size and path sandbox checks, before the routing to `HandlePlanTool`/`ExecuteTextTool`. Tools not in the blocked set pass through to normal execution.

**Files:** `src/ToolParser.py`, `instruct/Developer.py`

New security mechanism prevents the model from accessing files outside the working directory. A `PathApprover` class (`src/PathApprover.py`) manages per-project approvals, loaded from and saved to `PROJECT.md` in the working directory.

**How it works:**
- On startup, `Handle.py` creates a `PathApprover` with `working_dir` from config.
- If no `PROJECT.md` exists, defaults to approving `.` (the entire working directory).
- Before any file tool executes, `ToolParser.FireToolInvocation()` checks all path parameters against approved directories/files.
- If a path is not approved, the tool returns an error with instructions to use `!PROJECT ADD DIR/FILE`.

**15 guarded tools:** ReadFile, WriteFile, CreateFile, AppendFile, ReplaceLine, Grep, Sed, Head, Tail, Sort, Diff, TreeView, List, Find, ExecuteScript

**`!PROJECT` command (`src/Commands.py`):**
- `!PROJECT` — show current approvals
- `!PROJECT ADD DIR <path>` — approve a directory
- `!PROJECT ADD FILE <path>` — approve a specific file
- `!PROJECT DENY <path>` — block a previously allowed path
- `!PROJECT REMOVE DIR|FILE <path>` — remove an approval
- `!PROJECT RESET` — reset to defaults (only working directory)

**Files:** `config.py`, `src/PathApprover.py`, `src/Handle.py`, `src/ToolParser.py`, `src/Commands.py`

## 2026-07-04

### Fixed: `<think>` tag leaking into tool parser

The model sometimes outputs `<think>...</think>` in its `content` field (separate from the native thinking API). The tool parser was detecting `<think>` as a tool name and failing with "Tool `think` not found", polluting the conversation history and confusing the model.

**Files:** `src/Handle.py`, `src/ToolParser.py`
- Strip `<think>...</think>` and orphan `</think>` from model response content before tool parsing, repetition hash check, and history storage.

### Added: Automatic context window management

Long-running sessions accumulated 2.5M+ tokens, exceeding the model's 262K context window. Two new config options and four new methods handle this automatically at the start of each `AI()` call.

**Config options** (`config.py`):
- `AI_CONTEXT_LIMIT` (default: 262144) — model's max context window in tokens
- `AI_CLEAR_THRESHOLD` (default: 0.8) — fraction of limit that triggers management

**Flow** (`src/Handle.py`):
1. Estimate total token count (`chars / 4` + per-message overhead)
2. If over threshold → **summarize**: keep system prompts + last 5 exchanges, feed the rest to the model for a concise summary, insert as `[Context summary: ...]` system message
3. If still over (or summarization fails) → **auto-clear**: keep only system messages, drop everything else, reset counters

### Added: History archiving for training data

Before any destructive history operation (summarize, clear, !CLEAR), the raw `.dbk` file is archived as `{sid}.{suffix}.{timestamp}.dbk` in the `history/` directory. Archives are discoverable by `HistoryManager` for manual reload.

**Archive suffixes:**
- `cleared` — on `!CLEAR` command or auto-clear (context limit)
- `summarized` — on auto-summarization

**Also:** A tip `session_{sid}_cleared` is saved on clear operations, recording the archive filename and message count for model retrieval via `<GetTip>`.

**Files:** `src/Handle.py`, `src/Commands.py`

### Added: Expanded ReplaceLine examples in Developer persona (and all file-editing personas)

Added concrete single-line and multi-line ReplaceLine examples to all personas that edit files: `instruct/Developer.py`, `instruct/SysAdmin.py`, `instruct/Researcher.py`, and `instruct/DataCollector.py`. The updated instructions explicitly show the most common model mistake (`<content>` vs `<replacement>`) and warn that multi-line replacements shift later line numbers.

### Rewritten: DataCollector persona — `plan()` and `build()` overhaul

**`plan()`**: Removed hardcoded `<createTask>` XML (12 identical categories every session). Now describes categories as guidance — the model creates tasks dynamically with its own titles/instructions. Added `<planDone/>` instruction so model signals when planning is complete.

**`build()`**: 
- Removed confusing PLAN WORKFLOW section (told model to `createPlan`/`createTask` in BUILD mode, where plan already exists).
- Added **AUTO-CONTINUE** section explaining the system auto-advances after tool-based work — model doesn't need `<nextTask>` unless blocked.
- Added **SAFETY** section with 2MB file size limit and AppendFile+ReadFile corruption warning (46GB and 7.3GB historical incidents).
- Truncated redundant category descriptions (kept concise bullet lists).
- Kept full tool reference with correct parameter names, ReplaceLine critical notes/examples, PLAN MANAGEMENT TOOLS, and TOOL USAGE RULES.

**Files:** `instruct/DataCollector.py`

### Added: Auto-continue tasks in BUILD mode

When in BUILD mode with a task plan, the system now automatically advances to the next task after the model completes tool-based work — no need to explicitly call `<nextTask>`. Triggered only when tool calls were made during the current AI turn (option 2).

**Config:** `AUTO_CONTINUE_TASKS: True` in `config.py`

**Mechanism:** A new `_try_auto_continue()` method in `src/Handle.py` checks at the end of each `AI()` turn for pending plan tasks. If found, it calls `PlanBase.draft.nextTask()`, injects a user message `"continue task X / N...\n\nYour task:\n<instruction>"`, and loops the AI. The existing explicit `<nextTask>` tool path is unaffected.

**Files:** `config.py`, `src/Handle.py`

### Added: File size guard for write tools

New safety mechanism prevents the model from creating or modifying files larger than `AI_MAX_FILE_SIZE` (default 2,097,152 bytes). Guards are checked in `ToolParser.FireToolInvocation()` before any tool executes — works for both XML and native Ollama tool calls.

**Guarded tools and their content parameters:**
- `WriteFile` — checks `contentOfFile`
- `CreateFile` — checks `contentOfFile`
- `AppendFile` — checks `contentOfFile` plus existing file size (cumulative)
- `ReplaceLine` — checks `replacement`

When a write tool exceeds the limit, it returns an error message (not executed), the error is appended to history as a tool result, and the model can correct itself on the next iteration.

**Config:** `AI_MAX_FILE_SIZE: 2097152` in `config.py`

**Files:** `config.py`, `src/ToolParser.py`
