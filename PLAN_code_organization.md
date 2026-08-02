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
| `src/ToolParser.py` | 929 | XML parsing + execution + caching + validation + plan-tools |
| `run.py` | 517 | CLI parsing, factory reset, persona resolution, server flags |
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

## Step 4 — `src/ToolParser.py` → coordinator
- `ToolXmlParser` — `ParseTextToolInvocation`, `ExtractToolResult`, `_format_action`, `CheckJobDone`
- `ToolExecutor` — `ExecuteTextTool`, `FireToolInvocation`, `_cache_key`, `_tool_usage`, `_validate_file`
- `PlanToolHandler` — `HandlePlanTool`
- `ToolParser` becomes a thin coordinator.
- **Verify**: `pytest -q`, tool invocation smoke test, commit.

## Step 5 — `run.py` → thin entry
- `src/cli.py` — `_preparse_server_flags` + arg parsing + `Help()`
- `src/FactoryReset.py` — `reset_to_factory`, `_confirm_factory_reset`
- `src/PersonaResolver.py` — `_list_personas`, `_resolve_persona`
- `run.py` keeps `Main`/`Run`/`cleanup`/`handle_exception`.
- **Verify**: `pytest -q`, `python run.py -Q -p Developer -Y "hi"` smoke, commit.

## Step 6 — Final pass
- Add import/smoke tests per new module; run full `pytest -q`; update `AGENTS.md` Architecture section if module list changed; one commit per step for clean bisect.

## Out of scope
- Any behavior changes, new features, renames of public APIs, or moving personas in `instruct/`.
