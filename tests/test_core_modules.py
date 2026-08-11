import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Step 5: run.py extraction — src/cli.py

def test_cli_imports():
	from src.cli import Help, parse_cli, _preparse_server_flags
	assert callable(Help)
	assert callable(parse_cli)
	assert callable(_preparse_server_flags)

def test_cli_help_prints(capsys):
	from src.cli import Help
	Help()
	out = capsys.readouterr().out
	assert "Help for AIIA" in out
	assert "--site-scripts-path" in out

def test_parse_cli_one_shot_flags():
	from config import Options
	from src.cli import parse_cli
	opt_help, opt_one, oneOpt, opt_history_lists = parse_cli(['-Y', 'hello', '-T', '0.5'], '/tmp', '/framework')
	assert opt_help is False
	assert opt_one == 'hello'
	assert opt_history_lists is False
	assert Options['QUIET'] is True
	assert Options['AI_OPTIONS']['temperature'] == 0.5

def test_parse_cli_sets_working_dir():
	from config import Options
	from src.cli import parse_cli
	Options['working_dir'] = None
	parse_cli([], '/some/cwd', '/framework')
	assert Options['working_dir'] == '/some/cwd'

def test_parse_cli_model_backend():
	from config import Options
	from src.cli import parse_cli
	parse_cli(['-m', 'gemma3:12b', '-b', 'VLLM'], '/tmp', '/framework')
	assert Options['AI_MODEL'] == 'gemma3:12b'
	assert Options['AI_BACKEND'] == 'vllm'

def test_preparse_server_flags():
	from config import Options
	from src.cli import _preparse_server_flags
	_preparse_server_flags(['-m', 'gemma3:12b', '--site-scripts-path', 'rel/x', '--quick'])
	assert Options['AI_MODEL'] == 'gemma3:12b'
	assert Options['AI_QUICK'] is True
	assert Options['SITE_SCRIPTS_PATH'].endswith('/rel/x')

def test_preparse_server_flags_persona_numeric():
	from config import Options
	from src.cli import _preparse_server_flags
	from src.PersonaResolver import _list_personas
	_preparse_server_flags(['--persona=0'])
	assert Options['INSTRUCT_CLASS'] == _list_personas()[0]
	assert Options['INSTRUCT_CLASS_OVERRIDE'] is True

# Step 5: src/FactoryReset.py

def test_factory_reset_module():
	from src.FactoryReset import _confirm_factory_reset, reset_to_factory
	assert callable(_confirm_factory_reset)
	assert callable(reset_to_factory)

def test_confirm_factory_reset_no(monkeypatch):
	from src.FactoryReset import _confirm_factory_reset
	monkeypatch.setattr('builtins.input', lambda *a, **k: 'n')
	assert _confirm_factory_reset() is False

def test_confirm_factory_reset_yes(monkeypatch):
	from src.FactoryReset import _confirm_factory_reset
	monkeypatch.setattr('builtins.input', lambda *a, **k: 'yes')
	assert _confirm_factory_reset() is True

# Step 5: src/PersonaResolver.py

def test_persona_resolver_list():
	from src.PersonaResolver import _list_personas
	personas = _list_personas()
	assert len(personas) > 0
	assert personas == sorted(personas)
	assert all(not p.endswith('.py') for p in personas)

def test_persona_resolver_resolve():
	from src.PersonaResolver import _list_personas, _resolve_persona
	personas = _list_personas()
	assert _resolve_persona('Developer') == 'Developer'
	assert _resolve_persona('0') == personas[0]
	assert _resolve_persona('99999') == '99999'

# Step 3: Commands mixins + registry

def test_commands_mixins_import():
	from src.Commands import Commands
	mro = [c.__name__ for c in Commands.__mro__]
	for name in ('CommandsConfig', 'CommandsSession', 'CommandsPersona', 'CommandsTips',
	             'CommandsTimers', 'CommandsSites', 'CommandsPlan', 'CommandsWorkers'):
		assert name in mro

def test_commands_registry_builds():
	from src.Commands import Commands
	c = Commands({'handle': None})
	assert len(c.cmds) >= 46
	for key, info in c.cmds.items():
		assert callable(info['func'])

# Step 4: ToolParser mixins

def test_toolparser_mixins_import():
	from src.ToolParser import ToolParser
	mro = [c.__name__ for c in ToolParser.__mro__]
	for name in ('ToolXmlParser', 'ToolExecutor', 'PlanToolHandler'):
		assert name in mro
	assert isinstance(ToolParser._plan_tools, set)
	assert 'listTasks' in ToolParser._plan_tools
	assert {'CreatePlan', 'CreateTask', 'AppendTask'} <= ToolParser._plan_tools


def test_plan_tool_aliases_registered():
	from src.ToolParser import ToolParser
	from src.ToolXmlParser import _PLAN_TOOLS
	aliases = ('CreatePlan', 'CreateTask', 'AppendTask')
	assert all(a in _PLAN_TOOLS for a in aliases)
	assert all(a in ToolParser._plan_tools for a in aliases)


def test_plan_tool_alias_sort_keys():
	from src.ToolExecutor import ToolExecutor
	sk = ToolExecutor._fire_sort_key
	assert sk({'name': 'CreateTask'}) == sk({'name': 'createTask'})
	assert sk({'name': 'AppendTask'}) == sk({'name': 'createTask'})
	assert sk({'name': 'CreatePlan'}) == sk({'name': 'createPlan'})


