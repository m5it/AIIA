import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class FakeLG:
	def echo(self, msg, opts=None):
		pass


class FakeTC:
	def __init__(self):
		self.handles = {}


class FakeHandle:
	def __init__(self, options=None):
		self.Options = dict({
			'MODE': 'build',
			'TOOL_SHOW_LOAD': False,
			'TOOL_RESULT_AS_SYSTEM': False,
			'TOOL_RESULT_AS_USER': False,
			'TOOL_TRANSIENT_ENABLED': True,
			'TOOL_TRANSIENT_MAX_STEPS': 10,
			'AI_MAX_FILE_SIZE': 2097152,
		}, **(options or {}))
		self.hTC = FakeTC()
		self.hLG = FakeLG()
		self.hHM = type('H', (), {})()
		self.hHM.msgs = []
		self.tool_iteration = 0
		self.tool_errors = 0
		self._last_failed_tool = None
		self._last_failed_tool_count = 0
		self._plan_blocked_tool = None
		self._rewrite_calls = []
		self._response_calls = []

	def Response(self, role, opts):
		self._response_calls.append((role, opts))
		self.hHM.msgs.append({
			'role': role,
			'content': opts.get('content', ''),
			'name': opts.get('name', ''),
		})

	def _rewrite_history(self, msgs):
		self._rewrite_calls.append([dict(m) for m in msgs])


class FakeReadTool:
	info = {"parameters": {"required": ["fileName"]}}
	def __init__(self):
		self.kwargs = None
	def run(self, fileName, **kwargs):
		self.kwargs = kwargs
		return "data: {}".format(fileName)


class FakeWriteTool:
	info = {"parameters": {"required": ["fileName", "contentOfFile"]}}
	def run(self, fileName, contentOfFile):
		return "wrote"


def _te(handle):
	from src.ToolParser import ToolParser
	obj = ToolParser.__new__(ToolParser)
	obj.handle = handle
	return obj


@pytest.fixture(autouse=True)
def _clean_plan():
	from src.PlanManager import PlanBase
	PlanBase.draft = None


def test_transient_param_popped_before_tool_run():
	h = FakeHandle()
	h.hTC.handles['ReadFile'] = {'handle': FakeReadTool()}
	obj = _te(h)
	params = {'fileName': 'x.txt', 'transient': '5'}
	res = obj.ExecuteTextTool('ReadFile', params)
	assert res == 'data: x.txt'
	# transient must not be passed to run(); other kwargs are the tool's own
	tool = h.hTC.handles['ReadFile']['handle']
	assert 'transient' not in tool.kwargs
	# restored to the clamped int after the call
	assert params.get('transient') == 5


def test_transient_param_clamped():
	h = FakeHandle({'TOOL_TRANSIENT_MAX_STEPS': 3})
	h.hTC.handles['ReadFile'] = {'handle': FakeReadTool()}
	obj = _te(h)
	params = {'fileName': 'x.txt', 'transient': '99'}
	obj.ExecuteTextTool('ReadFile', params)
	assert params.get('transient') == 3


def test_transient_disabled_no_restore():
	h = FakeHandle({'TOOL_TRANSIENT_ENABLED': False})
	h.hTC.handles['ReadFile'] = {'handle': FakeReadTool()}
	obj = _te(h)
	params = {'fileName': 'x.txt', 'transient': '5'}
	obj.ExecuteTextTool('ReadFile', params)
	# restored so FireToolInvocation can still see it, but marking is gated by enabled
	assert params.get('transient') == 5


def test_fire_tool_marks_read_tool_rows():
	h = FakeHandle()
	h.hTC.handles['ReadFile'] = {'handle': FakeReadTool()}
	obj = _te(h)
	# assistant row that issued the read
	h.hHM.msgs.append({'role': 'assistant', 'content': '<ReadFile>\n<fileName>x.txt</fileName>\n<transient>2</transient>\n</ReadFile>'})
	obj.FireToolInvocation([{'name': 'ReadFile', 'parameters': {'fileName': 'x.txt', 'transient': '2'}}])
	assert len(h.hHM.msgs) == 2
	assert h.hHM.msgs[0]['role'] == 'assistant'
	assert h.hHM.msgs[0].get('transient') == 2
	assert h.hHM.msgs[1]['role'] == 'tool'
	assert h.hHM.msgs[1].get('transient') == 2
	assert len(h._rewrite_calls) == 1


