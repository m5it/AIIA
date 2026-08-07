import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FakeHistory:
	def __init__(self, msgs):
		self.msgs = msgs


class FakeHandle:
	def __init__(self, msgs):
		self.hHM = FakeHistory(msgs)


def _msgs():
	return [
		{'role': 'system', 'content': 'MODE: BUILD', 'name': ''},
		{'role': 'user', 'content': 'check the network config', 'name': ''},
		{'role': 'assistant', 'content': 'I will read fw.sh', 'thinking': 'need to inspect the firewall rules', 'name': ''},
		{'role': 'tool', 'content': '=== nftables ruleset ===', 'name': 'Terminal'},
		{'role': 'user', 'content': 'now remove DROP rule', 'name': ''},
	]


def _make(msgs=None):
	from src.Commands import Commands
	c = Commands({'handle': FakeHandle(_msgs() if msgs is None else msgs)})
	return c, c.handle


def _make_handle(msgs, tmp_path):
	"""Fake handle with Options + history dir, for commands that touch disk."""
	h = type('H', (), {})()
	h.hHM = FakeHistory(msgs)
	h.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
	h.Options = {
		'path': str(tmp_path),
		'AI_FILE_HISTORY': 'test_sess.dbk',
		'working_dir': None,
		'AI_SESS_PREFIX': '',
		'AI_SESS_ID': 0,
	}
	(tmp_path / 'history').mkdir(exist_ok=True)
	return h


def test_sh_registered():
	c, _ = _make()
	assert 'SH' in c.cmds
	info = c.cmds['SH']
	assert info['regex'] == r'^!SH(\s+.+)?$'
	assert info['func'] == c.CMD_SEARCH_HISTORY


def test_sh_search_substring_case_insensitive():
	from src.CommandsSession import _ph_search
	msgs = _msgs()
	assert _ph_search(msgs, 'NETWORK') == [(1, msgs[1])]
	assert _ph_search(msgs, 'network') == [(1, msgs[1])]
	assert _ph_search(msgs, 'fw.sh') == [(2, msgs[2])]


def test_sh_search_matches_thinking_and_tool_name():
	from src.CommandsSession import _ph_search
	msgs = _msgs()
	assert _ph_search(msgs, 'firewall') == [(2, msgs[2])]
	assert _ph_search(msgs, 'terminal') == [(3, msgs[3])]
	assert _ph_search(msgs, 'drop') == [(4, msgs[4])]


def test_sh_search_regex():
	from src.CommandsSession import _ph_search
	msgs = _msgs()
	assert _ph_search(msgs, r'^check|^now', regex=True) == [(1, msgs[1]), (4, msgs[4])]
	assert _ph_search(msgs, r'\d+', regex=True) == []


def test_sh_search_no_match():
	from src.CommandsSession import _ph_search
	assert _ph_search(_msgs(), 'zzz_not_here') == []


def test_sh_invalid_regex_prints_error(capsys):
	from src.CommandsSession import _ph_search
	out = _ph_search(_msgs(), r'[unclosed', regex=True)
	assert out == []
	assert 'Invalid regex' in capsys.readouterr().out


def test_sh_cmd_usage(capsys):
	c, _ = _make()
	ret = c.CMD_SEARCH_HISTORY('!SH')
	assert ret == 2
	assert 'Usage' in capsys.readouterr().out


def test_sh_cmd_no_matches(capsys):
	c, _ = _make()
	ret = c.CMD_SEARCH_HISTORY('!SH zzz_not_here')
	assert ret == 2
	assert 'No matches' in capsys.readouterr().out


def test_sh_cmd_prints_row_indexes(capsys):
	c, _ = _make()
	ret = c.CMD_SEARCH_HISTORY('!SH drop')
	assert ret == 2
	out = capsys.readouterr().out
	assert '1 match(es)' in out
	# Row number printed must match msgs index so !RH <N> works
	assert '  4 ' in out
	assert '  2 ' not in out


def test_remove_command_renamed_to_rh():
	c, _ = _make()
	info = c.cmds['REMOVE']
	assert info['regex'] == r'^!RH\s+\d+(\s+\d+)?$'
	assert info['usage'] == '!RH <row_num> | !RH <from_row> <to_row>'
	assert info['func'] == c.CMD_REMOVE


