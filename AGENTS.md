# AGENTS.md

## Commands

```bash
source .venv/bin/activate       # activate virtual environment (Python 3.10)
pip install -r requirements.txt  # install common core deps (fast, ~5MB)
pip install -r requirements-ollama.txt  # install default backend (Ollama)
pip install -r requirements-vllm.txt    # install vLLM backend instead (OpenAI-compatible)
pip install -r requirements-gpu.txt  # optional GPU deps (torch, diffusers, etc.)
pip install -r requirements-marketplace.txt  # optional aiia_work marketplace client (separated feature)
python run.py                    # start AIIA interactive session
python run.py -m gemma3:12b     # specify model (default: kimi-k2.5:cloud, see config.py)
python run.py -b vllm -m <model>  # use vLLM backend (OpenAI-compatible, default: ollama)
python run.py -p MediaAnalyst   # use MediaAnalyst persona (image/video analysis)
python run.py -Q -p Developer   # quick mode — skip interactive prompts
python run.py -P "You are a coding assistant"  # custom system message prefix
python run.py -Y "prompt"        # single request, no interactive session
python run.py -d                 # enable debug output
python run.py -T 0.8             # set temperature
python run.py -c                 # continue a previous project session (loads state.aiia and HISTORY.md, skips startup prompts)
python run.py -Q                 # quick mode — skip startup prompts (use with -c to restore state without interactive prompts)

python run.py --work             # start aiia_work marketplace client (!WORK commands)
python run_orchestra.py --port 9876        # start orchestra director
python run_worker.py --connect localhost:9876 --name w1 -m gemma3:12b  # start worker

# Build koslenium_driver (Java web client)
cd tools/koslenium_driver && ./build.sh     # build both driver + www jars
cd tools/koslenium_driver && ./build.sh quick  # incremental compile (fast)
cd tools/koslenium_driver && ./build.sh test   # run Java tests
```

## Auto-Versioning

```bash
git config core.hooksPath hooks   # enable auto-versioning on every commit
```

Each commit auto-increments the third decimal in `AUTOVERSION.py` (e.g., `1.0.0` → `1.0.1`) and prepends an entry to `CHANGELOG.md` with the date, new version, and changed files. Merge commits are skipped.

## User Commands

| Command | Description |
|---------|-------------|
| `!MODE [plan\|build]` | Switch modes |
| `!START_BUILD` | Switch to build mode and start executing tasks |
| `!MODELS` | List models on the active backend (used ones starred) |
| `!MODEL <name>` | Switch AI model mid-session |
| `!BACKEND <ollama\|vllm>` | Switch LLM backend mid-session |
| `!PLAN [PREVIEW\|VIEW\|TASKS\|STATUS\|LIST\|CLEAR\|DELETE\|RESET\|DONE]` | View / manage plan |
| `!GET <key>` | Show any config value |
| `!HELP` | Show all commands |
| `!STATS` | Token counts |
| `!SET <key> <value>` | Override any config at runtime (e.g. `!SET NUM_PREDICT 16384`) |
| `!NEW SESSION` | Full reset |
| `!SUMMARIZE` | Clear chat history (keeps system messages), then warm the model back up on available tools and tips — as a single system message that also preserves the active plan |
| `!REHEAT` | Re-run the startup warm-up: refresh tool infos and reload saved tips |
| `!SH <term>` | Search chat history for a term; prints matching row numbers (`!SH -r <regex>` for regex) |
| `!PH [row]` | Preview chat history; `!PH <N>` shows a single row in full |
| `!RH <row>` or `!RH <from> <to>` | Remove a row, or an inclusive range of rows, from chat history |
| `!SAVE_HISTORY [filename]` | Export current chat history as a reloadable `.dbk`-style file (saved to `history/` and the framework root); a bare name without an extension gets `.dbk` appended |
| `!AH [search_term]` | List all available history files, or search them by term — matches filename OR content (same as the startup history chooser) |
| `!INSTALL_DEPS [persona]` | Install missing persona dependencies |
| `!CACHE` | List the write-tool file buffer cache (`!CACHE SHOW <file>` previews, `!CACHE CLEAR` empties it) |
| `!SITE_LIST` | List all websites with available JS support scripts |
| `!SITE <domain>` | Show available scripts for a specific website |
| `!SITE_UPDATE <domain> <script>` | Create or update a website JS support script |

