import os
import tempfile

import pytest

from config import Options
from tools.tool_ReadFile import ReadFile


def _write(path, content):
    with open(path, 'w') as f:
        f.write(content)
    return path


def test_readfile_basic(tmp_path):
    path = _write(tmp_path / 'f.txt', 'line1\nline2\nline3\n')
    t = ReadFile()
    res = t.run(str(path))
    assert 'line1' in res
    assert 'line2' in res
    assert 'line3' in res


def test_readfile_linenumbers(tmp_path):
    path = _write(tmp_path / 'f.txt', 'line1\nline2\nline3\n')
    t = ReadFile()
    res = t.run(str(path), lineNumbers='true')
    assert '1: line1' in res
    assert '2: line2' in res
    assert '3: line3' in res


def test_readfile_linenumbers_match_replaceline_count(tmp_path):
    """ReadFile lineNumbers count must match ReplaceLine's 1-indexed view."""
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = ReadFile()
    res = t.run(str(path), lineNumbers='true')
    lines = [ln for ln in res.splitlines() if ln.strip()]
    # last numbered line should be 3: c
    assert lines[-1].startswith('3: c')


def test_readfile_linenumbers_with_offset(tmp_path):
    content = '\n'.join('line{}'.format(i) for i in range(1, 21))
    path = _write(tmp_path / 'f.txt', content)
    t = ReadFile()
    res = t.run(str(path), offset=len('line1\nline2\nline3\n'), lineNumbers='true')
    # offset starts at the beginning of line 4
    assert '4: line4' in res
    assert res.startswith(' 4: line4')


def test_readfile_linenumbers_with_lines_limit(tmp_path):
    path = _write(tmp_path / 'f.txt', 'l1\nl2\nl3\nl4\nl5\n')
    t = ReadFile()
    res = t.run(str(path), lines='3', lineNumbers='true')
    lines = res.splitlines()
    assert '1: l1' in res
    assert '2: l2' in res
    assert '3: l3' in res
    assert '4: l4' not in res


def test_readfile_default_line_numbers_enabled(tmp_path, monkeypatch):
    """With READFILE_LINENUMBERS=True (default), ReadFile returns numbered lines."""
    monkeypatch.setitem(Options, 'READFILE_LINENUMBERS', True)
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = ReadFile()
    res = t.run(str(path))
    assert '1: a' in res
    assert '2: b' in res
    assert '3: c' in res


def test_readfile_explicit_false_overrides_config(tmp_path, monkeypatch):
    """lineNumbers='false' overrides a global True default."""
    monkeypatch.setitem(Options, 'READFILE_LINENUMBERS', True)
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = ReadFile()
    res = t.run(str(path), lineNumbers='false')
    assert '1: a' not in res
    assert res.startswith('a\n')


def test_readfile_default_line_numbers_disabled(tmp_path, monkeypatch):
    """With READFILE_LINENUMBERS=False, ReadFile returns plain text by default."""
    monkeypatch.setitem(Options, 'READFILE_LINENUMBERS', False)
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = ReadFile()
    res = t.run(str(path))
    assert '1: a' not in res
    assert res.startswith('a\n')


def test_readfile_explicit_true_overrides_config(tmp_path, monkeypatch):
    """lineNumbers='true' overrides a global False default."""
    monkeypatch.setitem(Options, 'READFILE_LINENUMBERS', False)
    path = _write(tmp_path / 'f.txt', 'a\nb\nc\n')
    t = ReadFile()
    res = t.run(str(path), lineNumbers='true')
    assert '1: a' in res
    assert '3: c' in res
