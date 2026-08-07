import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeInstructManager:
	def __init__(self):
		self.choosed = False
	def Choose(self):
		self.choosed = True


class FakeHistoryManager:
	def __init__(self):
		self.chosen = False
	def Choose(self):
		self.chosen = True


class FakeHandle:
	def __init__(self, options=None):
		self.hLG = FakeLogger()
		self.hIM = FakeInstructManager()
		self.hHM = FakeHistoryManager()
		self.Options = dict({
			'MODE': 'build',
			'AI_MODEL': 'test-model',
			'AI_LIVE': True,
			'AI_QUICK': False,
			'AI_ROW_ID': 0,
		}, **(options or {}))
		self.responses = []

	def Response(self, role, content_dict):
		self.responses.append((role, content_dict.get('content', '')))


def _make_prepare(options=None):
	from src.Prepare import Prepare
	fake = FakeHandle(options)
	p = Prepare({'handle': fake})
	# Stub the instruction-text helpers so we don't depend on a real persona
	p._get_mode_instructions = lambda mode: "[{} instructions]".format(mode)
	p._inject_agents_md = lambda text: text
	return p, fake


def test_continue_skips_system_message_prompt():
	p, fake = _make_prepare({'CONTINUE': True, 'INSTRUCT_CLASS_OVERRIDE': True})
	p.Prepare()
	assert fake.hIM.choosed is True
	assert fake.hHM.chosen is False  # history selection should be skipped
	assert len(fake.responses) == 1
	assert fake.responses[0][0] == 'system'
	assert '[build instructions]' in fake.responses[0][1]


def test_instruct_class_override_skips_system_message_prompt():
	p, fake = _make_prepare({'INSTRUCT_CLASS_OVERRIDE': True, 'INSTRUCT_CLASS': 'Developer'})
	p.Prepare()
	assert fake.hIM.choosed is True
	assert fake.hHM.chosen is False
	assert len(fake.responses) == 1
	assert fake.responses[0][0] == 'system'


def test_fresh_session_prompts_for_system_message(monkeypatch):
	p, fake = _make_prepare()
	inputs = ["custom prefix"]
	monkeypatch.setattr('src.Prepare.user_input', lambda *a, **k: inputs.pop(0))
	p.Prepare()
	assert fake.hIM.choosed is True
	assert fake.hHM.chosen is True
	assert len(fake.responses) == 1
	assert fake.responses[0][0] == 'system'
	assert 'custom prefix' in fake.responses[0][1]


def test_continuing_with_history_returns_early():
	p, fake = _make_prepare({'CONTINUING': True})
	fake.hIM.choosed = False
	p.Prepare()
	assert fake.hIM.choosed is False
	assert fake.hHM.chosen is False
	assert fake.responses == []
