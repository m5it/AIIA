import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeTipManager:
	def __init__(self):
		self.tips = {}

	def save(self, title, source, entries):
		self.tips[title] = entries

	def get(self, title, source=None):
		return self.tips.get(title, [])

	def delete(self, title, source=None):
		self.tips.pop(title, None)
		return True


class _Stub:
	"""Minimal stub for mode-instruction tests."""
	def __init__(self, options, msgs=None):
		self.Options = dict(options)
		self.hLG = FakeLogger()
		self.hHM = type('H', (), {})()
		self.hHM.msgs = list(msgs) if msgs else []
		self.hTM = FakeTipManager()
		self._consumed_tips = set()
		self._rewritten = []

	def Response(self, role, opts):
		self.hHM.msgs.append({'role': role, 'content': opts.get('content', '')})

	def _rewrite_history(self, msgs):
		self._rewritten.append(list(msgs))
		self.hHM.msgs = list(msgs)


@pytest.fixture(autouse=True)
def _clean_planbase():
	from src.PlanManager import PlanBase
	PlanBase.draft = None
	yield
	PlanBase.draft = None


def _make_stub_with_both_instructions(mode='build'):
	"""Create a stub with the short prompt + both plan and build tips loaded."""
	from src.Prepare import Prepare

	options = {
		'MODE': mode,
		'AI_INSTRUCT_OPTION': 2,
		'INSTRUCT_CLASS': 'Developer',
		'INSTRUCT_PATH': 'instruct',
		'path': '/framework',
	}
	stub = _Stub(options)
	stub.hPP = Prepare({'handle': stub})

	# Inject the option-2 short prompt and the two tip-based instruction blocks
	plan_text = stub.hPP._get_mode_instructions('plan')
	build_text = stub.hPP._get_mode_instructions('build')

	stub.hHM.msgs = [
		{'role': 'system', 'content': stub.hPP._get_mode_instructions('build')},  # short prompt
		{'role': 'system', 'content': '[PLAN MODE INSTRUCTIONS]\n' + plan_text},
		{'role': 'system', 'content': '[BUILD MODE INSTRUCTIONS]\n' + build_text},
		{'role': 'user', 'content': 'make a thing'},
	]
	return stub


def test_ensure_mode_instructions_removes_stale_plan_instructions():
	from src.HandleChat import HandleChat
	from src.HandleState import HandleState

	stub = _make_stub_with_both_instructions('build')

	class HCombined(HandleChat, HandleState):
		def __init__(self, s):
			self.hLG = s.hLG
			self.hHM = s.hHM
			self.Options = s.Options
			self.hPP = s.hPP
			self._consumed_tips = s._consumed_tips
			self._rewritten = s._rewritten

		def Response(self, role, opts):
			self.hHM.msgs.append({'role': role, 'content': opts.get('content', '')})

		def _rewrite_history(self, msgs):
			self._rewritten.append(list(msgs))
			self.hHM.msgs = list(msgs)

	hc = HCombined(stub)
	hc._ensure_mode_instructions()

	# Build instructions should remain; plan instructions should be gone
	roles = [m.get('role') for m in stub.hHM.msgs]
	contents = [m.get('content', '') for m in stub.hHM.msgs]
	assert roles == ['system', 'system', 'user']
	assert any(c.startswith('[BUILD MODE INSTRUCTIONS]') for c in contents)
	assert not any(c.startswith('[PLAN MODE INSTRUCTIONS]') for c in contents)
	assert stub._rewritten


def test_set_mode_instructions_dedupes_current_mode_instructions():
	from src.HandleChat import HandleChat

	stub = _make_stub_with_both_instructions('build')
	# Duplicate build instructions
	stub.hHM.msgs.insert(1, {'role': 'system', 'content': '[BUILD MODE INSTRUCTIONS]\n' + stub.hPP._get_mode_instructions('build')})

	class HCH(HandleChat):
		def __init__(self, s):
			self.hLG = s.hLG
			self.hHM = s.hHM
			self.Options = s.Options
			self.hPP = s.hPP
			self._consumed_tips = s._consumed_tips
			self._rewritten = s._rewritten

		def Response(self, role, opts):
			super().Response(role, opts)

		def _rewrite_history(self, msgs):
			self._rewritten.append(list(msgs))
			self.hHM.msgs = list(msgs)

	hch = HCH(stub)
	hch._set_mode_instructions('build')

	contents = [m.get('content', '') for m in stub.hHM.msgs if m.get('role') == 'system']
	build_count = sum(1 for c in contents if c.startswith('[BUILD MODE INSTRUCTIONS]'))
	plan_count = sum(1 for c in contents if c.startswith('[PLAN MODE INSTRUCTIONS]'))
	assert build_count == 1
	assert plan_count == 0


