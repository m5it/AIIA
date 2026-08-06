import os
import re
import tempfile

from config import Options as _opts
from tools.tool_ReplaceLine import ReplaceLine

# The tool is 0- or 1-indexed depending on config — convert a 1-indexed
# conceptual line number into the tool's line numbering.
ZERO_INDEXED = _opts.get('REPLACELINE_ZERO_INDEXED', False)


def tool_line(n1):
	return n1 - 1 if ZERO_INDEXED else n1


def _write(path, content):
	with open(path, 'w') as f:
		f.write(content)
	return path


def _apply(tool, path, line, replacement):
	return tool.run(fileName=path, fromLine=str(tool_line(line)),
		replacement=replacement, confirmed='true')


def test_preview_leaves_file_unchanged(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='B')
	assert 'currently reads' in res and 'B' in res and 'To apply' in res
	assert open(path).read() == 'a\nb\nc\n'


def test_preview_shows_diff(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\nd\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='B')
	assert 'PREVIEW DIFF' in res
	assert '-b' in res and '+B' in res
	assert open(path).read() == 'a\nb\nc\nd\n'


def test_preview_multiline_diff(tmp_path):
	path = _write(tmp_path / 'f.txt', 'l1\nl2\nl3\nl4\nl5\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(3)),
		toLine=str(tool_line(4)), replacement='X1\nX2')
	assert 'PREVIEW DIFF' in res
	assert '-l3' in res and '-l4' in res and '+X1' in res and '+X2' in res
	assert open(path).read() == 'l1\nl2\nl3\nl4\nl5\n'


def test_preview_no_difference_detected(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='b')
	assert 'no difference detected' in res
	assert 'PREVIEW DIFF' in res


def test_indent_warning_on_depth_mismatch(tmp_path):
	path = _write(tmp_path / 'f.txt', 'def f():\n    return 1\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='  return 2')
	assert 'PREVIEW DIFF' in res
	assert 'indented at level' in res
	assert open(path).read() == 'def f():\n    return 1\n'


def test_indent_warning_on_mixed_tabs_spaces(tmp_path):
	path = _write(tmp_path / 'f.txt', 'def f():\n    return 1\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='\t return 2')
	assert 'mixes tabs and spaces' in res
	assert open(path).read() == 'def f():\n    return 1\n'


def test_indent_no_warning_when_matching(tmp_path):
	path = _write(tmp_path / 'f.txt', 'def f():\n    return 1\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)), replacement='    return 2')
	assert 'PREVIEW DIFF' in res
	assert 'indented at level' not in res


def test_indent_warning_on_verification_diff(tmp_path):
	path = _write(tmp_path / 'f.txt', 'def f():\n    return 1\n')
	t = ReplaceLine()
	res = _apply(t, str(path), 2, '  return 2')
	assert 'VERIFICATION DIFF' in res
	assert 'indented at level' in res
	assert open(path).read() == 'def f():\n  return 2\n'


def test_apply_shows_diff_creates_backup_and_pending(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\nd\n')
	t = ReplaceLine()
	res = _apply(t, str(path), 2, 'B')
	assert open(path).read() == 'a\nB\nc\nd\n'
	assert 'VERIFICATION DIFF' in res
	assert '-b' in res and '+B' in res
	assert 'finalize' in res and 'revert' in res
	assert t._backup_path and os.path.exists(t._backup_path)


def test_finalize_keeps_change_and_removes_backup(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\nd\n')
	t = ReplaceLine()
	_apply(t, str(path), 2, 'B')
	backup = t._backup_path
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)),
		replacement='B', confirmed='finalize')
	assert 'Finalized' in res
	assert open(path).read() == 'a\nB\nc\nd\n'
	assert not os.path.exists(backup)
	assert t._backup_path is None


def test_revert_restores_original_file(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\nd\n')
	t = ReplaceLine()
	_apply(t, str(path), 2, 'B')
	backup = t._backup_path
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)),
		replacement='B', confirmed='revert')
	assert 'Reverted' in res
	assert open(path).read() == 'a\nb\nc\nd\n'
	assert not os.path.exists(backup)
	assert t._backup_path is None


def test_confirm_without_pending_errors(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)),
		replacement='B', confirmed='finalize')
	assert 'no pending replacement' in res
	res = t.run(fileName=str(path), fromLine=str(tool_line(2)),
		replacement='B', confirmed='revert')
	assert 'no pending replacement' in res


def test_range_and_multiline_replace(tmp_path):
	path = _write(tmp_path / 'f.txt', 'l1\nl2\nl3\nl4\nl5\n')
	t = ReplaceLine()
	res = t.run(fileName=str(path), fromLine=str(tool_line(3)),
		toLine=str(tool_line(4)), replacement='X1\nX2', confirmed='true')
	assert open(path).read() == 'l1\nl2\nX1\nX2\nl5\n'
	assert '-l3' in res and '-l4' in res and '+X1' in res and '+X2' in res


def test_file_changed_since_preview_forces_fresh_preview(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
	t = ReplaceLine()
	line = str(tool_line(2))
	t.run(fileName=str(path), fromLine=line, replacement='B')
	with open(path, 'a') as f:
		f.write('external\n')
	res = t.run(fileName=str(path), fromLine=line, replacement='B', confirmed='true')
	assert 'File changed since preview' in res
	assert open(path).read().endswith('external\n')


def test_diff_fallback_when_diff_unavailable(tmp_path, monkeypatch):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\nd\n')
	t = ReplaceLine()

	def _boom(*a, **k):
		raise OSError('diff not available')

	monkeypatch.setattr('tools.tool_ReplaceLine.subprocess.run', _boom)
	res = _apply(t, str(path), 2, 'B')
	assert 'VERIFICATION DIFF' in res
	assert '-b' in res and '+B' in res


def test_backup_lives_in_tmpdir(tmp_path):
	path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
	t = ReplaceLine()
	_apply(t, str(path), 2, 'B')
	assert t._backup_path.startswith(tempfile.gettempdir())
	assert re.match(r'.*replaceline_.*\.bak$', t._backup_path)
