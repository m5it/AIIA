import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class FakeLG:
	def echo(self, msg, opts=None):
		pass


class ToolStubHandle:
	"""Minimal handle for ToolExecutor._cache_file_buffer."""

	def __init__(self, plan_text='plan', cache=None, options=None):
		self.hLG = FakeLG()
		self.Options = dict({
			'TOOL_FILE_CACHE': True,
			'TOOL_FILE_CACHE_ON_PLAN': True,
			'TOOL_FILE_CACHE_MAX_FILE': 100000,
			'TOOL_FILE_CACHE_MAX_FILES': 20,
		}, **(options or {}))
		self._plan_text = plan_text
		self.file_buffer_cache = cache if cache is not None else {}

	def _active_plan_text(self):
		return self._plan_text


@pytest.fixture(autouse=True)
def _clean_draft():
	from src.PlanManager import PlanBase
	PlanBase.draft = None
	PlanBase.done = {}


def _cache_obj(handle):
	from src.ToolExecutor import ToolExecutor
	obj = ToolExecutor.__new__(ToolExecutor)
	obj.handle = handle
	return obj


def test_cache_writefile_populates(tmp_path):
	f = tmp_path / 'f.py'
	f.write_text('line1\nline2\n')
	obj = _cache_obj(ToolStubHandle())
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert obj.handle.file_buffer_cache[str(f)] == 'line1\nline2\n'


def test_cache_assembles_chunked_writes(tmp_path):
	from src.functions import fwrite
	f = tmp_path / 'big.py'
	obj = _cache_obj(ToolStubHandle())
	fwrite(str(f), 'part1\n', True)
	obj._cache_file_buffer('AppendFile', {'fileName': str(f)}, 'ok')
	fwrite(str(f), 'part1\npart2\n', True)
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert obj.handle.file_buffer_cache[str(f)] == 'part1\npart2\n'


def test_no_cache_without_plan(tmp_path):
	f = tmp_path / 'f.py'
	f.write_text('x')
	obj = _cache_obj(ToolStubHandle(plan_text=''))
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert obj.handle.file_buffer_cache == {}


def test_no_cache_when_toggle_off(tmp_path):
	f = tmp_path / 'f.py'
	f.write_text('x')
	obj = _cache_obj(ToolStubHandle(options={'TOOL_FILE_CACHE': False}))
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert obj.handle.file_buffer_cache == {}


def test_no_cache_on_error_result(tmp_path):
	f = tmp_path / 'f.py'
	f.write_text('x')
	obj = _cache_obj(ToolStubHandle())
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'Error: nope')
	assert obj.handle.file_buffer_cache == {}


def test_sed_only_cached_when_inplace(tmp_path):
	f = tmp_path / 'f.py'
	f.write_text('a\nb\n')
	obj = _cache_obj(ToolStubHandle())
	obj._cache_file_buffer('Sed', {'fileName': str(f), 'inplace': False}, 'ok')
	assert obj.handle.file_buffer_cache == {}
	obj._cache_file_buffer('Sed', {'fileName': str(f), 'inplace': 'true'}, 'ok')
	assert obj.handle.file_buffer_cache[str(f)] == 'a\nb\n'


def test_cache_skips_large_file(tmp_path):
	f = tmp_path / 'big.py'
	f.write_text('y' * 5000)
	obj = _cache_obj(ToolStubHandle(options={'TOOL_FILE_CACHE_MAX_FILE': 1000}))
	obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert obj.handle.file_buffer_cache == {}


def test_cache_evicts_oldest(tmp_path):
	obj = _cache_obj(ToolStubHandle(options={'TOOL_FILE_CACHE_MAX_FILES': 2}))
	for i in range(3):
		f = tmp_path / ('f%d.py' % i)
		f.write_text('c%d' % i)
		obj._cache_file_buffer('WriteFile', {'fileName': str(f)}, 'ok')
	assert len(obj.handle.file_buffer_cache) == 2
	assert str(tmp_path / 'f0.py') not in obj.handle.file_buffer_cache
	assert str(tmp_path / 'f2.py') in obj.handle.file_buffer_cache


def _context_obj(cache, options=None, plan_text='plan'):
	from src.HandleContext import HandleContext
	obj = HandleContext.__new__(HandleContext)
	obj.Options = dict({'TOOL_FILE_CACHE_REINJECT': True,
		'TOOL_FILE_CACHE_REINJECT_MAX': 5000,
		'TOOL_FILE_CACHE_REINJECT_TOTAL': 30000}, **(options or {}))
	obj.file_buffer_cache = cache
	return obj


def test_file_cache_section_empty_when_toggle_off():
	obj = _context_obj({'a': 'x'}, options={'TOOL_FILE_CACHE_REINJECT': False})
	assert obj._file_cache_section() == ''


def test_file_cache_section_empty_cache():
	obj = _context_obj({})
	assert obj._file_cache_section() == ''


def test_file_cache_section_full_content():
	obj = _context_obj({'workout/a.py': 'print(1)'})
	section = obj._file_cache_section()
	assert '[CACHED FILE BUFFERS]' in section
	assert '### workout/a.py (8 chars)' in section
	assert 'print(1)' in section


def test_file_cache_section_truncates_per_file():
	obj = _context_obj({'a.py': 'x' * 100}, options={'TOOL_FILE_CACHE_REINJECT_MAX': 20})
	section = obj._file_cache_section()
	assert 'x' * 20 in section and 'x' * 21 not in section
	assert 'truncated' in section


def test_file_cache_section_total_cap_manifest():
	cache = {'a.py': 'z' * 100, 'b.py': 'w' * 100}
	obj = _context_obj(cache, options={'TOOL_FILE_CACHE_REINJECT_TOTAL': 130})
	section = obj._file_cache_section()
	assert '- b.py (100 chars)' in section
	assert '### a.py' in section
	assert '### b.py' not in section


def test_insert_summary_does_not_include_cache_section():
	from src.HandleContext import HandleContext
	from src.PlanManager import PlanBase
	obj = _context_obj({'workout/out.txt': 'cached data'})
	obj.Options.update({'AI_SESS_ID': 's1', 'AI_ROW_ID': 5})
	PlanBase.draft = None
	msgs = [{'role': 'system', 'content': 'S1'}, {'role': 'user', 'content': 'u'}]
	new = obj._insert_summary(msgs, {0, 1}, 'SUM')
	assert '[CACHED FILE BUFFERS]' not in new[1]['content']
	assert 'cached data' not in new[1]['content']


def test_continue_prompt_includes_cache_section():
	from src.PlanManager import PlanBase
	obj = _context_obj({'workout/out.txt': 'cached data'})
	PlanBase.draft = None
	prompt = obj._build_continue_prompt()
	assert '[CACHED FILE BUFFERS]' in prompt
	assert 'cached data' in prompt


def test_jobdone_clears_cache():
	from src.PlanManager import Plan, PlanBase
	plan = Plan('t1', 'T', 'i')
	plan.save = lambda: None
	handle = ToolStubHandle(cache={'a.py': 'x'})
	plan.jobDone(handle)
	assert handle.file_buffer_cache == {}
	assert PlanBase.draft is None
