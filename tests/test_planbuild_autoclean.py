import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from src.HandleContext import HandleContext
from src.HandleParse import HandleParse


def _sys(content):
	return {'role': 'system', 'content': content}


def _usr(content):
	return {'role': 'user', 'content': content}


def _asst(content='work'):
	return {'role': 'assistant', 'content': content}


def _tool(content='ok'):
	return {'role': 'tool', 'content': content}


def _plan_done_sys():
	return _sys('Plan is ready! Starting first task.\n\nTask 1/3 - build a thing')


def _startbuild_sys():
	return _sys('Mode changed to BUILD. You can now make changes.\n\nTask 1/3 - build a thing')


def _next_task_usr(n=2):
	return _usr('<nextTask>\n\nYour task:\nTask {}/3 - next thing'.format(n))


def _make_stub(options, msgs, calls=None):
	stub = type('Stub', (), {})()
	stub.Options = dict(options)
	stub.hHM = type('H', (), {})()
	stub.hHM.msgs = list(msgs)
	stub.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub._pb_anchor_indices = lambda msgs: HandleContext._pb_anchor_indices(stub, msgs)
	if calls is not None:
		stub._clean_calls = calls
		stub._pb_autoclean = lambda: stub._clean_calls.append(True)
	return stub


def _bind_clean(stub):
	return HandleContext._pb_autoclean(stub)


def _options(**kw):
	o = {
		'AI_PLANBUILD_AUTOCLEAN': 1,
		'AI_PLANBUILD_WAIT': 5,
		'AI_FREEZE_HISTORY': 0,
		'MODE': 'build',
		'path': '/tmp/fw',
		'working_dir': None,
	}
	o.update(kw)
	return o


def test_autoclean_removes_between_anchors():
	msgs = [
		_usr('make a thing'), _asst(), _tool(), _asst(),
		_plan_done_sys(), _startbuild_sys(),
		_asst(), _tool(), _asst(), _next_task_usr(),
		_asst('current work'),
	]
	stub = _make_stub(_options(), msgs)
	# first call cleans the OLDEST uncleaned block: the planning phase
	assert _bind_clean(stub) is True
	assert [m.get('role') for m in stub.hHM.msgs] == [
		'user', 'system', 'system', 'assistant', 'tool', 'assistant', 'user', 'assistant',
	]
	# second call advances the sliding window: the finished task-1 work
	assert _bind_clean(stub) is True
	assert [m.get('role') for m in stub.hHM.msgs] == [
		'user', 'system', 'system', 'user', 'assistant',
	]
	assert stub.hHM.msgs[-2] == _next_task_usr()
	assert stub.hHM.msgs[-1] == _asst('current work')


def test_autoclean_keeps_system_messages_in_window():
	msgs = [
		_usr('make a thing'), _plan_done_sys(), _startbuild_sys(),
		_sys('extra instruction'), _asst(), _tool(), _asst(), _next_task_usr(),
	]
	stub = _make_stub(_options(), msgs)
	assert _bind_clean(stub) is True
	assert any(m.get('role') == 'system' and m.get('content') == 'extra instruction' for m in stub.hHM.msgs)


def test_autoclean_first_clean_drops_planning_phase():
	msgs = [
		_usr('make a thing'), _asst('plan note'), _tool(), _asst(),
		_plan_done_sys(),
	]
	stub = _make_stub(_options(), msgs)
	assert _bind_clean(stub) is True
	assert [m.get('role') for m in stub.hHM.msgs] == ['user', 'system']


def test_autoclean_needs_two_anchors():
	msgs = [_usr('make a thing'), _asst(), _tool()]
	stub = _make_stub(_options(), msgs)
	# single anchor → no clean
	assert HandleContext._pb_autoclean(stub) is False
	assert len(stub.hHM.msgs) == 3


def test_autoclean_no_removal_returns_false():
	msgs = [_usr('make a thing'), _plan_done_sys(), _startbuild_sys(), _next_task_usr()]
	stub = _make_stub(_options(), msgs)
	assert HandleContext._pb_autoclean(stub) is False
	assert len(stub.hHM.msgs) == 4