## User Commands (build mode)

| Command | Description |
|---------|-------------|
| `1` | Switch to build mode |
| `2` | Stay — let AI continue planning |
| `3` | Cancel — stop the current turn |
| `4` | Continue — allow the blocked action |

When the model attempts a blocked tool (WriteFile/CreateFile/ReplaceLine/Sed/ExecuteScript) during plan mode, Build Mode Manager shows these options so you can let the AI proceed with implementation work mid-plan.

## LLM Backends

Chat requests run through a pluggable backend abstraction (`src/LLMBackends/`), so the core can use **Ollama** (default) or any **OpenAI-compatible server** (e.g. **vLLM**).

- `AI_BACKEND: "ollama" | "vllm"` — active backend (config.py / aiia.json / `-b` flag / `!BACKEND`)
- `VLLM_HOST` — OpenAI-compatible base URL (default `http://localhost:8000/v1`)
- `VLLM_API_KEY` — optional API key
- `VLLM_TIMEOUT` — request timeout in seconds
- `AI_IMAGE_BACKEND: "auto" | "ollama" | "vllm" | "local"` — image generation backend (`auto` follows `AI_BACKEND`; `local` = diffusers) — lets you e.g. chat via vLLM while generating images via Ollama

Classes:
- `src/LLMBackends/BaseBackend.py` — shared interface (`chat()`, `list_models()`, `name`, `is_vllm`)
- `src/LLMBackends/OllamaBackend.py` — wraps `ollama.Client`; returns native `ChatResponse` objects
- `src/LLMBackends/VLLMBackend.py` — wraps the `openai` SDK; emits duck-typed stream chunks shaped like Ollama so `Handle.Stream()` needs no changes

### Hugging Face Inference API (serverless OpenAI-compatible router)

HF's hosted router speaks the OpenAI Chat Completions API, so you can point the **existing `vllm` backend** at it — no new backend or code changes:

```bash
pip install -r requirements-vllm.txt
python run.py -b vllm -m Qwen/Qwen3-8B
```

