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
