import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeHistoryManager:
	def __init__(self, msgs):
		self.msgs = msgs


class FakeHandle:
	def __init__(self, opts):
		self.Options = opts
		self.hLG = FakeLogger()
		self.hHM = FakeHistoryManager([])
		self.tool_iteration = 0
		self.tool_errors = 0
		self._last_failed_tool = None
		self._last_failed_tool_count = 0
		self.responses = []

	def Response(self, role, opts):
		msg = {
			'role': role,
			'content': opts.get('content', ''),
			'name': opts.get('name', ''),
		}
		self.hHM.msgs.append(msg)
		self.responses.append((role, msg['content'], msg['name']))


class FakeTool:
	cache_ttl = 0
	def __init__(self, result):
		self.result = result

	def run(self, **kwargs):
		return self.result


class FakeToolChooser:
	def __init__(self):
		self.handles = {}


class StubExecutor:
	"""Minimal ToolExecutor stub with only the dedup logic."""
	_read_tools_dedup = {'ReadFile', 'Grep'}

	def __init__(self, handle):
		self.handle = handle
		self.hTC = FakeToolChooser()

	def _read_content_hash(self, content):
		import zlib
		return '{:08x}'.format(zlib.crc32(str(content or '').encode('utf-8')))

	def _find_duplicate_read_result(self, toolName, content):
		new_hash = self._read_content_hash(content)
		for i in range(len(self.handle.hHM.msgs) - 1, -1, -1):
			msg = self.handle.hHM.msgs[i]
			if msg.get('role') == 'tool' and msg.get('name') == toolName:
				if self._read_content_hash(msg.get('content', '')) == new_hash:
					return i
		return None

	def _dedup_result(self, toolName, result):
		if (self.handle.Options.get('TOOL_DEDUPLICATE_READS', True)
			and toolName in self._read_tools_dedup
			and result
			and not str(result).startswith('Error')):
			row = self._find_duplicate_read_result(toolName, result)
			if row is not None:
				notice = ("[Duplicate result: same content already returned by {} at row {} "
					"({} chars). Use that result instead of re-reading.]".format(toolName, row, len(str(result))))
				return notice, row
		return result, None


def test_dedup_finds_duplicate_read_result():
	h = FakeHandle({'TOOL_DEDUPLICATE_READS': True})
	h.hHM.msgs = [
		{'role': 'assistant', 'content': '<ReadFile><fileName>x.txt</fileName></ReadFile>'},
		{'role': 'tool', 'content': 'same content', 'name': 'ReadFile'},
	]
	ex = StubExecutor(h)
	assert ex._find_duplicate_read_result('ReadFile', 'same content') == 1
	assert ex._find_duplicate_read_result('ReadFile', 'different content') is None


def test_dedup_replaces_duplicate_with_notice():
	h = FakeHandle({'TOOL_DEDUPLICATE_READS': True})
	h.hHM.msgs = [
		{'role': 'tool', 'content': 'same content', 'name': 'ReadFile'},
	]
	ex = StubExecutor(h)
	result, row = ex._dedup_result('ReadFile', 'same content')
	assert row == 0
	assert 'Duplicate result' in result
	assert 'row 0' in result


def test_dedup_disabled_leaves_result_unchanged():
	h = FakeHandle({'TOOL_DEDUPLICATE_READS': False})
	h.hHM.msgs = [
		{'role': 'tool', 'content': 'same content', 'name': 'ReadFile'},
	]
	ex = StubExecutor(h)
	result, row = ex._dedup_result('ReadFile', 'same content')
	assert row is None
	assert result == 'same content'


def test_dedup_only_applies_to_read_tools():
	h = FakeHandle({'TOOL_DEDUPLICATE_READS': True})
	h.hHM.msgs = [
		{'role': 'tool', 'content': 'same content', 'name': 'WriteFile'},
	]
	ex = StubExecutor(h)
	result, row = ex._dedup_result('WriteFile', 'same content')
	assert row is None
	assert result == 'same content'


def test_dedup_ignores_errors():
	h = FakeHandle({'TOOL_DEDUPLICATE_READS': True})
	h.hHM.msgs = [
		{'role': 'tool', 'content': 'Error: something', 'name': 'ReadFile'},
	]
	ex = StubExecutor(h)
	result, row = ex._dedup_result('ReadFile', 'Error: something')
	assert row is None


def test_ph_format_row_flags_duplicate():
	from src.CommandsSession import _ph_format_row
	seen = set()
	out1 = _ph_format_row(0, {'role': 'tool', 'content': 'abc', 'name': 'ReadFile'}, seen)
	out2 = _ph_format_row(1, {'role': 'tool', 'content': 'abc', 'name': 'ReadFile'}, seen)
	assert 'DUP' in out2
	assert 'DUP' not in out1


def test_ph_format_row_no_flag_without_seen():
	from src.CommandsSession import _ph_format_row
	out = _ph_format_row(0, {'role': 'tool', 'content': 'abc', 'name': 'ReadFile'}, None)
	assert 'DUP' not in out


def test_fire_tool_invocation_deduplicates_read_file(tmp_path):
	"""End-to-end: FireToolInvocation with a duplicate ReadFile returns a notice
	and injects a user reminder."""
	from src.ToolParser import ToolParser

	class _FH:
		def __init__(self):
			self.Options = {
				'MODE': 'build',
				'TOOL_SHOW_LOAD': False,
				'TOOL_RESULT_AS_SYSTEM': False,
				'TOOL_RESULT_AS_USER': False,
				'TOOL_DEDUPLICATE_READS': True,
				'TOOL_TRANSIENT_ENABLED': False,
				'AI_MAX_FILE_SIZE': 2097152,
			}
			self.hTC = type('TC', (), {'handles': {}})()
			self.hLG = FakeLogger()
			self.hHM = type('H', (), {})()
			self.hHM.msgs = []
			self.tool_iteration = 0
			self.tool_errors = 0
			self._last_failed_tool = None
			self._last_failed_tool_count = 0
			self._response_calls = []

		def Response(self, role, opts):
			self._response_calls.append((role, opts))
			self.hHM.msgs.append({
				'role': role,
				'content': opts.get('content', ''),
				'name': opts.get('name', ''),
			})

	class _RT:
		info = {"parameters": {"required": ["fileName"]}}
		def __init__(self):
			self.calls = []
		def run(self, fileName, **kwargs):
			self.calls.append(fileName)
			return "file contents"

	h = _FH()
	h.hTC.handles['ReadFile'] = {'handle': _RT()}
	obj = ToolParser.__new__(ToolParser)
	obj.handle = h

	# First read
	res1 = obj.FireToolInvocation([{'name': 'ReadFile', 'parameters': {'fileName': 'a.txt'}}])
	assert res1 == 'file contents'
	assert h._response_calls[-1] == ('tool', {'content': 'file contents', 'name': 'ReadFile'})

	# Second read returns identical content -> deduplicated
	res2 = obj.FireToolInvocation([{'name': 'ReadFile', 'parameters': {'fileName': 'a.txt'}}])
	assert 'Duplicate result' in res2
	assert 'row 0' in res2
	assert h._response_calls[-2] == ('tool', {'content': res2, 'name': 'ReadFile'})
	assert h._response_calls[-1][0] == 'user'
	assert 'row 0' in h._response_calls[-1][1]['content']