def test_plan_tool_aliases_route_to_handlers(tmp_path, monkeypatch):
	from src.PlanToolHandler import PlanToolHandler
	calls = []

	obj = PlanToolHandler.__new__(PlanToolHandler)
	obj.handle = type('H', (), {
		'Options': {'plans_path': str(tmp_path / 'plans')},
	})()
	monkeypatch.setattr(obj, '_plan_createPlan', lambda p, pl: calls.append(('createPlan', pl)) or 'ok')
	monkeypatch.setattr(obj, '_plan_createTask', lambda p, pl: calls.append(('createTask', pl)) or 'ok')
	monkeypatch.setattr(obj, '_plan_addTask', lambda p, pl: calls.append(('addTask', pl)) or 'ok')

	obj.HandlePlanTool('CreatePlan', {'title': 't', 'instructions': 'i'})
	obj.HandlePlanTool('CreateTask', {'title': 't', 'instruction': 'i'})
	obj.HandlePlanTool('AppendTask', {'title': 't', 'instruction': 'i'})
	assert calls == [
		('createPlan', str(tmp_path / 'plans')),
		('addTask', str(tmp_path / 'plans')),
		('addTask', str(tmp_path / 'plans')),
	]

def test_toolparser_known_tools():
	from src.ToolParser import ToolParser
	tp = ToolParser()
	tools = tp.get_known_tools()
	assert 'ReadFile' in tools
	assert 'WriteFile' in tools

# Step 2: Handle mixins

def test_handle_mixins_import():
	from src.Handle import Handle
	mro = [c.__name__ for c in Handle.__mro__]
	for name in ('HandleStream', 'HandleParse', 'HandleContext', 'HandleState', 'HandleChat'):
		assert name in mro

# Step 7: split-method helpers (unit tests via mixin stubs)

def test_stream_periodic_interrupt_continue():
	from src.HandleStream import HandleStream, _STREAM_CONTINUE
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_ai_interrupt = lambda: False
	state = {'response': 'x', 'thinking': '', 'native_tool_calls': []}
	assert Stub()._check_periodic_interrupt(3, state, None) is _STREAM_CONTINUE

def test_stream_periodic_interrupt_fires():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_ai_interrupt = lambda: True
	state = {'response': 'abc', 'thinking': 'th', 'native_tool_calls': ['t']}
	r = Stub()._check_periodic_interrupt(5, state, None)
	assert r['ctrl_d_interrupt'] is True and r['content'] == 'abc' and r['native_tool_calls'] == ['t']

def test_stream_process_chunk_thinking():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_stream_abort = lambda s: None
	class Msg:
		def __init__(self):
			self.thinking = 'part1'
			self.content = ''
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	assert stub._process_stream_chunk(type('C', (), {'message': Msg()})(), state, True, None) is None
	assert state['thinking'] == 'part1' and state['if_thinking'] is True

def test_stream_process_chunk_speaking_and_abort():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_stream_abort = lambda s: 'blocked' if 'WriteFile' in s else None
	class Msg:
		def __init__(self, content):
			self.thinking = ''
			self.content = content
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('hi')})(), state, True, None) is None
	assert state['response'] == 'hi'
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('<WriteFile>')})(), state, True, None) == 'blocked'

def test_parse_stream_error_too_large():
	from src.HandleParse import HandleParse, _PARSE_CONTINUE
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	r = Stub()._parse_stream_error('request body too large (413)', {'content': 'x'}, True)
	assert r['stream_too_large'] is True and r['invocations'] == []
	assert Stub()._parse_stream_error('some error', {'content': 'x'}, False) is _PARSE_CONTINUE
	assert Stub()._parse_stream_error(None, {'content': 'x'}, False) is _PARSE_CONTINUE

def test_detect_tool_invocations_merges_native_and_xml():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.hTP = __import__('src.ToolParser', fromlist=['ToolParser']).ToolParser()
		def _convert_native_tool_calls(self, native_tool_calls):
			return [{'name': c['function']['name'], 'parameters': c['function']['arguments']} for c in native_tool_calls]
	stub = Stub()
	response = {
		'content': "<createPlan><title>Hello</title><description>hi</description></createPlan>\n"
		           "<createTask><id>1</id><title>Write hello.py</title></createTask>\n"
		           "<planDone></planDone>",
		'native_tool_calls': [{'function': {'name': 'WriteFile',
		                                    'arguments': {'fileName': 'hello.py', 'contentOfFile': 'print(1)'}}}],
	}
	inv = stub._detect_tool_invocations(response)
	names = [i['name'] for i in inv]
	assert names == ['WriteFile', 'createPlan', 'createTask', 'planDone']

def test_detect_tool_invocations_dedupes_native_over_xml():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.hTP = __import__('src.ToolParser', fromlist=['ToolParser']).ToolParser()
		def _convert_native_tool_calls(self, native_tool_calls):
			return [{'name': c['function']['name'], 'parameters': c['function']['arguments']} for c in native_tool_calls]
	stub = Stub()
	response = {
		'content': "<WriteFile><fileName>dup.py</fileName><contentOfFile>xml</contentOfFile></WriteFile>",
		'native_tool_calls': [{'function': {'name': 'WriteFile',
		                                    'arguments': {'fileName': 'dup.py', 'contentOfFile': 'native'}}}],
	}
	inv = stub._detect_tool_invocations(response)
	assert len(inv) == 1
	assert inv[0]['parameters']['contentOfFile'] == 'native'

