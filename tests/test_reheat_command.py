import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FakeTipManager:
	def clear_all_caches(self):
		self.cleared = True


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeHandle:
	def __init__(self):
		self.hTM = FakeTipManager()
		self.hLG = FakeLogger()
		self._consumed_tips = {'instruct_Developer', 'tool_reference_build'}
		self.msgs = []
		self.Options = {}

	def Response(self, role, content_dict):
		self.msgs.append((role, content_dict['content']))


def _make():
	from src.Commands import Commands
	fake = FakeHandle()
	c = Commands({'handle': fake})
	return c, fake


def test_reheat_registered():
	c, _ = _make()
	assert 'REHEAT' in c.cmds
	info = c.cmds['REHEAT']
	assert info['regex'] == r'^!REHEAT$'
	assert info['func'] == c.CMD_REHEAT
	assert info['usage'] == '!REHEAT'


def test_reheat_clears_caches_and_consumed_tips():
	c, fake = _make()
	ret = c.CMD_REHEAT('!REHEAT')
	assert fake.hTM.cleared
	assert fake._consumed_tips == set()
	assert ret == 0


def test_reheat_injects_warmup_message():
	c, fake = _make()
	c.CMD_REHEAT('!REHEAT')
	assert len(fake.msgs) == 1
	role, content = fake.msgs[0]
	assert role == 'user'
	assert '[Tool Reheat Session]' in content
	assert '<listTools>' in content
	assert '<GetTip>' in content


def test_reheat_help_output_contains(capsys):
	c, fake = _make()
	c.CMD_HELP()
	out = capsys.readouterr().out
	assert 'Reheat' in out
	assert '!REHEAT' in out