def test_set_mode_instructions_removes_stale_plan_tool_reference_and_example():
	from src.HandleChat import HandleChat

	stub = _make_stub_with_both_instructions('build')
	stub.hHM.msgs.insert(1, {'role': 'system', 'content': '[PLAN MODE TOOL REFERENCE]\nFoo'})
	stub.hHM.msgs.insert(1, {'role': 'system', 'content': '[PLAN MODE WORKFLOW EXAMPLE]\nBar'})

	class HCH(HandleChat):
		def __init__(self, s):
			self.hLG = s.hLG
			self.hHM = s.hHM
			self.Options = s.Options
			self.hPP = s.hPP
			self._consumed_tips = s._consumed_tips
			self._rewritten = s._rewritten

		def Response(self, role, opts):
			super().Response(role, opts)

		def _rewrite_history(self, msgs):
			self._rewritten.append(list(msgs))
			self.hHM.msgs = list(msgs)

	hch = HCH(stub)
	hch._set_mode_instructions('build')

	contents = [m.get('content', '') for m in stub.hHM.msgs if m.get('role') == 'system']
	assert not any(c.startswith('[PLAN MODE') for c in contents)
	assert any(c.startswith('[BUILD MODE INSTRUCTIONS]') for c in contents)


def test_reinsert_tip_filters_other_mode_instruct_entries():
	from src.TipManager import TipManager

	class _Handle:
		def __init__(self):
			self.Options = {'MODE': 'build', 'AI_ROW_ID': 0}
			self._consumed_tips = set()
			self.reinserted = []
			self._set_mode_instructions_calls = []
			self.hLG = FakeLogger()

		def Response(self, role, opts):
			self.reinserted.append({'role': role, 'content': opts.get('content', '')})

		def _set_mode_instructions(self, mode):
			self._set_mode_instructions_calls.append(mode)

	handle = _Handle()
	tm = TipManager({'handle': handle})
	tm.get = lambda title, source=None: [{
		'entries': [
			{'role': 'system', 'content': '[PLAN MODE INSTRUCTIONS]\nplan text'},
			{'role': 'system', 'content': '[BUILD MODE INSTRUCTIONS]\nbuild text'},
			{'role': 'system', 'content': '[BUILD MODE TOOL REFERENCE]\nbuild tools'},
			{'role': 'system', 'content': '[PLAN MODE TOOL REFERENCE]\nplan tools'},
		]
	}]
	count = tm.reinsert('instruct_developer')
	assert count == 2
	contents = [m['content'] for m in handle.reinserted]
	assert any(c.startswith('[BUILD MODE INSTRUCTIONS]') for c in contents)
	assert any(c.startswith('[BUILD MODE TOOL REFERENCE]') for c in contents)
	assert not any(c.startswith('[PLAN MODE') for c in contents)
	assert handle._set_mode_instructions_calls == ['build']


def test_reinsert_tip_does_not_filter_arbitrary_tips():
	from src.TipManager import TipManager

	class _Handle:
		def __init__(self):
			self.Options = {'MODE': 'build', 'AI_ROW_ID': 0}
			self._consumed_tips = set()
			self.reinserted = []
			self.hLG = FakeLogger()

		def Response(self, role, opts):
			self.reinserted.append({'role': role, 'content': opts.get('content', '')})

	handle = _Handle()
	tm = TipManager({'handle': handle})
	tm.get = lambda title, source=None: [{
		'entries': [
			{'role': 'system', 'content': '[PLAN MODE INSTRUCTIONS]\nplan text'},
			{'role': 'user', 'content': 'note'},
		]
	}]
	count = tm.reinsert('legacy_tip')
	assert count == 2