def test_fire_plan_tools_run_before_blocked_write(tmp_path):
	from src.ToolParser import ToolParser
	from src.PlanManager import PlanBase
	class LG:
		def echo(self, *a, **k): pass
	handle = type('H', (), {})()
	handle.Options = {
		'plans_path': str(tmp_path / 'plans'),
		'working_dir': str(tmp_path),
		'MODE': 'plan',
		'TOOL_ALLOWED': [],
		'TOOL_BLOCKED': [],
		'TOOL_SHOW_LOAD': False,
		'TOOL_CODE_VALIDATE': True,
		'NUM_PREDICT': None,
		'NUM_LAST_RESPONSE_TOKENS': 0,
		'AI_TOOL_PREVIEW': 0,
		'TOOL_RESULT_AS_SYSTEM': False,
		'TOOL_RESULT_AS_USER': False,
	}
	handle.hLG = LG()
	handle.Response = lambda role, content: None
	handle.tool_iteration = 0
	handle.tool_errors = 0
	handle._last_failed_tool = None
	handle._last_failed_tool_count = 0
	handle._plan_blocked_tool = None
	PlanBase.draft = None
	tp = ToolParser({'handle': handle, 'logger': None})
	invocations = [
		{'name': 'WriteFile', 'parameters': {'fileName': 'hello.py', 'contentOfFile': 'print(1)'}},
		{'name': 'createPlan', 'parameters': {'title': 'Hello', 'instructions': 'Create hello world script'}},
		{'name': 'createTask', 'parameters': {'title': 'Write hello.py', 'instruction': 'Create the script'}},
		{'name': 'planDone', 'parameters': {}},
	]
	tp.FireToolInvocation(invocations)
	assert handle._plan_blocked_tool == 'WriteFile'
	assert PlanBase.draft is not None
	assert len(PlanBase.draft.tasks) == 1
	assert any(t.status == "in_progress" for t in PlanBase.draft.tasks.values())
	PlanBase.draft = None

def test_parse_ctrl_d_saves_partial():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
	stub = Stub()
	r = stub._parse_ctrl_d({'content': 'part', 'thinking': 'th'}, False, True, True, None)
	assert r['ctrl_d_interrupt'] is True
	assert stub.responses[0][0] == 'assistant' and stub.responses[0][1]['content'] == 'part'

def test_parse_repeated_return_object():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		pass
	r = Stub()._parse_repeated({'content': 'again'}, True, None)
	assert r['invocations'] == [] and r['response'] == 'again'

def test_parse_early_abort_fires_complete_invocations():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': 'plan'}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.fired = None
			self.history_called = False
			self.inv = [{'name': 'GetTip', 'parameters': {'title': 'instruct_developer'}}]
		def _detect_tool_invocations(self, response):
			return self.inv
		def _parse_assistant_history(self, response, tool_invocations, opt_skip_history, color):
			self.history_called = True
			self.Response('assistant', {'content': response['content']})
		def _fire_tool_invocations(self, tool_invocations, response, opt_stream_cb, stream_error):
			self.fired = tool_invocations
			return {'invocations': tool_invocations, 'response': response['content'],
					'job_done': False, 'stream_error': stream_error}
	stub = Stub()
	response = {
		'content': "<GetTip><title>instruct_developer</title></GetTip>\n<WriteFile>",
		'thinking': 'th',
	}
	r = stub._parse_early_abort(response, False, True, True, None,
		"'WriteFile' cannot be used in PLAN mode")
	assert stub.history_called is True
	assert stub.fired is not None and stub.fired[0]['name'] == 'GetTip'
	assert r['plan_blocked'] == 'WriteFile'
	assert r['invocations'][0]['name'] == 'GetTip'

def test_parse_early_abort_no_invocations_keeps_old_path():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': 'plan'}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.fired = None
		def _detect_tool_invocations(self, response):
			return []
	stub = Stub()
	response = {'content': 'plain text <WriteFile', 'thinking': 'th'}
	r = stub._parse_early_abort(response, False, True, True, None,
		"'WriteFile' cannot be used in PLAN mode")
	assert stub.fired is None
	assert stub.responses[0][0] == 'assistant'
	assert r['invocations'] == []
	assert r['plan_blocked'] == 'WriteFile'

def test_context_collect_drop_indices():
	from src.HandleContext import HandleContext
	msgs = [{'role': 'system', 'content': 'S'}]
	for i in range(8):
		msgs.append({'role': 'user', 'content': 'u{}'.format(i)})
		msgs.append({'role': 'assistant', 'content': 'a{}'.format(i)})
	msgs, idx = HandleContext.__new__(HandleContext)._collect_drop_indices(msgs)
	assert msgs[0]['role'] == 'system'
	assert len(idx) == 6  # first 3 exchanges dropped (last 5 kept)
	assert idx[0] == 1
	assert all(m['role'] for m in msgs)

def test_context_collect_drop_indices_malformed():
	from src.HandleContext import HandleContext
	msgs, idx = HandleContext.__new__(HandleContext)._collect_drop_indices([{'bad': 1}, {'role': 'user', 'content': 'x'}])
	assert len(msgs) == 1 and len(idx) == 0