`config.py` / `aiia.json`:
- `AI_BACKEND: "vllm"`
- `VLLM_HOST: "https://router.huggingface.co/v1"`
- `VLLM_API_KEY: "hf_<token>"` — fine-grained HF token with **"Make calls to Inference Providers"** permission (https://huggingface.co/settings/tokens)
- `AI_MODEL: "<hf model id>"` (e.g. `Qwen/Qwen3-8B`)

Notes:
- `!MODELS` works — the router exposes `GET /v1/models` (OpenAI-style model list)
- **Set `AI_THINK: false`** — HF does not accept vLLM's `enable_reasoning` extra body param
- **Set `AI_IMAGE_BACKEND: "local"`** — HF has no `{host}/images/generations` endpoint (use diffusers for image generation)
- HF models aren't in the model registry (`src/ModelRegistry.py`), so unknown-model context defaults are conservative — tune with `!SET AI_CONTEXT_LIMIT <n>`

Behavior notes:
- The `ollama` import is lazy — vLLM-only installs don't need the ollama python package
- Ollama options are mapped to OpenAI params: `num_predict`→`max_tokens`, `num_ctx` dropped, `think`→`extra_body.enable_reasoning` + `reasoning_content`
- Ollama vision messages (`images: [base64]`) are converted to OpenAI `image_url` content parts
- `GenerateImage` tool is backend-agnostic: `AI_IMAGE_BACKEND` (default `auto` → follows `AI_BACKEND`) picks Ollama, vLLM-Omni, or local diffusers; cross-backend fallback then local diffusers on failure
- `!MODEL`'s GPU-freeing (`ollama stop`) only runs on the ollama backend

## Codecov

```bash
# Run tests with coverage locally
source .venv/bin/activate
pip install -r requirements.txt
pytest --cov --cov-branch --cov-report=xml

# Upload to Codecov (set env var once in your shell or in CI)
#   GitHub repo secret: Settings → Secrets and variables → Actions → CODECOV_TOKEN
#   Local: export CODECOV_TOKEN=f75b948b-8c84-4523-a32f-2d7a3701757a
#   CI:    The workflow at .github/workflows/ci.yml passes ${{ secrets.CODECOV_TOKEN }} as env var
#          The action also reads $CODECOV_TOKEN from the runner's env automatically.
pip install codecov-cli
CODECOV_TOKEN="$CODECOV_TOKEN" codecovcli upload-report

# Badge (PVP: add to README.md):
#   [![codecov](https://codecov.io/gh/m5it/OurAI/branch/main/graph/badge.svg)](https://codecov.io/gh/m5it/OurAI)
```


## Architecture

- **Entry point**: `run.py` → thin entry; CLI parsing in `src/cli.py`, factory reset in `src/FactoryReset.py`, persona resolution in `src/PersonaResolver.py`, then initializes `Handle` class from `src/Handle.py`
- **Orchestra entry points**: `run_orchestra.py` (director), `run_worker.py` (worker)
- **Marketplace entry point**: `run_work.py` (aiia_work client, `python run.py --work`)
- **Core modules**: all in `src/` — `Handle.py` orchestrates chat, tools, history via 5 mixins (`HandleStream`, `HandleParse`, `HandleContext`, `HandleState`, `HandleChat`); `Commands.py` routes user `!`-commands via 8 mixins (`CommandsConfig` … `CommandsWorkers`) with the command registry in `src/commands_registry.py`; `ToolParser.py` parses/executes XML tool calls via 3 mixins (`ToolXmlParser`, `ToolExecutor`, `PlanToolHandler`)
- **Personas**: `instruct/` directory — personality classes with plan/build system prompts, optional model override
- **Tools**: `tools/` directory — dynamically loaded Python classes that the AI invokes via `<ToolName>` XML syntax
- **Dependency system**: `src/DependencyChecker.py` + `src/DependencyInstaller.py` — check/install per-persona deps into isolated venvs at `~/.config/aiia/envs/<persona>/`, tracked in `~/.config/aiia/persona_deps.json`. Personas define requirements via `requirements()` method (pip packages + HF models). Automatically checked on persona switch; manual trigger via `!INSTALL_DEPS`.
- **Plan/build loop**: plan-mode auto-continues as long as last AI response used tools and plan is not yet complete. Blocked tools (WriteFile/CreateFile/ReplaceLine/Sed/ExecuteScript) during planning show a 1-4 user menu. Plan completion detected via key phrases in assistant output.
- **Per-project state**: `state.aiia` (project dir when running from a project) stores model, mode, persona, token counters, and `!SET` overrides. `HISTORY.md` (project dir) stores the current session chat. `python run.py -c` loads both and resumes the session without startup prompts.
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

**Available tools (30 total):**
- `ReadFile` — Read from `workin/` (params: `<fileName>`, `<offset>` optional, `<lines>` optional, `<max_chars>` optional, `<lineNumbers>` optional — when `true`, prepends original 1-based line numbers, useful before `ReplaceLine`/`AppendFile`)
- `ReadPDF` — Extract text and metadata from PDF files (params: `<fileName>`, `<fromPage>` optional, `<toPage>` optional, `<limit>` optional)
- `WriteFile` — Write to `workout/` (params: `<fileName>`, `<contentOfFile>`)
- `AppendFile` — Append or insert in a file (params: `<fileName>`, `<contentOfFile>`, `<fromLineNumber>` optional — `0` = before first line, `N` = after line `N` using the 1-indexed line numbers from `ReadFile <lineNumbers>true</lineNumbers>`, `-1`/omitted = append at end)
- `CreateFile` — Create new file in `workout/` (fails if exists) (params: `<fileName>`, `<content>`)
- `ReplaceLine` — Replace specific line(s) in a file (params: `<fileName>`, `<fromLine>`, `<toLine>` optional, `<replacement>`, `<confirmed>`). Line numbers are 1-indexed by default (config `REPLACELINE_ZERO_INDEXED`). Three-phase flow: preview (includes a unified diff + indentation check) → `confirmed=true` applies + shows a verification diff (whole-file backup saved to `/tmp`) → `confirmed=finalize` accepts or `confirmed=revert` restores from backup
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
- `CurrentTime` — Get current date/time (params: `<format>` optional, `<timezone>` optional)
- `WWW` — Fetch a web page via the Java web client. Supports JS rendering, screenshots, and auto-execution of per-website support scripts. (params: `<url>`, `<js>`, `<browser>`, `<text>`, `<links>`, `<source>`, `<screenshot>`, `<wait>`, `<selector>`, `<siteScript>`, `<jsExecute>`, `<cacheSource>`) — also invocable as `<www>` and `<WWWJS>`
- `WWWExec` — Execute JavaScript on the currently loaded page in the persistent browser window (params: `<js>`, `<wait>`)
- `ParsePage` — Parse a cached HTML page locally with BeautifulSoup. Extract scripts, links, metadata, text, DOM tree, or run CSS queries. (params: `<fileName>`, `<action>` [scripts/links/meta/text/tree/query], `<selector>` for query, `<limit>`, `<full>`)
- `SiteScript` — Discover and execute per-website JS support scripts (params: `<site>`, `<script>`, `<action>`, `<params>`)
- `UpdateSiteScript` — Create or update per-website JS support scripts (params: `<site>`, `<script>`, `<content>`, `<action>`, `<info>`)
- `SaveTip` — Save a tip with title and content to model storage (params: `<title>`, `<content>`)
- `GetTip` — Retrieve a saved tip by title (params: `<title>`, `<source>` optional)
- `ListTips` — List all saved tips (params: `<source>` optional)
- `DeleteTip` — Delete a tip by title (params: `<title>`, `<source>` optional)
- `ReinsertTip` — Reinsert a saved tip's entries into current chat history (params: `<title>`)

**Tool result caching:** Tools with a `cache_ttl` class attribute (e.g., listTools=600s, TreeView=300s) automatically cache results. Cache entries stored under `~/.config/aiia/tips/_cache/{toolname}/{key_hash}.json`. Cache invalidates on TTL expiry, tool file mtime change, `!CACHE_CLEAR`, `!NEW SESSION`, or `!UPDATE HANDLE`. Global default TTL: 86400s (1 day) via `TOOL_CACHE_TTL` in config.

**File buffer cache (long data):** When a plan is active, the write tools (`WriteFile`/`CreateFile`/`AppendFile`/`ReplaceLine`/`Sed`-inplace) cache the assembled content of each file they touch in memory (`handle.file_buffer_cache`, keyed by the fileName the model passed). After a context auto-clear or summarize, the cached buffers are re-appended into the injected system message (plan-gated) so the model can continue chunked writes on small-context models. Config: `TOOL_FILE_CACHE` (master toggle), `TOOL_FILE_CACHE_ON_PLAN`, `TOOL_FILE_CACHE_MAX_FILE` (skip larger files), `TOOL_FILE_CACHE_MAX_FILES` (eviction), `TOOL_FILE_CACHE_REINJECT` (reinject on clear), `TOOL_FILE_CACHE_REINJECT_MAX` (per-file cap), `TOOL_FILE_CACHE_REINJECT_TOTAL` (total cap; files beyond it become one-line manifest entries). Cache is cleared when the plan finishes (`jobDone`) or via `!CACHE CLEAR`; inspect with `!CACHE` / `!CACHE SHOW <file>`.

**Transient tool results (small-context paging):** Read tools (`ReadFile`/`ReadPDF`/`Head`/`Tail`/`Grep`/`List`/`TreeView`/`Sort`/`Diff`/`WWW`/`WWWJS`/`ParsePage`) accept a `<transient>N</transient>` parameter. The tool result (and the assistant row that issued it) are auto-removed from history after N AI-loop iterations, so the model can page through large files in bounded chunks without re-filling the context window. Example: `<ReadFile><fileName>big.py</fileName><offset>0</offset><max_chars>2000</max_chars><transient>3</transient></ReadFile>`. Config: `TOOL_TRANSIENT_ENABLED`, `TOOL_TRANSIENT_MAX_STEPS` (clamp).

**Large file writing:** When `num_predict` is set, the model may hit the output token limit mid-write. If truncation is detected, the model is warned automatically and chunked writing instructions are injected into the persona. Use `<WriteFile>` for the first ~200 lines, then `<AppendFile>` for subsequent chunks. Override with `!SET CHUNKED_WRITE_HINT true/false`.

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

**Site script tool examples:**
```xml
<SiteScript>
<site>google.com</site>
<action>list</action>
</SiteScript>

<SiteScript>
<site>google.com</site>
<action>info</action>
</SiteScript>

<SiteScript>
<site>google.com</site>
<script>support_search</script>
<params>{"query":"python programming"}</params>
</SiteScript>

<UpdateSiteScript>
<site>google.com</site>
<script>support_search</script>
<content>// ==SiteScript==
// title: Google Search
// name: support_search
// site: google.com
// description: Search Google and return structured results.
// usage: <SiteScript site="google.com" script="support_search" params='{"query":"text"}'/>
// params: query (string) required
// returns: JSON array of results
// ==/SiteScript==
// ... JS code ...
</content>
</UpdateSiteScript>
```

**jsExecute + save-for-reuse workflow:**
```xml
<!-- Step 1: Extract data from URL using JS -->
<WWW>
<url>https://github.com/m5it?tab=repositories</url>
<jsExecute>Array.from(document.querySelectorAll("a[itemprop='name']")).map(a => a.textContent.trim())</jsExecute>
</WWW>

<!-- Step 2: Save the JS as a reusable site script -->
<UpdateSiteScript>
<site>github.com</site>
<script>get_repos</script>
<content>// ==SiteScript==
// title: Get User Repositories
// name: get_repos
// site: github.com
// description: Extract repository names from a GitHub profile page.
// usage: Navigate to profile, then: <SiteScript site="github.com" script="get_repos"/>
// returns: JSON array of repository names
// ==/SiteScript==
return Array.from(document.querySelectorAll("a[itemprop='name']")).map(a => a.textContent.trim());
</content>
</UpdateSiteScript>

<!-- Step 3: Next time, use the saved script directly -->
<SiteScript>
<site>github.com</site>
<script>get_repos</script>
</SiteScript>
```

**Source cache (large HTML pages):**
When `<source>true</source>` returns content exceeding `WWW_SOURCE_MAX_SIZE` (default 80K chars), the full HTML is saved to `workout/` and a warning is returned instead. Use `<ReadFile>` with line ranges or `<Grep>` to read parts:
```xml
<!-- Source too large — saved to workout/www_source_20260725_143022.html -->
<ReadFile>
<fileName>workout/www_source_20260725_143022.html</fileName>
<fromLine>100</fromLine>
<toLine>200</toReadFile>

<Grep>
<pattern>itemprop="name"</pattern>
<fileName>workout/www_source_20260725_143022.html</fileName>
</Grep>
```

## Module System

The project uses a custom module loader (`src/functions.py`):
- `importmodule("Name", reload=True, {'path': 'src'})` — imports and optionally reloads modules
- `initmodule(imported, "ClassName", opts)` — instantiates classes with options
- `functions.py` exists in both root and `src/` — `src/functions.py` is the canonical version used by core modules

## Instructions System

Mode instructions (system prompts for plan/build modes) live in `instruct/` as persona classes:
- `instruct/Developer.py` — default persona, provides `plan()` and `build()` methods
- `instruct/DeveloperV2.py` — Developer variant with explicit "STOP after planDone" instructions and clearer mode-transition language
- `instruct/DeveloperV3.py` — DeveloperV2 plus framework-awareness sections explaining system-vs-user turn messages and auto-continue
- `instruct/MediaAnalyst.py` — image/video analysis persona (default model: qwen3-vl:latest)
- `instruct/BookSmith.py` — literary assistant for book analysis and writing (default mode: build, requires pypdf/python-docx/ebooklib)
- `instruct/BookSmithV2.py` — V2 with explicit stop signals, clearer mode transitions, analysis/writing workflow split (default mode: plan)
- `instruct/BookSmithV3.py` — V3 with framework-awareness, long-context book handling, auto-continue explained (default mode: plan)
- `instruct/BookSmithAnalyst.py` — literary/critical analysis specialist: thematic, structural, character, stylistic analysis (default mode: plan)
- `instruct/BookSmithNovelist.py` — fiction writing specialist: story structure, character craft, scene construction, revision (default mode: build)
- `instruct/BookSmithPoet.py` — poetry specialist: analyze and write poems across forms, meters, and traditions (default mode: build)
- `instruct/BookSmithEditor.py` — editing & revision specialist: developmental, line, copy edits, and proofreading (default mode: build)
- Switch persona via `config.py`: `INSTRUCT_CLASS` option (e.g., `"Developer"`)
- The `[--#THINKING#--ID1--]` placeholder in both plan and build text is replaced at runtime based on mode and `BUILD_THINKING_DISABLED` option
- Create new personas by adding files to `instruct/` with the same `plan()`/`build()` interface
- Personas can optionally define `requirements()` returning `{pip_packages: [...], hf_models: [...], size_gb: N}` for automatic dependency installation

## Runtime Requirements

- Ollama server running (default: `localhost:11434`, override via `OLLAMA_HOST` env var) — or a vLLM server with `-b vllm` (see LLM Backends)
- Virtual environment at `.venv/` (Python 3.10.12)
- Default model: `kimi-k2.5:cloud` (config.py) — change with `-m` flag
- LM Studio SDK in `package.json` but not used by Python code (Node deps appear unused)

## Per-Project Config (`aiia.json`)

Place an `aiia.json` file in your project directory to override global `config.py` defaults:

```json
{
  "AI_MODEL": "gemma3:12b",
  "AI_OPTIONS": {
    "temperature": 0.8,
    "num_ctx": 65536
  },
  "MODE": "build",
  "AI_MAX_ITERATIONS": 20,
  "AI_THINK": false
}
```

**Override priority** (highest to lowest):
1. CLI flags (`-m`, `-p`, `-T`, etc.)
2. `aiia.json` (in CWD when `run.py` is invoked)
3. `config.py` global defaults

**Merge rules**: dict-typed options (e.g. `AI_OPTIONS`) are deep-merged — individual keys update rather than replacing the entire dict. Simple values replace the global default. CLI flags always win.

Only loaded when CWD differs from the framework directory (i.e., when you `cd` into a project and run `aiia` from there).

## Response Limits

- `AI_MAX_CONTENT_LEN` (default `20000`) — max assistant response content characters; user input already rejected above it, and assistant responses now abort mid-stream and append a warning.
- `AI_THINK_LIMIT` (default `8192`) — max thinking/reasoning characters per response. Streams are aborted and a warning is injected as a `user` message so the model is forced to be concise. Set to `0` to disable.

## Testing Flags

Session-only testing toggles (never persisted to `state.aiia`; flip with `!SET`).

- `AI_FREEZE_HISTORY` (default `0`) — when `1`, **every** chat-history append is skipped (disk + `HISTORY.md` + in-memory `msgs`), for all roles (user/assistant/tool/system). The model keeps seeing the exact context that was loaded when the flag was set. Typical use: start the framework, load an old history, `!SET AI_FREEZE_HISTORY 1`, then query the model repeatedly — responses stay stable since the context never changes. Set `!SET AI_FREEZE_HISTORY 0` to resume normal history recording.
- `AI_FREEZE_LOOP` (default `0`) — when `1`, the conversation pointer stays on `role:user`: instead of showing the prompt for new input, the last user message is re-sent to the model, repeating forever until reset. **Escape hatch:** press Ctrl+C/D during streaming and choose "2. Stop AI" — this pauses the repeat and returns to the prompt, where you can `!SET AI_FREEZE_LOOP 0`. Any new typed input clears the pause and resumes repeating with the new message.

## Plan/Build Autoclean

Persisted feature flags (saved to `state.aiia`; flip with `!SET`).

- `AI_PLANBUILD_AUTOCLEAN` (default `0`) — when `1`, finished plan/build task work is auto-pruned from the model context so long plan tasks don't re-fill the context window.
- `AI_PLANBUILD_WAIT` (default `5`, min `1`) — number of assistant responses after the latest task anchor before a clean triggers.

How it works:

1. The framework detects "task anchors" by content marker in history: the first `user` message, the `planDone` system message (`"Plan is ready! Starting first task."`), the `startBuild`/mode-switch system message (`"Mode changed to BUILD."`), and each `<nextTask>` user message.
2. Cleaning is triggered **only by a `<nextTask>` transition** — never by `planDone`/`startBuild`, and never mid-task. When a task completes, `AI_PLANBUILD_WAIT` assistant responses are counted, then the **just-completed task's block** (the non-system messages between the previous task anchor and that `nextTask`) is dropped.
3. On the **first** `nextTask`, the planning phase is also pruned: the plan-creation rows before `Mode changed to BUILD...` (including the first `user` message) are dropped alongside the first task's work. From the second `nextTask` on, only the just-completed task's own block is pruned — earlier task work stays in context.
4. After pruning, the **active mode-instruction system message** is relocated to the end of the chat so it doesn't end up stranded at the top of the context. In build mode the `"Plan is ready! Starting first task."` anchor is removed (it's superseded by the build instruction) and the `"Mode changed to BUILD."` anchor is moved to the end. If no build-switch anchor exists, the lone plan-ready anchor is moved instead. If the last message in the chat is already a `system` message, the relocated anchor replaces it (following the placement rule: *append at the end; replace only if the previous message role is `system`*). The persona and other system messages are otherwise left in place.
5. Only `HISTORY.md` is rebuilt (so `python run.py -c` resumes the cleaned view); the raw session `.dbk` in `root/history/` keeps **all** rows untouched. A later explicit history rewrite (`!RH`, `!SUMMARIZE`, `!NEW SESSION`, `_auto_clear`, mode switch) re-syncs `.dbk` from the pruned in-memory history.

