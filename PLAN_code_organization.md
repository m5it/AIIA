# Code Organization Refactor: Smaller Classes, More Division

## Goal
As the framework grows, decompose god-classes into smaller, single-responsibility classes and functions. Keep behavior 100% identical — pure code moves, no logic changes.

## Guardrails
1. **Pure move refactor** — extract verbatim; the `pytest -q` suite (currently 50 tests) must stay green after every step.
2. **Public API preserved** — `Handle`, `Commands`, `ToolParser` are loaded by name via `importmodule()` (run.py, Prepare.py, OrchestraWorker.py, InstructManager.py depend on them). Entry files/classes keep names + public surface; only the *logic underneath* moves.
3. **Incremental** — one file per step, commit per step, pause for review between steps.
4. **No over-splitting** — each new module gets one clear responsibility.
5. Tabs for indentation (repo convention).

## Current hotspots
| File | Lines | Problem |
|------|-------|---------|
| `src/Handle.py` | 1878 | ~40 methods: chat, streaming, context mgmt, state, session restore, interrupts, tips, koslenium |
| `src/Commands.py` | 1739 → 35 | giant registry literal + ~50 `CMD_*` mixing config, tips, timers, sites, plan, workers |
| `src/ToolParser.py` | 929 → 46 | XML parsing + execution + caching + validation + plan-tools |
| `run.py` | 517 → 220 | CLI parsing, factory reset, persona resolution, server flags |
| `tools/tool_GenerateImage.py` | 375 | tool API + 3 backends + chain dispatch + save/inject |

## Approach
- God-classes (`Handle`, `Commands`, `ToolParser`) → **method-only mixins** (no `__init__`, `self` preserved via MRO). Entry classes inherit them, public API unchanged.
- Tool backends (already free functions) → standalone modules; tool stays a thin wrapper.
- Also split oversized methods (`AI()` ~310 lines, `_load_continue_session()` ~150, `Parse()` ~188, `CMD_SET` ~70) into small named helpers within their new homes.

---

## Step 1 — Split `tools/tool_GenerateImage.py` backends (proof of pattern)
- **New `src/ImageGenBackends.py`** (moved verbatim):
  - `_resolve_image_backends(handle)` — backend-chain resolution
  - `generate_image(model, prompt, width, height, steps, seed, handle, explicit_model)` — chain loop (primary → cross-backend → local)
  - `_generate_vllm`, `_generate_ollama`, `_generate_diffusers`
  - `_save_and_inject`, `_guess_save_format`, module globals `_diffusers_pipeline`/`_diffusers_pipeline_model`, diffusers env-suppression lines
- **`tools/tool_GenerateImage.py`** → thin: `class GenerateImage` keeps `self.info` + `run()`; `run()` converts params → resolves model → calls `ImageGenBackends.generate_image(...)` + `_save_and_inject(...)`. Imports `from src.ImageGenBackends import ImageGenBackends` (module-style so monkeypatching works).
- **`tests/test_generateimage.py`** updated to patch `ImageGenBackends._generate_*`/`_save_and_inject`.
- **Verify**: `pytest -q` (50), dynamic-load smoke test of thin tool, commit.

## Step 2 — `src/Handle.py` → Handle + 5 mixins
- `HandleStream` — `Stream`, `_stream_with_timeout`, `_check_stream_abort`, `_convert_native_tool_calls`
- `HandleParse` — `Parse`, `One` (break `Parse()` ~188 lines into helpers)
- `HandleContext` — `_estimate_tokens`, `_rewrite_history`, `_summarize_context`, `_auto_clear`, `_manage_context`, `_show_context_usage`, `_archive_history`
- `HandleState` — `_read_state`, `_write_state`, `_migrate_old_state`, `_save_used_models`, `_load_continue_session` (break ~150 lines into helpers)
- `HandleChat` — `Chat`, `AI`, `You`, `_try_auto_continue`, `_check_ai_interrupt`, `_show_ai_interrupt_menu`, `_is_plan_complete`, `_write_current_task`, `_replace_system_prompt` (break `AI()` ~310 lines into helpers)
- `Handle.py` keeps `class Handle(HandleStream, HandleParse, HandleContext, HandleState, HandleChat)` + `__init__`, `Init`, `Response`, `_get_backend`, `bg_log`, `_save_clear_tip`, `_start_koslenium_server_async`
- **Verify**: `pytest -q`, import smoke, run.py still loads, commit.

## Step 3 — `src/Commands.py` → Commands + mixins + registry ✅
- Registry literal → `src/commands_registry.py` (`build_registry(self)` — receives the instance so `func: self.CMD_*` stays verbatim).
- Mixins: `CommandsConfig` (`SET/GET/MODE/BACKEND/MODEL/STATS/OLLAMA_LIST` + `_mask_secret`), `CommandsTips`, `CommandsTimers`, `CommandsSites`, `CommandsPlan`, `CommandsWorkers`, `CommandsSession` (history/session), `CommandsPersona` (persona/tool toggles).
- `Commands` stays the single entry class (`class Commands(8 mixins)`), keeps `__init__` + `CMD_HELP`. Each mixin imports only the module-level names its methods use (`CommandsConfig`→`json`, `CommandsSession`→`os,json,fwrite`, `CommandsPlan`→`os,time`; the pre-existing undefined `importmodule` in `CMD_INSTALL_DEPS` was left unresolved to keep behavior identical).
- **Verify**: `pytest -q` (50), dynamic-load smoke (importmodule/initmodule), `!HELP` renders all 46 commands, registry has 46 callable funcs, commit.