def test_context_insert_summary():
	from src.HandleContext import HandleContext
	from src.PlanManager import PlanBase
	PlanBase.draft = None
	obj = HandleContext.__new__(HandleContext)
	obj.Options = {'AI_SESS_ID': 's1', 'AI_ROW_ID': 5}
	msgs = [{'role': 'system', 'content': 'S1'}, {'role': 'user', 'content': 'u'}]
	new = obj._insert_summary(msgs, {0, 1}, 'SUM')
	assert new[1]['role'] == 'system' and new[1]['content'] == '[Context summary: SUM]'
	assert new[1]['rowId'] == 6

def test_context_request_summary_truncates():
	from src.HandleContext import HandleContext
	class Backend:
		def chat(self, **kw):
			class R: message = type('M', (), {'content': 'A' * 4000})()
			return R()
	class Stub(HandleContext):
		def __init__(self):
			self.Options = {'AI_MODEL': 'm'}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._get_backend = lambda: Backend()
	summary = Stub()._request_summary('p')
	assert len(summary) == 3001 and summary.endswith('…')

def test_handle_build_response_obj():
	from src.Handle import Handle
	obj = Handle.__new__(Handle)
	obj.Options = {'AI_SESS_ID': 's9', 'AI_ROW_ID': 3, 'AI_VISION_ENABLED': True}
	r = obj._build_response_obj('user', 'hi', None, 'toolA', ['AAA'], None)
	assert r['role'] == 'user' and r['content'] == 'hi' and r['name'] == 'toolA'
	assert r['sessionId'] == 's9' and r['rowId'] == 3 and 'timestamp' in r and 'date' in r
	assert r['images'] == ['AAA']

def test_handle_embed_token_counts():
	from src.Handle import Handle
	obj = Handle.__new__(Handle)
	obj.Options = {'NUM_PROMPT_TOKENS': 0, 'NUM_RESPONSE_TOKENS': 0,
		'NUM_LAST_PROMPT_TOKENS': 0, 'NUM_LAST_RESPONSE_TOKENS': 0}
	obj._write_state = lambda d: None
	obj.bg_log = lambda *a, **k: None
	r = {}
	obj._embed_token_counts(r, {'prompt_tokens': 10, 'response_tokens': 20})
	assert r['prompt_tokens'] == 10 and r['response_tokens'] == 20
	assert obj.Options['NUM_PROMPT_TOKENS'] == 10 and obj.Options['NUM_RESPONSE_TOKENS'] == 20

def test_tool_executor_fire_sort_key():
	from src.ToolExecutor import ToolExecutor
	sk = ToolExecutor._fire_sort_key
	assert sk({'name': 'createPlan'}) == -2
	assert sk({'name': 'addTask'}) == -1
	assert sk({'name': 'ReadFile'}) == 0

def test_tool_executor_guard_file_size():
	from src.ToolExecutor import ToolExecutor
	class Handle:
		def __init__(self):
			self.Options = {'AI_MAX_FILE_SIZE': 100}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
	obj = ToolExecutor.__new__(ToolExecutor)
	obj.handle = Handle()
	err = obj._guard_file_size('WriteFile', {'fileName': 'x', 'contentOfFile': 'z' * 200})
	assert err is not None and 'AI_MAX_FILE_SIZE' in err
	assert obj._guard_file_size('ReadFile', {}) is None


def _echo_capture_tool_executor(preview_value, options=None):
	from src.ToolExecutor import ToolExecutor
	opts = {'AI_TOOL_PREVIEW': preview_value}
	if options:
		opts.update(options)
	captured = {}

	class LG:
		def echo(self, text, echo_opts=None):
			captured['text'] = text
			captured['opts'] = echo_opts or {}

	class Handle:
		def __init__(self):
			self.Options = opts
			self.hLG = LG()

	obj = ToolExecutor.__new__(ToolExecutor)
	obj.handle = Handle()
	return obj, captured


def test_tool_preview_on_shows_success_to_user():
	obj, cap = _echo_capture_tool_executor(1)
	obj._fire_echo_result('ReadFile', 'file content')
	assert 'ReadFile' in cap['text']
	assert cap['opts']['debugOnly'] is False


def test_tool_preview_off_hides_success_from_user():
	obj, cap = _echo_capture_tool_executor(0)
	obj._fire_echo_result('ReadFile', 'file content')
	# debugOnly unset -> Log.echo() defaults it to True (DEBUG-only)
	assert 'debugOnly' not in cap['opts']


def test_tool_preview_error_always_shown():
	obj, cap = _echo_capture_tool_executor(0)
	obj._fire_echo_result('Terminal', 'Error: command failed')
	assert cap['opts']['debugOnly'] is False
	obj, cap = _echo_capture_tool_executor(1)
	obj._fire_echo_result('Terminal', 'Warning: unusual output')
	assert cap['opts']['debugOnly'] is False


def test_tool_preview_keeps_truncation():
	obj, cap = _echo_capture_tool_executor(1)
	obj._fire_echo_result('ReadFile', 'x' * 2000)
	assert len(cap['text']) < 600
	assert 'truncated' in cap['text']

def test_history_manager_choose_search(monkeypatch):
	from src.HistoryManager import HistoryManager
	obj = HistoryManager.__new__(HistoryManager)
	obj.handle = type('H', (), {
		'hLG': type('LG', (), {'echo': lambda *a, **k: None})(),
	})()
	obj.available = ['a1_1.dbk']
	obj.history = ''
	obj._search = lambda q: [{'filename': 'a1_1.dbk', 'index': 0, 'date': 'd', 'preview': 'p'}] if q == 'foo' else []
	obj._show_list = lambda items, names: None
	obj._view_file = lambda *a: None
	obj.msgs = []
	obj.Get = lambda: obj.msgs.append(obj.history)
	inputs = iter(['0'])
	monkeypatch.setattr('src.HistoryManager.user_input', lambda: next(inputs, None))
	assert obj._choose_search('s foo', {}) is True
	assert obj.history == 'a1_1.dbk'

