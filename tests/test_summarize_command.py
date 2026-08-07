import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FakeTipManager:
	def __init__(self):
		self.cleared = False

	def clear_all_caches(self):
		self.cleared = True


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeHandle:
	"""Fake handle with a minimal _auto_clear (keeps system msgs only)."""

	def __init__(self):
		self.hLG = FakeLogger()
		self.hTM = FakeTipManager()
		self._consumed_tips = {'instruct_developer', 'tool_reference_build'}
		self.Options = {'AI_ROW_ID': 0}
		self._auto_clear_calls = 0
		self.hHM = type('H', (), {})()
		self.hHM.msgs = [
			{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
			{'role': 'user', 'content': 'check the network config', 'name': ''},
			{'role': 'assistant', 'content': 'I will read fw.sh', 'name': ''},
			{'role': 'tool', 'content': '=== nftables ruleset ===', 'name': 'Terminal'},
		]

	def _auto_clear(self):
		self._auto_clear_calls += 1
		self.hHM.msgs = [m for m in self.hHM.msgs if m.get('role') == 'system']
		self.Options['AI_ROW_ID'] = 0

	def Response(self, role, opts):
		msg = {'role': role, 'content': opts['content']}
		self.hHM.msgs.append(msg)
		self.Options['AI_ROW_ID'] += 1


def _make():
	from src.Commands import Commands
	fake = FakeHandle()
	c = Commands({'handle': fake})
	return c, fake


def test_summarize_registered():
	c, _ = _make()
	assert 'SUMMARIZE' in c.cmds
	info = c.cmds['SUMMARIZE']
	assert info['regex'] == r'^!SUMMARIZE$'
	assert info['func'] == c.CMD_SUMMARIZE
	assert info['usage'] == '!SUMMARIZE'


def test_summarize_clears_to_system_and_resets_tools():
	c, fake = _make()
	ret = c.CMD_SUMMARIZE('!SUMMARIZE')
	assert fake._auto_clear_calls == 1
	assert fake.hTM.cleared
	assert fake._consumed_tips == set()
	assert ret == 0
	# Only system messages remain, plus the injected warm-up user message
	roles = [m['role'] for m in fake.hHM.msgs]
	assert roles == ['system', 'user']


def test_summarize_injects_warmup_message():
	c, fake = _make()
	c.CMD_SUMMARIZE('!SUMMARIZE')
	last = fake.hHM.msgs[-1]
	assert last['role'] == 'user'
	assert '[Context Summarized]' in last['content']
	assert '<listTools>' in last['content']
	assert '<GetTip>' in last['content']
	assert '<ReinsertTip>' in last['content']


def test_summarize_help_output_contains(capsys):
	c, fake = _make()
	c.CMD_HELP()
	out = capsys.readouterr().out
	assert 'Summarize' in out
	assert '!SUMMARIZE' in out
