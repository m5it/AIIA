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

### Updated: DataCollector persona plan workflow

Added a structured `PLAN WORKFLOW` section to `instruct/DataCollector.py` so the model knows to create a plan and tasks before starting the data collection workout. Also added a full `PLAN MANAGEMENT TOOLS` reference (createPlan, createTask, planDone, nextTask, LogProgress, jobDone, etc.) to both `plan()` and `build()` methods, and removed the per-turn `workout/dataset_log.jsonl` logging rule that caused runaway file growth.

**Files:** `instruct/DataCollector.py`

### Added: Auto-continue tasks in BUILD mode

When in BUILD mode with a task plan, the system now automatically advances to the next task after the model completes tool-based work — no need to explicitly call `<nextTask>`. Triggered only when tool calls were made during the current AI turn (option 2).

**Config:** `AUTO_CONTINUE_TASKS: True` in `config.py`

**Mechanism:** A new `_try_auto_continue()` method in `src/Handle.py` checks at the end of each `AI()` turn for pending plan tasks. If found, it calls `PlanBase.draft.nextTask()`, injects a user message `"continue task X / N...\n\nYour task:\n<instruction>"`, and loops the AI. The existing explicit `<nextTask>` tool path is unaffected.

**Files:** `config.py`, `src/Handle.py`