def test_history_manager_choose_search_no_match(monkeypatch):
	from src.HistoryManager import HistoryManager
	obj = HistoryManager.__new__(HistoryManager)
	obj.handle = type('H', (), {
		'hLG': type('LG', (), {'echo': lambda *a, **k: None})(),
	})()
	obj.available = ['a1_1.dbk']
	obj._search = lambda q: []
	obj._show_list = lambda items, names: None
	obj._view_file = lambda *a: None
	assert obj._choose_search('s nope', {}) is False

def test_model_registry_known_model():
	from src.ModelRegistry import apply
	opts = {'AI_THINK': False, 'AI_VISION_ENABLED': False}
	changes = apply(opts, 'kimi-k2.5:cloud')
	assert opts['AI_THINK'] is True
	assert any('Thinking' in c for c in changes)

def test_model_registry_qwen25_coder_known():
	from src.ModelRegistry import apply
	opts = {'AI_THINK': False, 'AI_VISION_ENABLED': False}
	changes = apply(opts, 'w4d4f4k/qwen25-coder-aiia-v2:latest')
	assert opts['AI_THINK'] is True
	assert opts['AI_CONTEXT_LIMIT'] == 32768
	assert opts['AI_OPTIONS']['num_ctx'] == 32768
	assert opts['NUM_PREDICT'] == 16384
	assert any('Context' in c for c in changes)

def test_model_registry_unknown_model_resets_stale_flags():
	from src.ModelRegistry import apply
	opts = {'AI_THINK': True, 'AI_VISION_ENABLED': True}
	changes = apply(opts, 'custom/unknown-coder:latest')
	assert opts['AI_THINK'] is False
	assert opts['AI_VISION_ENABLED'] is False
	assert any('unknown model' in c for c in changes)

def test_model_registry_unknown_model_conservative_context():
	from src.ModelRegistry import apply
	opts = {'AI_THINK': False, 'AI_VISION_ENABLED': False}
	changes = apply(opts, 'some-unknown-model:latest')
	assert opts['AI_OPTIONS']['num_ctx'] == 16384
	assert opts['AI_CONTEXT_LIMIT'] == 16384
	assert any('conservative default' in c for c in changes)

def test_model_registry_unknown_cloud_model_no_context_change():
	from src.ModelRegistry import apply
	opts = {'AI_THINK': False, 'AI_VISION_ENABLED': False}
	changes = apply(opts, 'some-provider/model:cloud')
	assert 'AI_OPTIONS' not in opts
	assert any('conservative default' in c for c in changes) is False

def test_chat_params_think_disabled_in_build_mode():
	from src.HandleChat import HandleChat
	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'AI_OPTIONS': {},
				'AI_MODEL': 'm',
				'AI_THINK': True,
				'BUILD_THINKING_DISABLED': True,
				'MODE': 'build',
			}
	r = Stub()._build_chat_params([{'role': 'user', 'content': 'hi'}])
	assert 'think' not in r

def test_chat_params_think_kept_when_build_thinking_enabled():
	from src.HandleChat import HandleChat
	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'AI_OPTIONS': {},
				'AI_MODEL': 'm',
				'AI_THINK': True,
				'BUILD_THINKING_DISABLED': False,
				'MODE': 'build',
			}
	r = Stub()._build_chat_params([{'role': 'user', 'content': 'hi'}])
	assert r['think'] is True

def test_chat_params_think_kept_in_plan_mode_even_when_disabled():
	from src.HandleChat import HandleChat
	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'AI_OPTIONS': {},
				'AI_MODEL': 'm',
				'AI_THINK': True,
				'BUILD_THINKING_DISABLED': True,
				'MODE': 'plan',
			}
	r = Stub()._build_chat_params([{'role': 'user', 'content': 'hi'}])
	assert r['think'] is True

def test_ph_crc32_same_content_same_hash():
	from src.CommandsSession import _ph_crc32
	assert _ph_crc32('hello') == _ph_crc32('hello')
	assert _ph_crc32('hello') != _ph_crc32('hello ')
	assert len(_ph_crc32('x')) == 8

def test_ph_crc32_matches_zlib():
	import zlib
	from src.CommandsSession import _ph_crc32
	for s in ('', 'test', 'some longer content\nwith newline'):
		assert _ph_crc32(s) == '{:08x}'.format(zlib.crc32(s.encode('utf-8')))

def test_write_state_deep_merges_config(tmp_path):
	from src.HandleState import HandleState
	class Stub(HandleState):
		def __init__(self):
			self.Options = {'AI_FILE_STATE': str(tmp_path / 'state.aiia')}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub = Stub()
	stub._write_state({'config': {'AI_INSTRUCT_OPTION': 2}})
	stub._write_state({'config': {'NUM_PREDICT': 8192}})
	stub._write_state({'mode': 'build'})
	import json, os
	state = json.loads(open(str(tmp_path / 'state.aiia')).read())
	assert state['config'] == {'AI_INSTRUCT_OPTION': 2, 'NUM_PREDICT': 8192}
	assert state['mode'] == 'build'

