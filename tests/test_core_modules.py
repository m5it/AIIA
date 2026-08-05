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
