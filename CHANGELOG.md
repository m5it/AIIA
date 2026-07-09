# Changelog

## 2026-07-09 — v0.7

### Added: Model call timeout + auto-retry with switch recommendation

Cloud model calls (`ollama.chat()`) could hang indefinitely with no timeout. The `aiia.json` system now:

**`config.py`** — Two new options:
- `AI_MODEL_TIMEOUT: 120` — httpx timeout (connect + read) in seconds; catches both hanging connections and stalled streams
- `AI_MODEL_RETRIES: 3` — retries before injecting a model-switch recommendation

**`src/Handle.py`** — Uses `ollama.Client(timeout=...)` instead of the top-level `chat()` function. The `chat()` + `Parse()` call is wrapped in a retry loop:
- **Transient failure** → retries up to `AI_MODEL_RETRIES` times (logged to `background.log`, echoed to user, 1s gap between attempts)
- **Persistent failure** → after exhausting retries, injects a recovery message into history: *"Switch to a local model with `!MODEL gemma3:12b`"*
- **Context too large** (400/413) → auto-clears and retries immediately (existing behavior preserved)

### Added: Per-project config overrides (`aiia.json`)

Place an `aiia.json` file in your project directory to override global `config.py` defaults:

```json
{
  "AI_MODEL": "gemma3:12b",
  "AI_OPTIONS": { "temperature": 0.8, "num_ctx": 65536 },
  "MODE": "build",
  "AI_MAX_ITERATIONS": 20,
  "AI_THINK": false
}
```

- Loaded early in `run.py` before CLI parsing, so CLI flags (`-m`, `-p`, `-T`) always take highest priority
- Dict-typed options (e.g. `AI_OPTIONS`) are deep-merged — individual keys update rather than replacing
- Only activates when CWD differs from the framework directory (i.e., when you `cd` into a project)
- Documented in `AGENTS.md` as "Per-Project Config (`aiia.json`)"

**Files:** `run.py`, `AGENTS.md`

## 2026-07-07 — v0.7

### Added: `!SUMMARIZE` command — manual history trim

Clears all non-system messages from chat history. Use when context gets too large (e.g., after GenerateImage injects base64 images). Calls `_auto_clear()` internally.

### Fixed: HTTP 413 loop on large context

Added `_manage_context()` call inside the AI() iteration loop (previously only called once before the loop). When GenerateImage injects a large base64 image as a tool result mid-loop, the re-check now catches the bloat before the next model request, preventing the "request body too large" loop.

### Added: `AI_INSTRUCT_OPTION=2` — short prompt + tips instruction mode

**New config:** `AI_INSTRUCT_OPTION` (default `1`):
- **`1`** (default) — current behavior: full persona class instructions (`plan()`/`build()` text) used as the system prompt
- **`2`** — short system prompt that tells the AI to retrieve its instructions from tips. The persona's full `plan()` and `build()` content is saved as a tip (`instruct_{persona}`) at startup. The AI must use `<GetTip>` or `<ReinsertTip>` to load detailed guidance.

**Why:** Saves ~2K-8K chars per request from the system prompt. Full instructions are available on-demand via tips.

### Removed: `!CT` and `!TOOLS` commands — tools now auto-load dynamically

**Problem:** Both commands were legacy from the pre-auto-load era.
- `!CT` (Clear Tools) cleared tool state that tools themselves never touch
- `!TOOLS` (List/Choose Tools) just printed "Loading tools..." and continued

**Fix:** Removed both command entries and their method implementations from `Commands.py`. Removed from README command table. Tools are auto-discovered and loaded on-demand by `ToolChooser`/`ToolParser` — no manual management needed.

### Fixed: Ollama image-gen intercept in Terminal

When the AI tries `ollama run|generate|push` with image model names (`x/`, `flux`, `sdxl`, etc.), Terminal now returns a message redirecting to the `GenerateImage` tool instead of failing on GPU memory.

### Fixed: HTTP 413 "request body too large" auto-recovery

The `chat()` call in `Handle.py` now detects 400/413/too-large errors from Ollama, auto-clears conversation context, and retries — instead of getting stuck in a permanent error loop.

### Fixed: Image output path now cwd-relative

`GenerateImage` was resolving `workout/` via `handle.Options.get('path')` (project root). Changed to always use cwd-relative `workout/` — images land where you launched `ourai` from.

### Added: `nvidia-smi` to Terminal allowed programs

AI can now diagnose GPU memory usage directly.

### Added: Tip `image_gen_workflow` — steer AI toward GenerateImage tool

