import os
import tempfile

from tools.tool_AppendFile import AppendFile
from tools.tool_ReadFile import ReadFile


def _write(path, content):
    with open(path, 'w') as f:
        f.write(content)
    return path


def test_append_to_end(tmp_path):
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = AppendFile()
    res = t.run(str(path), 'd')
    assert 'updated with length' in res
    assert open(path).read() == 'a\nb\nc\nd\n'


def test_append_to_end_explicit_minus_one(tmp_path):
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = AppendFile()
    res = t.run(str(path), 'd', fromLineNumber=-1)
    assert 'updated with length' in res
    assert open(path).read() == 'a\nb\nc\nd\n'


def test_prepend_at_start(tmp_path):
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = AppendFile()
    res = t.run(str(path), '0', fromLineNumber=0)
    assert 'updated with length' in res
    assert open(path).read() == '0\na\nb\nc\n'


def test_insert_after_line(tmp_path):
    """fromLineNumber=N inserts after line N (1-indexed)."""
    path = _write(tmp_path / 'f.txt', 'l1\nl2\nl3\n')
    t = AppendFile()
    res = t.run(str(path), 'NEW', fromLineNumber=2)
    assert 'updated with length' in res
    assert open(path).read() == 'l1\nl2\nNEW\nl3\n'


def test_insert_multiline_block(tmp_path):
    """Multi-line content is inserted as a contiguous block."""
    path = _write(tmp_path / 'f.txt', 'def world():\n    print(1)\n')
    t = AppendFile()
    res = t.run(str(path), 'def extra():\n    print(2)', fromLineNumber=1)
    assert open(path).read() == 'def world():\ndef extra():\n    print(2)\n    print(1)\n'


def test_no_file_duplication(tmp_path):
    """AppendFile must overwrite, not append, the assembled content."""
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = AppendFile()
    t.run(str(path), 'x', fromLineNumber=1)
    content = open(path).read()
    assert content.count('a\n') == 1
    assert content == 'a\nx\nb\nc\n'


def test_insert_at_nonexistent_file(tmp_path):
    path = str(tmp_path / 'new.txt')
    t = AppendFile()
    res = t.run(path, 'first')
    assert 'updated with length' in res
    assert open(path).read() == 'first\n'
