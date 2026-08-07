import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


def test_list_tool_path_concatenation(tmp_path):
	"""List must not concatenate filenames without a separator."""
	from tools.tool_List import List
	lst = List()
	(tmp_path / 'game_logic.py').write_text('x')
	(tmp_path / 'PLAN.md').write_text('y')
	(tmp_path / 'sub').mkdir()

	result = lst.run('.', {'hiddenpath': str(tmp_path)})
	# Check visible paths are clean, not dot-prefixed
	visible = {v['fullpath'] for v in result.values()}
	assert 'game_logic.py' in visible
	assert 'PLAN.md' in visible
	assert '.game_logic.py' not in visible
	assert '.PLAN.md' not in visible
	# Check the real path used for stat is correct
	for entry in result.values():
		if entry['fullpath'] == 'game_logic.py':
			assert entry['type'] == 'file'


def test_list_tool_subpath_concatenation(tmp_path):
	"""List must join hiddenpath + visible path correctly for subdirs."""
	from tools.tool_List import List
	lst = List()
	(tmp_path / 'sub').mkdir()
	(tmp_path / 'sub' / 'a.py').write_text('x')

	result = lst.run('sub', {'hiddenpath': str(tmp_path)})
	visible = {v['fullpath'] for v in result.values()}
	sep = os.sep
	assert 'sub{}a.py'.format(sep) in visible
	for entry in result.values():
		if entry['fullpath'].endswith('a.py'):
			assert entry['type'] == 'file'


def test_list_tool_no_hiddenpath():
	"""List without hiddenpath should still work for current directory."""
	from tools.tool_List import List
	lst = List()
	# Empty path or '.' should default to current directory
	result = lst.run('.', {})
	assert isinstance(result, dict)
	result2 = lst.run('', {})
	assert isinstance(result2, dict)
