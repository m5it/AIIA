import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class FakeHandle:
	def __init__(self, tmpdir, working_dir=None):
		self.hLG = FakeLogger()
		self._consumed_tips = set()
		self.Options = {
			'AI_ROW_ID': 0,
			'AI_SESS_ID': 42,
			'TIPS_PATH': tmpdir,
			'working_dir': working_dir,
		}
		self._responses = []

	def Response(self, role, content_dict):
		self._responses.append((role, content_dict.get('content', '')))


class _TipHandle(FakeHandle):
	"""Handle with the project key helper and tip summary method."""
	def _project_tip_key(self):
		from src.Handle import Handle
		return Handle._project_tip_key(self)

	def _get_tip_summary(self):
		from src.HandleChat import HandleChat
		return HandleChat._get_tip_summary(self)


def _make_tm(tmpdir, working_dir=None):
	from src.TipManager import TipManager
	h = FakeHandle(tmpdir, working_dir)
	tm = TipManager({'handle': h})
	h.hTM = tm
	return h, tm


def _make_summary_handle(tmpdir, working_dir):
	from src.TipManager import TipManager
	h = _TipHandle(tmpdir, working_dir)
	h.hTM = TipManager({'handle': h})
	return h


def test_save_clear_tip_uses_project_subdir(tmp_path):
	from src.Handle import Handle
	h, tm = _make_tm(str(tmp_path), str(tmp_path / 'proj'))
	h._save_clear_tip = Handle._save_clear_tip.__get__(h, type(h))
	h._project_tip_key = Handle._project_tip_key.__get__(h, type(h))
	h._save_clear_tip('archive_1', 5)
	listed = tm.list()
	assert len(listed) == 1
	key = list(listed.keys())[0]
	assert key.startswith('model/p_')
	assert key.endswith('/session_42_cleared')
	assert listed[key]['count'] == 1


def test_save_clear_tip_falls_back_global_when_no_working_dir(tmp_path):
	from src.Handle import Handle
	h, tm = _make_tm(str(tmp_path), None)
	h._save_clear_tip = Handle._save_clear_tip.__get__(h, type(h))
	h._project_tip_key = Handle._project_tip_key.__get__(h, type(h))
	h._save_clear_tip('archive_1', 5)
	listed = tm.list()
	assert len(listed) == 1
	assert 'model/session_42_cleared' in listed


def test_list_recursively_finds_project_scoped_tips(tmp_path):
	h, tm = _make_tm(str(tmp_path), None)
	# Global tip
	tm.save('site_script_example_com_helper', 'model', [
		{'role': 'system', 'content': 'helper'}
	])
	# Project-scoped tip
	tm.save('session_1_cleared', 'model/p_abc123', [
		{'role': 'system', 'content': 'archive'}
	])
	listed = tm.list()
	assert len(listed) == 2
	assert 'model/site_script_example_com_helper' in listed
	assert 'model/p_abc123/session_1_cleared' in listed


def test_get_searches_project_scoped_tips(tmp_path):
	h, tm = _make_tm(str(tmp_path), None)
	tm.save('session_1_cleared', 'model/p_abc123', [
		{'role': 'system', 'content': 'scoped'}
	])
	entries = tm.get('session_1_cleared')
	assert len(entries) == 1
	assert entries[0]['entries'][0]['content'] == 'scoped'


def test_delete_removes_project_scoped_tips(tmp_path):
	h, tm = _make_tm(str(tmp_path), None)
	tm.save('session_1_cleared', 'model/p_abc123', [
		{'role': 'system', 'content': 'scoped'}
	])
	assert len(tm.list()) == 1
	tm.delete('session_1_cleared')
	assert len(tm.list()) == 0


def test_get_tip_summary_hides_session_tips_from_other_projects(tmp_path):
	h = _make_summary_handle(str(tmp_path), str(tmp_path / 'proj_a'))
	# Own session tip
	h.hTM.save('session_1_cleared', 'model/p_{}'.format(h._project_tip_key()), [
		{'role': 'system', 'content': 'own archive'}
	])
	# Other project's session tip
	h.hTM.save('session_2_cleared', 'model/p_other', [
		{'role': 'system', 'content': 'other archive'}
	])
	# Global reusable tip
	h.hTM.save('site_script_example_com_helper', 'model', [
		{'role': 'system', 'content': 'helper'}
	])
	summary = h._get_tip_summary()
	assert 'session_1_cleared' in summary
	assert 'session_2_cleared' not in summary
	assert 'site_script_example_com_helper' in summary


def test_get_tip_summary_includes_global_session_tip_when_no_project(tmp_path):
	h = _make_summary_handle(str(tmp_path), None)
	h.hTM.save('session_1_cleared', 'model', [
		{'role': 'system', 'content': 'global archive'}
	])
	h.hTM.save('session_2_cleared', 'model/p_other', [
		{'role': 'system', 'content': 'other archive'}
	])
	summary = h._get_tip_summary()
	assert 'session_1_cleared' in summary
	assert 'session_2_cleared' not in summary