New tip tells the AI to always use `GenerateImage` instead of calling ollama directly for image generation.

## 2026-07-07

### Added: `-c` persona persist — resume with last-used persona, not just Developer

**Problem:** `cleanup()` saved MODE (`mode.aiia`) but not the persona (`INSTRUCT_CLASS`). On restart with `-c`, persona always reverted to `Developer` from config, ignoring what was used in the last session.

**Fix:** Three changes:
1. `config.py` — Added `AI_FILE_PERSONA` config key pointing to `persona.aiia`
2. `run.py:cleanup()` — Now saves `INSTRUCT_CLASS` to `persona.aiia` alongside `mode.aiia`
3. `Handle.py:_load_continue_session()` — Reads `persona.aiia`, sets `INSTRUCT_CLASS` and `INSTRUCT_CLASS_OVERRIDE = True`, so `Choose()` auto-applies the restored persona

**Result:** `-c` now fully restores both mode AND persona. Running `-p MediaAnalyst`, closing, then `-c` resumes with MediaAnalyst persona.

### Added: HuggingFace diffusers fallback — Linux-compatible image generation

**Problem:** `GenerateImage` used `ollama.Client().generate()` which is macOS-only for diffusion models. On Linux it failed.

**Fix:** Refactored `tool_GenerateImage.py` into three layers:
1. `_generate_ollama()` — original Ollama backend (tried first)
2. `_generate_diffusers()` — new HuggingFace diffusers fallback (on Ollama failure)
3. `_save_and_inject()` — shared save/inject logic, reused by both backends

**Model mapping:** `x/flux2-klein` → `black-forest-labs/FLUX.1-schnell`, `x/z-image-turbo` → `stabilityai/sdxl-turbo`. Unknown models tried as-is with HF `DiffusionPipeline.from_pretrained()`.

**Pipeline cache:** Module-level `_diffusers_pipeline` / `_diffusers_pipeline_model` cache survives dynamic reloads — second generation with same model is instant.

**Dependencies:** Optional — added commented-out entries in `requirements.txt`. Install with: `pip install diffusers torch transformers accelerate`

**Caveat:** Python 3.14 may lack PyTorch wheels. Use CPU-only torch or wait for official builds.

### Added: Image generation — `GenerateImage` tool + `ModelRegistry` auto-config

**New tool: `tools/tool_GenerateImage.py`** — Generates images using Ollama diffusion models (`x/flux2-klein`, `x/z-image-turbo`). Calls `Client.generate()` with `width`, `height`, `steps`, `seed` params. Saves to `workout/` and auto-injects the result into the conversation so the AI can see what it generated.

**Model resolution chain:** `param > AI_IMAGE_GEN_MODEL config > current AI_MODEL > x/flux2-klein`. If no model is specified, the tool tries the current chat model first — cloud models like `kimi-k2.7-code:cloud` are used automatically.

**Auto GPU memory management:** Before `client.generate()`, the tool runs `ollama ps` and stops any loaded model that differs from the gen target. On `!MODEL` switches, the same logic frees GPU memory.

**`src/ModelRegistry.py`** — Added `x/flux2-klein:*` and `x/z-image-turbo:*` entries with `context_size=0` (non-chat model flag). The `apply()` function now skips context/think/vision changes for image gen models. Image gen models added to Terminal's allowed programs.

**`config.py`** — Added `AI_IMAGE_GEN_MODEL: "x/flux2-klein"` default.

**`instruct/MediaAnalyst.py`** — Full GenerateImage documentation in both plan() and build() methods: parameters, example XML, fallback chain notes, pull instructions.

**Files:** `tools/tool_GenerateImage.py`, `src/ModelRegistry.py`, `src/Commands.py`, `config.py`, `instruct/MediaAnalyst.py`, `tools/tool_Terminal.py`, `CHANGELOG.md`, `README.md`

### Fixed: MediaAnalyst persona — retired model and wasted Terminal iterations

**Model fix:** `qwen3-vl:235b-cloud` was retired 2026-06-16 (HTTP 410). Changed to `qwen3-vl:latest` which is available locally.

**Instruction fix:** The AI was wasting 6+ iterations on `find`/`ls` Terminal loops instead of using `TreeView` for file discovery:
- Added **CRITICAL FIRST STEP** header: "Use `<TreeView>` first, NEVER use Terminal for file discovery"
- Added **MANDATORY WORKFLOW** section with numbered steps (TreeView → ReadImage → analyze → save)
- Moved image discovery instructions to the very top of the build prompt

**Files:** `instruct/MediaAnalyst.py`

