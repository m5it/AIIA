import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


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

	def _auto_clear(self, sys_msg=None):
		self._auto_clear_calls += 1
		self.hHM.msgs = [m for m in self.hHM.msgs if m.get('role') == 'system']
		self.Options['AI_ROW_ID'] = 0
		if sys_msg:
			self.Response('system', {'content': sys_msg})

	def Response(self, role, opts):
		msg = {'role': role, 'content': opts['content']}
		self.hHM.msgs.append(msg)
		self.Options['AI_ROW_ID'] += 1


def _make():
	from src.Commands import Commands
	fake = FakeHandle()
	c = Commands({'handle': fake})
	return c, fake


@pytest.fixture(autouse=True)
def _clean_draft():
	from src.PlanManager import PlanBase
	PlanBase.draft = None
	yield
	PlanBase.draft = None


def _make_stub(tmp_path):
	from src.HandleContext import HandleContext

	class Stub(HandleContext):
		def __init__(self):
			self.hLG = FakeLogger()
			self.hHM = type('H', (), {})()
			self.hHM.msgs = [
				{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
				{'role': 'user', 'content': 'check the network config', 'name': ''},
				{'role': 'assistant', 'content': 'ok', 'name': ''},
			]
			self.Options = {
				'AI_ROW_ID': 0,
				'AI_SESS_ID': 'sess-test',
				'plans_path': str(tmp_path / 'plans'),
			}
			self.injected = []

		def _archive_history(self, label):
			return None

		def _save_clear_tip(self, *a, **k):
			pass

		def _rewrite_history(self, msgs):
			self.hHM.msgs = list(msgs)

		def Response(self, role, opts):
			self.hHM.msgs.append({'role': role, 'content': opts['content']})
			self.injected.append((role, opts['content']))

	return Stub()


def _sample_plan():
	from src.PlanManager import Plan
	plan = Plan('p1', 'Deploy Fix', 'Finish the deployment fix')
	plan.createTask('Write the regression test', title='Write test')
	return plan


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
	# Only system messages remain, plus the single injected warm-up system message
	roles = [m['role'] for m in fake.hHM.msgs]
	assert roles == ['system', 'system']


def test_summarize_injects_single_system_message():
	c, fake = _make()
	c.CMD_SUMMARIZE('!SUMMARIZE')
	sys_msgs = [m for m in fake.hHM.msgs if m['role'] == 'system']
	assert len(sys_msgs) == 2  # original system message + exactly one injected
	last = fake.hHM.msgs[-1]
	assert last['role'] == 'system'
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


def test_auto_clear_without_plan_injects_nothing(tmp_path):
	stub = _make_stub(tmp_path)
	stub._auto_clear()
	assert stub.injected == []
	assert all(m['role'] == 'system' for m in stub.hHM.msgs)
	assert len(stub.hHM.msgs) == 1


def test_auto_clear_with_plan_injects_single_system(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	PlanBase.draft = _sample_plan()
	stub._auto_clear()
	assert len(stub.injected) == 1
	role, content = stub.injected[0]
	assert role == 'system'
	assert '[ACTIVE PLAN]' in content
	assert 'Deploy Fix' in content
	assert all(m['role'] == 'system' for m in stub.hHM.msgs)


def test_auto_clear_sys_msg_with_plan(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	PlanBase.draft = _sample_plan()
	stub._auto_clear(sys_msg='[Context Summarized]\nWarm up')
	assert len(stub.injected) == 1
	role, content = stub.injected[0]
	assert role == 'system'
	assert '[Context Summarized]' in content
	assert '[ACTIVE PLAN]' in content
	assert 'Deploy Fix' in content


def test_auto_clear_sys_msg_no_plan(tmp_path):
	stub = _make_stub(tmp_path)
	stub._auto_clear(sys_msg='[Context Summarized]\nWarm up')
	assert len(stub.injected) == 1
	assert stub.injected[0][0] == 'system'
	assert stub.injected[0][1] == '[Context Summarized]\nWarm up'
	assert '[ACTIVE PLAN]' not in stub.injected[0][1]


def test_active_plan_text_uses_draft(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	PlanBase.draft = _sample_plan()
	assert 'Deploy Fix' in stub._active_plan_text()
	assert 'Write test' in stub._active_plan_text()


def test_active_plan_text_disk_fallback(tmp_path):
	from src.PlanManager import Plan
	stub = _make_stub(tmp_path)
	plan = Plan('p-disk', 'Disk Plan', 'fallback goal')
	plan.createTask('Task A', title='Task A')
	plan.save(stub.Options['plans_path'])
	text = stub._active_plan_text()
	assert 'Disk Plan' in text
	assert 'Task A' in text


def test_active_plan_text_none(tmp_path):
	stub = _make_stub(tmp_path)
	assert stub._active_plan_text() == ''


def test_insert_summary_appends_plan(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	PlanBase.draft = _sample_plan()
	msgs = [
		{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
		{'role': 'user', 'content': 'check the network config', 'name': ''},
		{'role': 'assistant', 'content': 'ok', 'name': ''},
	]
	new = stub._insert_summary(msgs, {0, 1}, 'the summary')
	summary_msgs = [m for m in new if m['content'].startswith('[Context summary:')]
	assert len(summary_msgs) == 1
	assert '[ACTIVE PLAN]' in summary_msgs[0]['content']
	assert 'Deploy Fix' in summary_msgs[0]['content']