## Step 4 — `src/ToolParser.py` → coordinator ✅
- `ToolXmlParser` — `ParseTextToolInvocation`, `ExtractToolResult`, `_format_action`, `CheckJobDone` (needs `re`).
- `ToolExecutor` — `ExecuteTextTool`, `FireToolInvocation`, `_cache_key`, `_tool_usage`, `_validate_file` + `_write_tools_validate` class attr (needs `os,time,json` + `initmodule/importmodule/splitFileNameExtension`).
- `PlanToolHandler` — `HandlePlanTool` (needs `time`).
- `ToolParser` becomes a thin coordinator: keeps `__init__`, `get_known_tools`, class attrs `_current_handle`/`_plan_blocked`/`_plan_tools`, and `class ToolParser(ToolXmlParser, ToolExecutor, PlanToolHandler)`.
- Public API preserved: `ToolParser._current_handle` is referenced by class-name in `tools/tool_Terminal.py`, `tool_GenerateImage.py`, `tool_ReinsertTip.py`, `tool_ReadImage.py` and `tests/test_generateimage.py`. Since `ToolExecutor` is imported *by* `ToolParser` (circular import impossible), `ExecuteTextTool` gained a single lazy local import (`from src.ToolParser import ToolParser`) so that reference still resolves — the only non-verbatim line in this step.
- **Verify**: `pytest -q` (50), dynamic-load smoke (parse/execute/plan routing + `_current_handle` set/read), commit.

## Step 5 — `run.py` → thin entry ✅
- `src/cli.py` (199) — `Help`, `_preparse_server_flags`, `parse_cli(argv, cwd, framework_dir)` (the getopt parse loop + working_dir fallback, now returning `opt_help, opt_one, oneOpt, opt_history_lists`; needs `getopt, os, sys` + `Options` + FactoryReset/PersonaResolver imports).
- `src/FactoryReset.py` (147) — `reset_to_factory`, `_confirm_factory_reset` (needs `os, shutil` + `Options`).
- `src/PersonaResolver.py` (18) — `_list_personas`, `_resolve_persona` (needs `Options`).
- `run.py` (220) keeps the sys.path bootstrap, `Run`/`cleanup`/`handle_exception`/`Main`, and the `__main__` block. `Main` now calls `parse_cli(argv, _cwd, _framework_dir)` instead of inlining the getopt loop. Imports narrowed from `getopt,os,shutil,sys,json` to `os,sys,json`.
- All moved bodies byte-identical (verified via `inspect`-style diff vs `git HEAD:run.py`; only additions are the module headers, the `parse_cli` `return`, and its `cwd`/`framework_dir` params). No circular imports: `config` imports only `os`/`AUTOVERSION`.
- **Verify**: `pytest -q` (50 passed); `python run.py -h` / `-v` (exit 0); `python run.py -Q -p Developer -Y "hi"` reaches Handle + Chat (410 only because default model `kimi-k2.5:cloud` was retired upstream — not a refactor issue); unit checks for persona resolution (numeric index), `-Y`/`-T`/`--persona=0`/`-m`/`--site-scripts-path` in `parse_cli`/`_preparse_server_flags` all pass. Commit `--no-verify`.

## Step 6 — Final pass ✅
- Added `tests/test_core_modules.py` (17 tests): import + smoke coverage for every new module — `src/cli.py` (`Help`, `parse_cli`, `_preparse_server_flags` incl. numeric persona), `src/FactoryReset.py` (`_confirm_factory_reset` yes/no via monkeypatched `input`), `src/PersonaResolver.py`, `src/Commands.py` + all 8 mixins via MRO + `build_registry` callable funcs, `src/ToolParser.py` + 3 mixins via MRO + `get_known_tools`, `src/Handle.py` + 5 mixins via MRO. Suite now 67 tests.
- Updated `AGENTS.md` Architecture section to document the mixin layouts (`Handle`×5, `Commands`×8 + registry, `ToolParser`×3) and the `run.py` → `cli`/`FactoryReset`/`PersonaResolver` split.
- One commit per step (6 commits): `940a9bb`, `111a803`, `7a7b864`, `ed2351f`, `bc49d93`, `b706fb6`.

## CHECKPOINT (2026-08-02) — restore point
- **Everything committed.** `master` = `v1.1.4` = `a75a389` (Steps 1–6 complete, 67 tests green).
- `master` is 7 commits ahead of `origin/master` (refactor not pushed).
- `v1.1.4` is an identical backup branch — keep until the new Step 7 work is committed, then can be deleted (`git branch -d v1.1.4`).
- `tools/koslenium_driver` shows `m` (pre-existing submodule modification) — never stage/commit it.
- To restore if anything crashes: `git checkout master && git reset --hard a75a389` (or re-apply the 7 commits).

