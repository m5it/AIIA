# Changelog

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