Cleaning is skipped while `AI_FREEZE_HISTORY=1`, outside build mode, when fewer than 2 anchors exist, once the plan is fully completed (`jobDone`), and on turns that fire `planDone`/`startBuild` (which reset the counter and disarm the pending clean instead).

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

## aiia_work Marketplace Client

Separate, opt-in feature (`python run.py --work`). Isolated from the normal chat session — no XML/AI tools, only `!WORK` commands. Lives in the standalone `aiia_work/` package (no `src/` deps) + `run_work.py` entry point, wired into `run.py`'s subcommand routing.

```bash
pip install -r requirements-marketplace.txt
python run.py --work --base-url http://localhost:8006/rest/aiia_work
```

**API key resolution** (priority order): env `AIIA_WORK_API_KEY` > config `AIIA_WORK_API_KEY` > stored key file `~/.config/aiia/aiia_work.json` (created automatically after `!WORK KEYGEN`). `!WORK KEYGEN` needs an SSO bearer token (`--sso-token` / `AIIA_WORK_SSO_TOKEN`).

**`!WORK` commands:** `HELP`, `KEYGEN [label] [role]`, `KEYS`, `KEYREVOKE <id>`, `CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]`, `LIST`, `SHOW <id>`, `STATUS <id> <open|in_progress|completed|closed>`, `APPLY <project_id> <msg>`, `MY`, `ACCEPT <rid>`, `DECLINE <rid>`, `CMD <name> [json]` (framework bridge), `QUIT`.

Config keys: `AIIA_WORK_BASE_URL` (default `https://apis.aiia-frame.work/rest/aiia_work`), `AIIA_WORK_API_KEY`, `AIIA_WORK_SSO_TOKEN`, `AIIA_WORK_KEY_FILE`, `AIIA_WORK_ROLE`, `AIIA_WORK_TIMEOUT`, `AIIA_WORK_RETRIES`.

## Quirks

- **Indentation**: code uses tabs (not spaces) despite being Python
- **Dynamic reload**: tools are reloaded on each use via custom import system — changes take effect immediately
- **Session state**: `sessid.aiia` tracks session counter; history files named `{session_id}.dbk` and `{session_id}.user.dbk`
- **Tests**: pytest suite in `tests/` (`pytest -q`); `tests/old_*.py` are legacy standalone scripts, not collected
- **No linting**: no linter, formatter, or typechecker configured