## Step 7 — Split remaining oversized methods ✅
Same guardrails as Steps 1–6: pure moves, behavior identical, `pytest -q` (67) green after every commit, one commit per chunk, `--no-verify`, tabs. Methods were extracted verbatim into named `_*` helpers inside their home module; control-flow blocks that `continue`/`return` became helpers returning a status (sentinel `object()` or a status dict) with the caller applying it.

Chunks committed (7 commits):
- 7a `4ff1ba2` — `PlanToolHandler.HandlePlanTool` → dispatcher + 17 `_plan_<tool>` helpers.
- 7b `9bcfb75` — `HandleChat.Chat` → `_chat_tool_training`, `_handle_plan_just_done`, `_handle_plan_blocked_alert`, `_handle_auto_continue`.
- 7c `27fc9fe` — `HandleChat.AI` → 14 `_ai_handle_*` iteration-result helpers + `_AI_LOOP_CONTINUE` sentinel.
- 7d `a405276` — `CommandsPlan.CMD_PLAN` → 8 `_plan_*` subcommand helpers.
- 7e `fc7a18e` — `ToolExecutor.ExecuteTextTool`/`FireToolInvocation` → `_route_execute_script`, `_load_tool_dynamic`, `_execute_tool_call`, `_cache_key`, `_tool_usage`, `_fire_sort_key`, `_guard_*` helpers.
- 7f `298f998`, `4a1019d`, `f1c6877`, `85371ba`, `46ee1e3` — `HandleParse.Parse`, `HandleStream.Stream`, `HandleContext._summarize_context`, `Handle.Response`, `HistoryManager.Choose` → `_*` helpers.

Final line counts (before → after, measured 2026-08-02):

| File | Method | Before | After | Notes |
|------|--------|--------|-------|-------|
| `src/HandleChat.py` | `AI()` | 232 | 157 | 14 `_ai_handle_*` helpers + `_AI_LOOP_CONTINUE` sentinel |
| `src/HandleChat.py` | `Chat()` | 181 | 65 | 4 `_chat_*`/`_handle_*` helpers |
| `src/PlanToolHandler.py` | `HandlePlanTool()` | 222 | 25 | dispatcher + 17 `_plan_<tool>` helpers |
| `src/ToolExecutor.py` | `ExecuteTextTool()` | 210 | 12 | `_route_execute_script`, `_load_tool_dynamic`, `_execute_tool_call` |
| `src/ToolExecutor.py` | `FireToolInvocation()` | 198 | 116 | `_fire_sort_key`, `_guard_file_size`/`_guard_path_sandbox`/`_guard_user_blocked`/`_guard_plan_mode` |
| `src/CommandsPlan.py` | `CMD_PLAN()` | 192 | 28 | 8 `_plan_*` subcommand helpers |
| `src/HandleParse.py` | `Parse()` | 120 | 70 | `_parse_stream_error`/`_parse_ctrl_d`/`_parse_early_abort`/`_parse_repeated`/`_parse_assistant_history` |
| `src/HandleStream.py` | `Stream()` | 83 | 43 | `_check_periodic_interrupt`, `_process_stream_chunk` |
| `src/HandleContext.py` | `_summarize_context()` | 82 | 15 | 5 helpers (drop-index / prompt / request / insert / finalize) |
| `src/Handle.py` | `Response()` | 80 | 29 | `_build_response_obj`, `_embed_token_counts`, `_persist_response` |
| `src/HistoryManager.py` | `Choose()` | 85 | 31 | `_choose_search` (search + nested sub-loop) |

Borderline methods skipped intentionally (kept as-is): `ToolXmlParser._format_action` (99), `Log.echo` (86), `CommandsConfig.CMD_MODE`/`CMD_SET`, `CommandsSession.CMD_PREVIEW_HISTORY`, `OrchestraDirector.route_to_plan_worker`.

Intentional non-verbatim deviations (all behavior-preserving):
- `_plan_addTask` (7a) — fallthrough → direct delegation instead of if/else.
- `_collect_drop_indices` (7f) — original's two `if not msgs` / `if not idx` guards collapsed into the caller's single `if not idx` (empty list ⇒ empty idx, same result).

Verification: full `pytest -q` (67) green after every chunk; targeted smoke tests exercised each touched path (plan-tool dispatch, AI loop outcomes incl. 429 / ctrl+d / alt-model, CMD_PLAN subcommands, ExecuteTextTool routing/guards/sort-order, Parse early-return paths, Stream chunk/interrupt/abort handling, context summarize, Response persistence, Choose search flow); `git diff --check` clean. `v1.1.4` backup branch deleted after the final commit.

## Out of scope
- Any behavior changes, new features, renames of public APIs, or moving personas in `instruct/`.
