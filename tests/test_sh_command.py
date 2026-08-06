import os, sys
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
	assert info['regex'] == r'^!RH\s+\d+$'
	assert info['usage'] == '!RH <row_num>'
	assert info['func'] == c.CMD_REMOVE


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