def test_restore_config_overrides(tmp_path):
	from src.HandleState import HandleState
	class Stub(HandleState):
		def __init__(self):
			self.Options = {'AI_FILE_STATE': str(tmp_path / 'state.aiia'), 'AI_OPTIONS': {'num_ctx': 4096}}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub = Stub()
	stub._write_state({'config': {'AI_INSTRUCT_OPTION': 2, 'AI_OPTIONS': {'temperature': 0.8}}})
	stub._restore_config_overrides(stub._read_state())
	assert stub.Options['AI_INSTRUCT_OPTION'] == 2
	assert stub.Options['AI_OPTIONS'] == {'num_ctx': 4096, 'temperature': 0.8}

def test_ai_interrupt_menu_choice2_marks_user_stop(monkeypatch):
	from src.HandleChat import HandleChat
	class Stub(HandleChat):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub = Stub()
	monkeypatch.setattr('src.HandleChat.user_input', lambda *a, **k: '2')
	assert stub._show_ai_interrupt_menu() == 2
	assert stub._ai_stopped_by_user is True

def test_ai_interrupt_menu_choice3_does_not_mark_user_stop(monkeypatch):
	from src.HandleChat import HandleChat
	class Stub(HandleChat):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub = Stub()
	monkeypatch.setattr('src.HandleChat.user_input', lambda *a, **k: '3')
	assert stub._show_ai_interrupt_menu() == 3
	assert not hasattr(stub, '_ai_stopped_by_user')

# --- think-block streaming & stripping (buffer-until-close rule) ---

def test_split_content_think_basic():
	from src.HandleStream import HandleStream
	stub = HandleStream.__new__(HandleStream)
	state = {}
	answer, thinking = stub._split_content_think('hi<think>secret</think>bye', state)
	assert answer == 'hibye' and thinking == 'secret'


def test_split_content_think_nested_open_is_data():
	from src.HandleStream import HandleStream
	stub = HandleStream.__new__(HandleStream)
	state = {}
	answer, thinking = stub._split_content_think('<think>a<think>b</think>c', state)
	# Only </think> stops the buffer; the nested <think> is just data
	assert answer == 'c' and thinking == 'ab'


def test_split_content_think_across_chunks():
	from src.HandleStream import HandleStream
	stub = HandleStream.__new__(HandleStream)
	state = {}
	a1, t1 = stub._split_content_think('<think>abc', state)
	assert a1 == '' and t1 == '' and state['_in_think'] is True
	a2, t2 = stub._split_content_think('def</think>ghi', state)
	assert a2 == 'ghi' and t2 == 'abcdef' and state['_in_think'] is False


def test_split_content_think_orphan_close_dropped():
	from src.HandleStream import HandleStream
	stub = HandleStream.__new__(HandleStream)
	state = {}
	answer, thinking = stub._split_content_think('text</think>more', state)
	assert answer == 'textmore' and thinking == ''


def test_split_content_think_unclosed_flushed_at_end():
	from src.HandleStream import HandleStream
	stub = HandleStream.__new__(HandleStream)
	state = {'_in_think': True, '_think_pending': 'partial'}
	stub._flush_think_buffer(state)
	assert state['thinking'] == 'partial' and state['_think_pending'] == ''


def test_stream_process_chunk_content_think_split():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_stream_abort = lambda s: None
	class Msg:
		def __init__(self, content):
			self.thinking = ''
			self.content = content
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('think: <think>secret</think> answer')})(), state, True, None) is None
	assert state['response'] == 'think:  answer'
	assert state['thinking'] == 'secret'


def test_strip_think_tags_robust():
	from src.HandleParse import HandleParse
	stub = HandleParse.__new__(HandleParse)
	r = {'content': 'a<think>one</think>b'}
	stub._strip_think_tags(r)
	assert r['content'] == 'ab'
	# case-insensitive + attributes
	r = {'content': 'a<Think mode="x">two</THINK>b'}
	stub._strip_think_tags(r)
	assert r['content'] == 'ab'
	# nested open is data, only close stops
	r = {'content': 'a<think>x<think>y</think>b'}
	stub._strip_think_tags(r)
	assert r['content'] == 'ab'
	# orphan close
	r = {'content': 'a</think>b'}
	stub._strip_think_tags(r)
	assert r['content'] == 'ab'
	# unclosed at end strips remainder
	r = {'content': 'a<think>rest of thinking here'}
	stub._strip_think_tags(r)
	assert r['content'] == 'a'


def test_parse_ignores_think_blocks():
	from src.ToolXmlParser import ToolXmlParser
	tp = ToolXmlParser()
	inv = tp.ParseTextToolInvocation('<think>let me plan</think><listTools/>')
	assert inv == [{'name': 'listTools', 'parameters': {}}]
	# nested/unclosed think must not be treated as a tool
	inv = tp.ParseTextToolInvocation('<think>a<think>b</think><WriteFile/>')
	assert inv == [{'name': 'WriteFile', 'parameters': {}}]


def test_log_gray_color_emits_ansi():
	from src.Log import Log
	log = Log.__new__(Log)
	log.hSpeak = None
	log.debug = False
	log.streamData = ''
	log.CRED = '\033[1;31m'
	log.CGREEN = '\033[1;32m'
	log.CORANGE = '\033[1;33m'
	log.CGRAY = '\033[90m'
	log.CNC = '\033[0m'
	import io, contextlib
	buf = io.StringIO()
	with contextlib.redirect_stdout(buf):
		log._echo_print('', {'color': True, 'colorValue': 'gray', 'returnStream': False, 'speak': False, 'end': '', 'flush': True})
	assert buf.getvalue() == '\033[90m\033[0m'


