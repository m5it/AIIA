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

	def _auto_clear(self):
		self._auto_clear_calls += 1
		self.hHM.msgs = [m for m in self.hHM.msgs if m.get('role') == 'system']
		self.Options['AI_ROW_ID'] = 0

	def _build_continue_prompt(self, base="Continue with the task."):
		return base

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
				'TOOL_FILE_CACHE_REINJECT': True,
				'TOOL_FILE_CACHE_REINJECT_MAX': 5000,
				'TOOL_FILE_CACHE_REINJECT_TOTAL': 30000,
			}
			self.injected = []
			self.file_buffer_cache = {}

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
	# Only system messages remain, plus the single injected warm-up user message
	roles = [m['role'] for m in fake.hHM.msgs]
	assert roles == ['system', 'user']


def test_summarize_injects_single_user_message():
	c, fake = _make()
	c.CMD_SUMMARIZE('!SUMMARIZE')
	sys_msgs = [m for m in fake.hHM.msgs if m['role'] == 'system']
	assert len(sys_msgs) == 1  # original system message kept
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


def test_auto_clear_keeps_system_only(tmp_path):
	stub = _make_stub(tmp_path)
	stub._auto_clear()
	assert stub.injected == []
	assert all(m['role'] == 'system' for m in stub.hHM.msgs)
	assert len(stub.hHM.msgs) == 1


def test_auto_clear_with_plan_injects_nothing(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	PlanBase.draft = _sample_plan()
	stub._auto_clear()
	assert stub.injected == []
	assert all(m['role'] == 'system' for m in stub.hHM.msgs)
	assert len(stub.hHM.msgs) == 1


def test_build_continue_prompt_with_plan_and_cache(tmp_path):
	from src.PlanManager import PlanBase
	stub = _make_stub(tmp_path)
	stub.file_buffer_cache = {'workout/a.py': 'hello'}
	PlanBase.draft = _sample_plan()
	prompt = stub._build_continue_prompt()
	assert '[ACTIVE PLAN]' in prompt
	assert 'Deploy Fix' in prompt
	assert '[CACHED FILE BUFFERS]' in prompt
	assert 'hello' in prompt


def test_build_continue_prompt_base_only(tmp_path):
	stub = _make_stub(tmp_path)
	stub.Options['MODE'] = 'build'
	prompt = stub._build_continue_prompt()
	assert "Current mode: BUILD." in prompt
	assert "Continue with the task." in prompt


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


def test_insert_summary_keeps_plan_out_of_summary(tmp_path):
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
	assert '[ACTIVE PLAN]' not in summary_msgs[0]['content']
	assert 'Deploy Fix' not in summary_msgs[0]['content']


def test_insert_summary_concats_into_single_row_and_places_after_standing_block(tmp_path):
	stub = _make_stub(tmp_path)
	msgs = [
		{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
		{'role': 'system', 'content': '## Project Instructions', 'name': ''},
		{'role': 'user', 'content': 'u1', 'name': ''},
		{'role': 'assistant', 'content': 'a1', 'name': ''},
		{'role': 'user', 'content': 'u2', 'name': ''},
		{'role': 'assistant', 'content': 'a2', 'name': ''},
	]
	# keep all system + last user exchange
	new = stub._insert_summary(msgs, {0, 1, 4, 5}, 'first summary')
	summary_msgs = [m for m in new if m['content'].startswith('[Context summary:')]
	assert len(summary_msgs) == 1
	assert 'first summary' in summary_msgs[0]['content']
	# placed after the standing system block, before the recent exchanges
	assert new[2]['role'] == 'system' and new[2]['content'].startswith('[Context summary:')
	assert new[3] == {'role': 'user', 'content': 'u2', 'name': ''}
	assert new[4] == {'role': 'assistant', 'content': 'a2', 'name': ''}
	# second summarize merges into the same row instead of adding a new one
	new2 = stub._insert_summary(new, {0, 1, 2, 3, 4}, 'second summary')
	summary_msgs2 = [m for m in new2 if m['content'].startswith('[Context summary:')]
	assert len(summary_msgs2) == 1
	assert 'second summary' in summary_msgs2[0]['content']
	assert 'first summary' in summary_msgs2[0]['content']


def test_insert_summary_collapses_legacy_summary_pile(tmp_path):
	stub = _make_stub(tmp_path)
	msgs = [
		{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
		{'role': 'system', 'content': '[Context summary: old one]', 'name': ''},
		{'role': 'system', 'content': '[Context summary: older two]', 'name': ''},
		{'role': 'user', 'content': 'u2', 'name': ''},
	]
	new = stub._insert_summary(msgs, {0, 1, 2, 3}, 'fresh')
	summary_msgs = [m for m in new if m['content'].startswith('[Context summary:')]
	assert len(summary_msgs) == 1
	assert 'fresh' in summary_msgs[0]['content']
	assert 'old one' in summary_msgs[0]['content']
	assert 'older two' in summary_msgs[0]['content']
	assert [m['content'] for m in new] == [
		'MODE: BUILD',
		summary_msgs[0]['content'],
		'u2',
	]


def test_merge_summary_content_respects_cap():
	from src.HandleChat import _merge_summary_content
	merged = _merge_summary_content('[Context summary: {}]'.format('x' * 1000), 'new', cap=100)
	# newest stays whole, older chunk is trimmed to fit the cap
	assert 'new' in merged
	assert merged.startswith('[Context summary: new')
	assert len(merged) <= 100 + 20
	assert 'x' * 1000 not in merged