### Fixed: Terminal tool working directory mismatch

Terminal commands ran from the Python process CWD, which drifted after session changes (`!NEW SESSION`, mode switches). The AI would `cd` to a directory but Terminal's `subprocess.run(cwd=".")` ignored it.

Fix: Terminal now detects `working_dir` from `ToolParser._current_handle.Options` and uses it as the subprocess CWD. Every command output now includes `(cwd: /path)` so the AI always knows where it's running.

**Files:** `tools/tool_Terminal.py`

### Fixed: Editor LogController missing type prefixes

Added `"token"` (empty prefix for clean streamed text display) and `"done"` (`[DONE]`) cases to LogController's prefix switch. Token events no longer show a `[LOG]` prefix.

**Files:** `../OurAIEditor/src/main/java/com/ourai/editor/LogController.java`

### Added: Direct user tool calls skip AI entirely

When a user (or editor) sends an XML tool invocation like `<TreeView><path>.</path></TreeView>`, the framework now executes it immediately and returns the result without ever calling the LLM. Previously, the tool was executed in `You()` but then `AI()` would still run, wasting tokens as the model reacted to the tool result in history.

**`Handle.You()`** — returns `1` instead of `0` when tool invocations are detected in user input:
- Executes tools via `FireToolInvocation()` as before
- Collects results into `_direct_tool_results` list for SSE/callers
- Returns `1` to signal "tool was executed — skip AI"
- Still adds both user message and tool result to conversation history for context

**`Handle.Chat()`** — handles `x==1` with `continue` (skip `AI()`, show prompt again)

**`Server.chat()`** — handles `result==1` by calling `_stream_tool_results()`:
- Converts stored results to proper SSE events by tool type:
  - `TreeView` → `{"type":"tool","tool":"TreeView","params":{"xml":"..."}}`
  - `ReadFile` → `{"type":"tool","tool":"ReadFile","params":{"contentOfFile":"..."}}`
  - Other → `{"type":"tool","tool":"...","params":{"result":"..."}}`
- Clears `_direct_tool_results` after streaming

Result: instant tool responses in both CLI and SSE modes, zero tokens wasted.

**Files:** `src/Handle.py`, `src/Server.py`

### Added: `POST /execute` endpoint for direct tool execution

New server endpoint `/execute` that runs tools directly without involving the AI model. Accepts XML tool calls and returns JSON results immediately.

- **`POST /execute`** — Accepts `{"tool": "<ToolName>...</ToolName>"}`, parses XML, executes via `ExecuteTextTool()`, returns `{"success": true, "tool": "ToolName", "result": "..."}`
- No chat history modification, no LLM roundtrip — instant tool results
- Designed for editor/IDE integrations that need fast file operations

**Files:** `src/Server.py`

### Added: XML format option to TreeView tool

`TreeView` now accepts an optional `format` parameter (`"ascii"` or `"xml"`). XML mode outputs `<dir name="..."><file name="..."/></dir>` structure suitable for programmatic consumption by editors and IDEs.

- `format="ascii"` (default) — existing box-drawing character output
- `format="xml"` — structured XML tree, machine-readable
- XML output includes proper escaping of special characters in filenames

**Files:** `tools/tool_TreeView.py`

## 2026-07-06

### Added: `-Q` / `--quick` mode and `-P` / `--prompt` CLI flags + removed actions system

- **`-Q` / `--quick`** — Skips all interactive Prepare prompts (system message, history selection). Uses persona instructions + optional `-P` prefix as system message. Automatically enabled in server (`-S`) mode.
- **`-P "Your prompt"` / `--prompt "Your prompt"`** — Sets a custom system message prefix prepended to persona instructions. Works in both interactive and quick modes.
- **Server mode** (`-S`) — Now auto-enables quick mode. Starts without requiring stdin interaction.
- **Removed actions system** — Deleted `src/Actions.py`, `actions/` directory, and all action-related commands from Commands.py (`!AOS`, `!AOL`, `!AO`, `!IA`, `!PA`, `!EA`).

Usage examples:
```bash
ourai -S 0.0.0.0:9877 -p MediaAnalyst -P "You are a vision analyst"
ourai -Q -p Developer -m gemma3:12b   # non-interactive local session
ourai -S 0.0.0.0:9877 -p Developer -M 3   # server with specific history
```

**Files:** `config.py`, `run.py`, `src/Prepare.py`, `src/Handle.py`, `src/Commands.py`, `src/Server.py`, `src/Actions.py` (deleted), `actions/` (deleted), `.gitignore`, `CHANGELOG.md`

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