def test_readfile_line_numbers_default_off():
	import tempfile
	from tools.tool_ReadFile import ReadFile
	tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
	tf.write("line one\nline two\nline three\n")
	tf.close()
	rf = ReadFile()
	out = rf.run(tf.name)
	assert out == "line one\nline two\nline three\n"


def test_readfile_line_numbers_on():
	import tempfile
	from tools.tool_ReadFile import ReadFile
	tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
	tf.write("line one\nline two\nline three\n")
	tf.close()
	rf = ReadFile()
	out = rf.run(tf.name, lineNumbers='True')
	assert out == "1: line one\n2: line two\n3: line three\n"


def test_readfile_line_numbers_with_lines():
	import tempfile
	from tools.tool_ReadFile import ReadFile
	tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
	tf.write("line one\nline two\nline three\nline four\n")
	tf.close()
	rf = ReadFile()
	out = rf.run(tf.name, lines='2', lineNumbers='True')
	assert out.startswith("1: line one\n2: line two")
	assert "Lines truncated" in out


def test_readfile_line_numbers_with_offset():
	import tempfile
	from tools.tool_ReadFile import ReadFile
	tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
	tf.write("line one\nline two\nline three\nline four\n")
	tf.close()
	rf = ReadFile()
	offset = len("line one\nline two\n")
	out = rf.run(tf.name, offset=str(offset), lineNumbers='True')
	assert out == "3: line three\n4: line four\n"


def test_stream_think_limit_native():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'AI_THINK_LIMIT': 10, 'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	class Msg:
		def __init__(self, thinking):
			self.thinking = thinking
			self.content = ''
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('1234567890')})(), state, True, None) is None
	assert state['thinking'] == '1234567890'
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('x')})(), state, True, None) == 'think_limit'


def test_stream_think_limit_content_tag():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'AI_THINK_LIMIT': 8, 'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_stream_abort = lambda s: None
	class Msg:
		def __init__(self, content):
			self.thinking = ''
			self.content = content
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	# First chunk opens an unclosed <think> block — thinking is buffered, not counted yet
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('<think>hello')})(), state, True, None) is None
	assert state['thinking'] == ''
	# Second chunk closes the block; total thinking "hello world" (11 chars) exceeds limit 8
	assert stub._process_stream_chunk(type('C', (), {'message': Msg(' world</think>')})(), state, True, None) == 'think_limit'
	assert state['thinking'] == 'hello world'


def test_stream_content_limit():
	from src.HandleStream import HandleStream
	class Stub(HandleStream):
		def __init__(self):
			self.Options = {'AI_MAX_CONTENT_LEN': 10, 'BUILD_THINKING_DISABLED': True}
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._check_stream_abort = lambda s: None
	class Msg:
		def __init__(self, content):
			self.thinking = ''
			self.content = content
			self.tool_calls = []
	stub = Stub()
	state = {'response': '', 'thinking': '', 'native_tool_calls': [], 'if_thinking': False, 'if_speaking': False}
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('1234567890')})(), state, True, None) is None
	assert state['response'] == '1234567890'
	assert stub._process_stream_chunk(type('C', (), {'message': Msg('x')})(), state, True, None) == 'content_limit'


def test_parse_limit_abort_think():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'AI_THINK_LIMIT': 10}
			self.responses = []
		def Response(self, role, content):
			self.responses.append((role, content))
	stub = Stub()
	r = stub._parse_limit_abort({'content': 'ans', 'thinking': 'th'}, False, True, True, None, 'think_limit')
	assert r['think_limit'] is True
	assert r['invocations'] == []
	assert stub.responses[0][0] == 'assistant'
	assert stub.responses[1][0] == 'user'
	assert 'AI_THINK_LIMIT' in stub.responses[1][1]['content']


def test_parse_limit_abort_content():
	from src.HandleParse import HandleParse
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'AI_MAX_CONTENT_LEN': 20}
			self.responses = []
		def Response(self, role, content):
			self.responses.append((role, content))
	stub = Stub()
	r = stub._parse_limit_abort({'content': 'ans', 'thinking': ''}, False, True, True, None, 'content_limit')
	assert r['content_limit'] is True
	assert r['invocations'] == []
	assert stub.responses[0][0] == 'assistant'
	assert stub.responses[1][0] == 'user'
	assert 'AI_MAX_CONTENT_LEN' in stub.responses[1][1]['content']


def test_parse_fire_plan_done_system_message(tmp_path):
	from src.HandleParse import HandleParse
	from src.PlanManager import PlanBase, Plan
	class MockTP:
		def FireToolInvocation(self, invocations):
			return "PLAN_DONE|Task 1/1|Build the game"
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': 'plan', 'plans_path': str(tmp_path / 'plans')}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hTP = MockTP()
			self._write_current_task = lambda: None
	PlanBase.draft = Plan('test')
	PlanBase.draft.createTask('Build the game', 'Build game')
	stub = Stub()
	r = stub._fire_tool_invocations([{'name': 'planDone', 'parameters': {}}], {'content': 'ok'}, None, None)
	assert r['plan_done'] is True
	assert stub.responses[-1][0] == 'system'
	assert 'Plan is ready' in stub.responses[-1][1]['content']
	PlanBase.draft = None