def test_remove_single_row(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_REMOVE('!RH 2')
	assert ret == 2
	assert [m['role'] for m in h.hHM.msgs] == ['system', 'user', 'tool', 'user']


def test_remove_range_removes_inclusive(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_REMOVE('!RH 1 3')
	assert ret == 2
	assert [m['role'] for m in h.hHM.msgs] == ['system', 'user']


def test_remove_range_swaps_order(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_REMOVE('!RH 3 1')
	assert ret == 2
	assert [m['role'] for m in h.hHM.msgs] == ['system', 'user']


def test_remove_range_out_of_bounds(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_REMOVE('!RH 0 99')
	assert ret == 2
	assert len(h.hHM.msgs) == 5
	assert 'out of range' in capsys.readouterr().out


def test_remove_too_many_args_usage(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_REMOVE('!RH 1 2 3')
	assert ret == 2
	assert 'Usage' in capsys.readouterr().out
	assert len(h.hHM.msgs) == 5


def test_remove_range_rebuilds_history_file(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	c.CMD_REMOVE('!RH 1 3')
	p = tmp_path / 'history' / 'test_sess.dbk'
	assert p.exists()
	lines = [l for l in p.read_text().strip().split('\n') if l]
	assert len(lines) == 2
	assert all(json.loads(l)['role'] == m['role'] for l, m in zip(lines, h.hHM.msgs))


def test_save_history_registered():
	c, _ = _make()
	assert 'SAVE_HISTORY' in c.cmds
	info = c.cmds['SAVE_HISTORY']
	assert info['regex'] == r'^!SAVE_HISTORY(\s+\S+)?$'
	assert info['usage'] == '!SAVE_HISTORY [filename]'
	assert info['func'] == c.CMD_SAVE_HISTORY


def test_save_history_writes_both_copies(tmp_path):
	from src.Commands import Commands
	from src.HistoryManager import HistoryManager
	msgs = _msgs()
	h = _make_handle(msgs, tmp_path)
	h.Options['AI_SESS_PREFIX'] = 'abc12345'
	h.Options['AI_SESS_ID'] = 7
	c = Commands({'handle': h})
	ret = c.CMD_SAVE_HISTORY('!SAVE_HISTORY')
	assert ret == 2
	saves = [f for f in (tmp_path / 'history').iterdir() if '.save.' in f.name]
	assert len(saves) == 1
	assert (tmp_path / saves[0].name).exists()
	loaded = [json.loads(l) for l in saves[0].read_text().strip().split('\n') if l]
	assert len(loaded) == len(msgs)
	assert [m['role'] for m in loaded] == [m['role'] for m in msgs]
	hm = HistoryManager({'handle': h, 'quiet': True, 'path': str(tmp_path / 'history')})
	hm.Get(path=str(saves[0]))
	assert len(hm.msgs) == len(msgs)


def test_save_history_custom_filename(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_SAVE_HISTORY('!SAVE_HISTORY myexport.md')
	assert ret == 2
	assert (tmp_path / 'history' / 'myexport.md').exists()
	assert (tmp_path / 'myexport.md').exists()


def test_save_history_does_not_clobber_active(tmp_path):
	from src.Commands import Commands
	h = _make_handle(_msgs(), tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_SAVE_HISTORY('!SAVE_HISTORY test_sess.dbk')
	assert ret == 2
	assert (tmp_path / 'history' / 'save_test_sess.dbk').exists()
	assert (tmp_path / 'save_test_sess.dbk').exists()


def test_save_history_no_history(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_handle([], tmp_path)
	c = Commands({'handle': h})
	ret = c.CMD_SAVE_HISTORY('!SAVE_HISTORY')
	assert ret == 2
	assert 'No history' in capsys.readouterr().out


def _make_history_handle(msgs, tmp_path):
	"""Fake handle whose hHM is a real HistoryManager (for !AH search)."""
	from src.HistoryManager import HistoryManager
	h = _make_handle(msgs, tmp_path)
	h.hHM = HistoryManager({'handle': h, 'quiet': False, 'path': str(tmp_path / 'history')})
	return h


def _write_history_file(tmp_path, fname, content):
	(tmp_path / 'history' / fname).write_text(
		'{}\n'.format(json.dumps({'role': 'user', 'content': content, 'name': ''})))


def test_ah_registered():
	c, _ = _make()
	assert 'VIEW_HISTORY' in c.cmds
	info = c.cmds['VIEW_HISTORY']
	assert info['regex'] == r'^!AH(\s+.+)?$'
	assert info['usage'] == '!AH [search_term]'
	assert info['func'] == c.CMD_VIEW_HISTORY


def test_ah_search_finds_matching_history(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_history_handle([], tmp_path)
	_write_history_file(tmp_path, 'abc12345_7.dbk', 'template matching firewall config')
	_write_history_file(tmp_path, 'abc12345_8.dbk', 'unrelated setup notes')
	c = Commands({'handle': h})
	ret = c.CMD_VIEW_HISTORY('!AH template')
	assert ret == 2
	out = capsys.readouterr().out
	assert 'abc12345_7.dbk' in out
	assert 'abc12345_8.dbk' not in out


def test_ah_search_case_insensitive(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_history_handle([], tmp_path)
	_write_history_file(tmp_path, 'abc12345_7.dbk', 'deploy the TEMPLATE stack')
	c = Commands({'handle': h})
	c.CMD_VIEW_HISTORY('!AH template')
	assert 'abc12345_7.dbk' in capsys.readouterr().out


def test_ah_search_no_match(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_history_handle([], tmp_path)
	_write_history_file(tmp_path, 'abc12345_7.dbk', 'template notes')
	c = Commands({'handle': h})
	ret = c.CMD_VIEW_HISTORY('!AH zzz_not_here')
	assert ret == 2
	assert 'No history files matching' in capsys.readouterr().out


def test_ah_lists_all_history(tmp_path, capsys):
	from src.Commands import Commands
	h = _make_history_handle([], tmp_path)
	_write_history_file(tmp_path, 'abc12345_7.dbk', 'first session')
	_write_history_file(tmp_path, 'abc12345_8.dbk', 'second session')
	c = Commands({'handle': h})
	ret = c.CMD_VIEW_HISTORY('!AH')
	assert ret == 2
	out = capsys.readouterr().out
	assert 'abc12345_7.dbk' in out
	assert 'abc12345_8.dbk' in out


def test_sh_cmd_regex_flag(capsys):
	c, _ = _make()
	ret = c.CMD_SEARCH_HISTORY('!SH -r ^check')
	assert ret == 2
	out = capsys.readouterr().out
	assert 'REGEX' in out
	assert '  1 ' in out


def test_ph_format_row_contains_index():
	from src.CommandsSession import _ph_format_row
	msgs = _msgs()
	line = _ph_format_row(3, msgs[3])
	assert '  3 ' in line
	assert 'Terminal' in line


def test_ph_format_row_shows_size():
	from src.CommandsSession import _ph_format_row
	msgs = _msgs()
	line = _ph_format_row(2, msgs[2])
	assert ' chars' in line
	assert '{} chars'.format(len(msgs[2]['content'])) in line
	big = {'role': 'assistant', 'content': 'x' * 12345, 'name': ''}
	assert '12345 chars' in _ph_format_row(0, big)


def test_ph_row_view_shows_size(capsys):
	from src.CommandsSession import _ph_row_view
	msgs = _msgs()
	_ph_row_view(msgs, 1)
	out = capsys.readouterr().out
	assert '{} chars'.format(len(msgs[1]['content'])) in out
	assert 'crc32b:' in out


def test_ph_list_view_returns_2(capsys):
	# Regression: bare !PH crashed the Chat() loop because _ph_list_view
	# returned None (None >= 3 in HandleChat.Chat())
	from src.CommandsSession import _ph_list_view
	assert _ph_list_view(_msgs()) == 2
	out = capsys.readouterr().out
	assert 'CHAT HISTORY' in out


def test_ph_cmd_returns_int_for_all_forms(capsys):
	c, _ = _make()
	assert c.CMD_PREVIEW_HISTORY('!PH') == 2
	assert c.CMD_PREVIEW_HISTORY('!PH 2') == 2


def test_you_dispatch_coerces_none_to_2():
	# Any command that forgets a return must not crash the loop
	from src.HandleChat import HandleChat
	c, _ = _make()
	hc = HandleChat()
	hc.cmds = c
	hc.cmds.cmds = dict(hc.cmds.cmds)
	hc.cmds.cmds['BROKEN'] = {
		'name': 'Broken',
		'description': 'returns None',
		'regex': r'^!BROKEN$',
		'usage': '!BROKEN',
		'func': lambda inp: None,
	}
	assert hc.You('!BROKEN') == 2