def test_autoclean_rewrites_history_md_not_dbk(monkeypatch):
	from src.HandleContext import PlanSaver
	calls = []
	monkeypatch.setattr(PlanSaver, 'rebuild_history', lambda path, msgs: calls.append((path, list(msgs))))
	msgs = [
		_usr('make a thing'), _asst(), _tool(), _plan_done_sys(), _startbuild_sys(),
		_asst(), _next_task_usr(),
	]
	stub = _make_stub(_options(working_dir='/proj'), msgs)
	stub._sync_row_id_and_tokens = lambda: None
	assert _bind_clean(stub) is True
	assert len(calls) == 1
	assert calls[0][0] == os.path.join('/proj', 'HISTORY.md')
	assert [m.get('role') for m in calls[0][1]] == ['user', 'system', 'system', 'assistant', 'user']


def test_after_assistant_disabled():
	stub = _make_stub(_options(AI_PLANBUILD_AUTOCLEAN=0),
		[_usr('x'), _plan_done_sys(), _next_task_usr()])
	stub._pb_clean_counter = 7
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 7


def test_after_assistant_freeze_history():
	stub = _make_stub(_options(AI_FREEZE_HISTORY=1),
		[_usr('x'), _plan_done_sys(), _next_task_usr()])
	stub._pb_clean_counter = 0
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 0


def test_after_assistant_plan_mode_no_count():
	stub = _make_stub(_options(MODE='plan'),
		[_usr('x'), _plan_done_sys(), _next_task_usr()])
	stub._pb_clean_counter = 0
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 0


def test_after_assistant_fewer_than_two_anchors():
	stub = _make_stub(_options(), [_usr('x'), _asst()])
	stub._pb_clean_counter = 0
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 0


def test_after_assistant_counts_and_cleans_at_wait():
	calls = []
	msgs = [_usr('x'), _plan_done_sys(), _startbuild_sys(), _next_task_usr(), _asst()]
	stub = _make_stub(_options(AI_PLANBUILD_WAIT=2), msgs, calls)
	stub._pb_clean_counter = 0
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 1
	assert calls == []
	HandleParse._pb_after_assistant(stub)
	assert stub._pb_clean_counter == 0
	assert calls == [True]


def test_after_assistant_plan_completed_stops(monkeypatch):
	import src.PlanManager as PM
	monkeypatch.setattr(PM.PlanBase, 'draft', type('D', (), {'tasks': {'a': type('T', (), {'status': 'completed'})()}})())
	msgs = [_usr('x'), _plan_done_sys(), _startbuild_sys(), _next_task_usr(), _asst()]
	calls = []
	stub = _make_stub(_options(AI_PLANBUILD_WAIT=1), msgs, calls)
	stub._pb_clean_counter = 0
	HandleParse._pb_after_assistant(stub)
	assert calls == []


def test_parse_assistant_history_anchor_turn_resets():
	records = []

	class PStub:
		pass

	stub = PStub()
	stub.Options = _options()
	stub.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub.Response = lambda role, opts=None: records.append((role, opts))
	stub._pb_clean_counter = 3
	stub._pb_after_assistant = lambda: records.append(('after_assistant', None))
	HandleParse._parse_assistant_history(stub, {'content': 'x'}, [{'name': 'nextTask'}], False, None)
	assert ('after_assistant', None) not in records
	assert stub._pb_clean_counter == 0


def test_parse_assistant_history_normal_turn_counts():
	records = []

	class PStub:
		pass

	stub = PStub()
	stub.Options = _options()
	stub.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	stub.Response = lambda role, opts=None: records.append((role, opts))
	stub._pb_clean_counter = 0
	stub._pb_after_assistant = lambda: records.append(('after_assistant', None))
	HandleParse._parse_assistant_history(stub, {'content': 'x'}, [{'name': 'ReadFile'}], False, None)
	assert ('after_assistant', None) in records