def test_plan_planDone_refused_when_build_started(tmp_path):
	from src.PlanToolHandler import PlanToolHandler
	from src.PlanManager import PlanBase, Plan
	obj = PlanToolHandler.__new__(PlanToolHandler)
	obj.handle = type('H', (), {'Options': {'plans_path': str(tmp_path / 'plans')}})()
	PlanBase.draft = Plan('test')
	PlanBase.draft.createTask('Build the game', 'Build game')
	# Simulate build already started
	for t in PlanBase.draft.tasks.values():
		t.status = 'in_progress'
	result = obj._plan_planDone({}, str(tmp_path / 'plans'))
	assert not result.startswith('PLAN_DONE|')
	assert 'Build already started' in result
	PlanBase.draft = None


def test_parse_fire_plan_done_refused_when_build_started(tmp_path):
	from src.HandleParse import HandleParse
	from src.PlanManager import PlanBase, Plan
	class MockTP:
		def FireToolInvocation(self, invocations):
			return "Build already started — use <nextTask>completed</nextTask> to advance..."
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': 'build', 'plans_path': str(tmp_path / 'plans')}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hTP = MockTP()
			self._write_current_task = lambda: None
	PlanBase.draft = Plan('test')
	PlanBase.draft.createTask('Build the game', 'Build game')
	PlanBase.draft.tasks[list(PlanBase.draft.tasks.keys())[0]].status = 'in_progress'
	stub = Stub()
	r = stub._fire_tool_invocations([{'name': 'planDone', 'parameters': {}}], {'content': 'ok'}, None, None)
	assert r['plan_done'] is False
	assert not any(role == 'system' and 'Plan is ready' in content for role, content in stub.responses)
	PlanBase.draft = None


def test_parse_fire_start_build_system_message(tmp_path):
	from src.HandleParse import HandleParse
	from src.PlanManager import PlanBase, Plan
	class MockTP:
		def FireToolInvocation(self, invocations):
			return "START_BUILD|Task 1/1|Build the game"
	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': 'build', 'plans_path': str(tmp_path / 'plans')}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hTP = MockTP()
			self._write_current_task = lambda: None
	PlanBase.draft = Plan('test')
	PlanBase.draft.createTask('Build the game', 'Build game')
	stub = Stub()
	r = stub._fire_tool_invocations([{'name': 'startBuild', 'parameters': {}}], {'content': 'ok'}, None, None)
	assert stub.responses[-1][0] == 'system'
	assert 'Mode changed to BUILD' in stub.responses[-1][1]['content']
	PlanBase.draft = None


def test_start_build_command_injects_system_message(tmp_path):
	from src.HandleChat import HandleChat
	from src.PlanManager import PlanBase, Plan
	class Stub(HandleChat):
		def __init__(self):
			self.Options = {'plans_path': str(tmp_path / 'plans'), 'MODE': 'build'}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._write_current_task = lambda: None
		def _ensure_plan_loaded(self, plan_id=None):
			return True
		def _find_first_task(self):
			if PlanBase.draft:
				for t in PlanBase.draft.tasks.values():
					return t
			return None
	PlanBase.draft = Plan('test')
	PlanBase.draft.createTask('Build the game', 'Build game')
	stub = Stub()
	stub.StartBuild()
	assert stub.responses[-1][0] == 'system'
	assert 'Mode changed to BUILD' in stub.responses[-1][1]['content']
	PlanBase.draft = None


def test_start_build_command_no_tasks_system_message(tmp_path):
	from src.HandleChat import HandleChat
	from src.PlanManager import PlanBase, Plan
	class Stub(HandleChat):
		def __init__(self):
			self.Options = {'plans_path': str(tmp_path / 'plans'), 'MODE': 'build'}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._write_current_task = lambda: None
		def _ensure_plan_loaded(self, plan_id=None):
			return True
		def _find_first_task(self):
			return None
	PlanBase.draft = Plan('test')
	stub = Stub()
	stub.StartBuild()
	assert stub.responses[-1][0] == 'system'
	assert 'All tasks in the plan are completed' in stub.responses[-1][1]['content']
	PlanBase.draft = None


def test_toolexecutor_lowercase_createfile_loads():
	"""Regression: initmodule() returns False when the first class name does not
	exist. The old code only checked `if h is None`, so False was treated as a
	valid handle and then `_execute_tool_call` failed with 'bool' object has no
	attribute 'run'. The fix checks `if not h:` and falls back to the case-insensitive
	class scan, which finds the real CreateFile tool."""
	import os, tempfile, sys
	from src.ToolExecutor import ToolExecutor
	class FakeLG:
		def echo(self, msg, opts=None):
			pass
	class FakeTC:
		def __init__(self):
			self.handles = {}
	class FakeHandle:
		def __init__(self, tools_path):
			self.Options = {'tools_path': tools_path, 'MODE': 'build'}
			self.hTC = FakeTC()
			self.hLG = FakeLG()
	# Use the real tools/ directory but write output into a temp workout dir
	real_tools = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')
	with tempfile.TemporaryDirectory() as tmp:
		if real_tools not in sys.path:
			sys.path.insert(0, real_tools)
		out_path = os.path.join(tmp, 'out.txt')
		obj = ToolExecutor.__new__(ToolExecutor)
		handle = FakeHandle(real_tools)
		obj.handle = handle
		res = obj.ExecuteTextTool('createFile', {'fileName': out_path, 'contentOfFile': 'hello'})
		assert res.startswith('File {} created successfully'.format(out_path))
		assert open(out_path).read() == 'hello'