def test_fire_tool_does_not_mark_non_read_tool():
	h = FakeHandle()
	h.hTC.handles['WriteFile'] = {'handle': FakeWriteTool()}
	obj = _te(h)
	h.hHM.msgs.append({'role': 'assistant', 'content': '<WriteFile>...</WriteFile>'})
	obj.FireToolInvocation([{'name': 'WriteFile', 'parameters': {'fileName': 'x.txt', 'contentOfFile': 'hi', 'transient': '2'}}])
	assert len(h.hHM.msgs) == 2
	assert h.hHM.msgs[0].get('transient') is None
	assert h.hHM.msgs[1].get('transient') is None
	assert len(h._rewrite_calls) == 0


def test_fire_tool_does_not_mark_when_disabled():
	h = FakeHandle({'TOOL_TRANSIENT_ENABLED': False})
	h.hTC.handles['ReadFile'] = {'handle': FakeReadTool()}
	obj = _te(h)
	h.hHM.msgs.append({'role': 'assistant', 'content': '<ReadFile>...</ReadFile>'})
	obj.FireToolInvocation([{'name': 'ReadFile', 'parameters': {'fileName': 'x.txt', 'transient': '2'}}])
	assert h.hHM.msgs[0].get('transient') is None
	assert h.hHM.msgs[1].get('transient') is None


def test_mark_transient_rows_assistant_marker_does_not_shrink():
	"""If the assistant row already has a higher transient value, keep it."""
	h = FakeHandle()
	obj = _te(h)
	h.hHM.msgs.append({'role': 'assistant', 'content': 'a', 'transient': 5})
	h.hHM.msgs.append({'role': 'tool', 'content': 'r'})
	obj._mark_transient_rows(2)
	assert h.hHM.msgs[0]['transient'] == 5
	assert h.hHM.msgs[1]['transient'] == 2


def test_sweep_transient_rows_decrements_and_removes():
	from src.HandleContext import HandleContext
	class Stub(HandleContext):
		def __init__(self):
			self.Options = {'AI_CONTEXT_LIMIT': 10000, 'AI_CLEAR_THRESHOLD': 0.8}
			self.hLG = FakeLG()
			self.hHM = type('H', (), {})()
			self.hHM.msgs = [
				{'role': 'system', 'content': 's'},
				{'role': 'assistant', 'content': 'call', 'transient': 2},
				{'role': 'tool', 'content': 'result', 'transient': 2},
				{'role': 'user', 'content': 'u'},
			]
			self._rewrite_calls = []
		def _rewrite_history(self, msgs):
			self._rewrite_calls.append([dict(m) for m in msgs])
	s = Stub()
	s._sweep_transient_rows()
	assert len(s.hHM.msgs) == 4
	assert s.hHM.msgs[1]['transient'] == 1
	assert s.hHM.msgs[2]['transient'] == 1
	assert len(s._rewrite_calls) == 0
	# second sweep removes the transient rows
	s._sweep_transient_rows()
	assert len(s.hHM.msgs) == 2
	assert [m['role'] for m in s.hHM.msgs] == ['system', 'user']
	assert len(s._rewrite_calls) == 1


def test_sweep_leaves_regular_rows():
	from src.HandleContext import HandleContext
	class Stub(HandleContext):
		def __init__(self):
			self.Options = {'AI_CONTEXT_LIMIT': 10000, 'AI_CLEAR_THRESHOLD': 0.8}
			self.hLG = FakeLG()
			self.hHM = type('H', (), {})()
			self.hHM.msgs = [
				{'role': 'system', 'content': 's'},
				{'role': 'assistant', 'content': 'a'},
				{'role': 'user', 'content': 'u'},
			]
			self._rewrite_calls = []
		def _rewrite_history(self, msgs):
			self._rewrite_calls.append([dict(m) for m in msgs])
	s = Stub()
	s._sweep_transient_rows()
	assert len(s.hHM.msgs) == 3
	assert len(s._rewrite_calls) == 0


def test_manage_context_calls_sweep():
	from src.HandleContext import HandleContext
	class Stub(HandleContext):
		def __init__(self):
			self.Options = {'AI_CONTEXT_LIMIT': 10000, 'AI_CLEAR_THRESHOLD': 0.8}
			self.hLG = FakeLG()
			self.hHM = type('H', (), {})()
			self.hHM.msgs = [
				{'role': 'assistant', 'content': 'call', 'transient': 1},
				{'role': 'tool', 'content': 'result', 'transient': 1},
			]
			self._rewrite_calls = []
			self.sweeped = False
		def _sweep_transient_rows(self):
			self.sweeped = True
		def _estimate_tokens(self, msgs):
			return 0
		def _rewrite_history(self, msgs):
			self._rewrite_calls.append([dict(m) for m in msgs])
	s = Stub()
	s._manage_context()
	assert s.sweeped is True
