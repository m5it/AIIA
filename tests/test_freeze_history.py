import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from src.Handle import Handle


def _make_stub(options, msgs=None):
	stub = type('Stub', (), {})()
	stub.Options = dict(options)
	stub.hHM = type('H', (), {})()
	stub.hHM.msgs = list(msgs or [])
	return stub


def _call_persist(stub, obj, monkeypatch, raise_on_write=False):
	import src.Handle as HandleModule

	def _fake_fwrite(*a, **k):
		if raise_on_write:
			raise AssertionError("fwrite should not be called while frozen")
		HandleModule._fake_write_calls.append(a[0])

	HandleModule._fake_write_calls = []
	monkeypatch.setattr(HandleModule, 'fwrite', _fake_fwrite)
	monkeypatch.setattr(HandleModule.PlanSaver, 'save_history', lambda *a, **k: None)
	Handle._persist_response(stub, obj, False)


def test_freeze_history_skips_all_appends(monkeypatch):
	stub = _make_stub({'AI_FREEZE_HISTORY': 1, 'path': '/tmp', 'AI_FILE_HISTORY': 'h.aiia'})
	before = list(stub.hHM.msgs)
	_call_persist(stub, {'role': 'user', 'content': 'hi'}, monkeypatch, raise_on_write=True)
	assert stub.hHM.msgs == before


def test_freeze_history_normal_when_disabled(monkeypatch):
	stub = _make_stub({'AI_FREEZE_HISTORY': 0, 'path': '/tmp', 'AI_FILE_HISTORY': 'h.aiia'})
	_call_persist(stub, {'role': 'user', 'content': 'hi'}, monkeypatch)
	assert stub.hHM.msgs == [{'role': 'user', 'content': 'hi'}]


def test_freeze_history_flag_default_off():
	from config import Options
	assert Options.get('AI_FREEZE_HISTORY', 0) == 0
	assert Options.get('AI_FREEZE_LOOP', 0) == 0


def _make_chat_stub(options, **attrs):
	stub = type('Stub', (), {})()
	stub.Options = dict(options)
	for k, v in attrs.items():
		setattr(stub, k, v)
	return stub


def test_freeze_loop_repeat_logic():
	repeat = Handle._freeze_loop_repeat

	# flag off → never repeat
	stub = _make_chat_stub({'AI_FREEZE_LOOP': 0}, _last_user_input='x')
	assert repeat(stub) is False

	# flag on but no last input yet → prompt normally
	stub = _make_chat_stub({'AI_FREEZE_LOOP': 1})
	assert repeat(stub) is False

	# flag on + last input → repeat
	stub = _make_chat_stub({'AI_FREEZE_LOOP': 1}, _last_user_input='test prompt')
	assert repeat(stub) is True

	# paused after user interrupt → let the prompt show
	stub = _make_chat_stub({'AI_FREEZE_LOOP': 1}, _last_user_input='test prompt', _freeze_loop_paused=True)
	assert repeat(stub) is False