def test_get_tip_summary_hides_instruct_tips_from_other_personas(tmp_path):
	h = _make_summary_handle(str(tmp_path), str(tmp_path / 'proj_a'))
	h.Options['INSTRUCT_CLASS'] = 'Developer'
	h.hTM.save('instruct_developer', 'model', [
		{'role': 'system', 'content': 'active persona'}
	])
	h.hTM.save('instruct_booksmith', 'model', [
		{'role': 'system', 'content': 'other persona'}
	])
	h.hTM.save('site_script_example_com_helper', 'model', [
		{'role': 'system', 'content': 'helper'}
	])
	summary = h._get_tip_summary()
	assert 'instruct_developer' in summary
	assert 'instruct_booksmith' not in summary
	assert 'site_script_example_com_helper' in summary


def test_get_tip_summary_shows_no_instruct_tips_when_persona_unknown(tmp_path):
	h = _make_summary_handle(str(tmp_path), str(tmp_path / 'proj_a'))
	h.Options['INSTRUCT_CLASS'] = ''
	h.hTM.save('instruct_developer', 'model', [
		{'role': 'system', 'content': 'persona'}
	])
	summary = h._get_tip_summary()
	assert 'instruct_developer' not in summary


def test_tip_clean_deletes_matching_titles(tmp_path):
	from src.Commands import Commands
	h, tm = _make_tm(str(tmp_path), None)
	h.hTM = tm
	tm.save('session_15_cleared', 'model', [
		{'role': 'system', 'content': 'stale'}
	])
	tm.save('site_script_example_com_helper', 'model', [
		{'role': 'system', 'content': 'keep'}
	])
	cmds = Commands({'handle': h})
	ret = cmds.CMD_TIP_CLEAN('!TIP_CLEAN')
	assert ret == 2
	listed = tm.list()
	assert len(listed) == 1
	assert 'model/site_script_example_com_helper' in listed


def test_tip_clean_custom_pattern(tmp_path):
	from src.Commands import Commands
	h, tm = _make_tm(str(tmp_path), None)
	h.hTM = tm
	tm.save('site_script_example_com_helper', 'model', [
		{'role': 'system', 'content': 'a'}
	])
	tm.save('site_script_github_com_other', 'model', [
		{'role': 'system', 'content': 'b'}
	])
	cmds = Commands({'handle': h})
	ret = cmds.CMD_TIP_CLEAN('!TIP_CLEAN site_script_example_*')
	assert ret == 2
	listed = tm.list()
	assert len(listed) == 1
	assert 'model/site_script_github_com_other' in listed


def test_tool_listtips_finds_project_scoped_tips(tmp_path, monkeypatch):
	import tools.tool_ListTips as tool_ListTips
	monkeypatch.setattr(tool_ListTips, 'Options', type('O', (), {
		'get': lambda self, k, d=None: {'TIPS_PATH': str(tmp_path)}.get(k, d)
	})())
	_, tm = _make_tm(str(tmp_path), None)
	tm.save('global_tip', 'model', [{'role': 'system', 'content': 'g'}])
	tm.save('session_1_cleared', 'model/p_abc123', [{'role': 'system', 'content': 's'}])
	out = tool_ListTips.ListTips().run()
	assert 'global_tip' in out
	assert 'session_1_cleared' in out
	assert 'model/p_abc123' in out


def test_tool_gettip_finds_project_scoped_tips(tmp_path, monkeypatch):
	import tools.tool_GetTip as tool_GetTip
	monkeypatch.setattr(tool_GetTip, 'Options', type('O', (), {
		'get': lambda self, k, d=None: {'TIPS_PATH': str(tmp_path)}.get(k, d)
	})())
	_, tm = _make_tm(str(tmp_path), None)
	tm.save('session_1_cleared', 'model/p_abc123', [{'role': 'system', 'content': 'scoped'}])
	out = tool_GetTip.GetTip().run('session_1_cleared')
	assert 'scoped' in out


def test_tool_deletetip_removes_project_scoped_tips(tmp_path, monkeypatch):
	import tools.tool_DeleteTip as tool_DeleteTip
	monkeypatch.setattr(tool_DeleteTip, 'Options', type('O', (), {
		'get': lambda self, k, d=None: {'TIPS_PATH': str(tmp_path)}.get(k, d)
	})())
	_, tm = _make_tm(str(tmp_path), None)
	tm.save('session_1_cleared', 'model/p_abc123', [{'role': 'system', 'content': 'scoped'}])
	out = tool_DeleteTip.DeleteTip().run('session_1_cleared')
	assert 'Deleted' in out
	assert len(tm.list()) == 0
