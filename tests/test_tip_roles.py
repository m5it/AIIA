import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))


class FakeLogger:
	def echo(self, msg, opts=None):
		pass


class RecordingTipManager:
	def __init__(self):
		self.saved = []

	def delete(self, title, source):
		pass

	def save(self, title, source, entries):
		self.saved.append((title, source, entries))


class FakeHandle:
	def __init__(self):
		self.hTM = RecordingTipManager()
		self.hLG = FakeLogger()
		self._consumed_tips = set()
		self.Options = {'AI_ROW_ID': 1}
		self.responses = []

	def Response(self, role, content_dict):
		self.responses.append((role, content_dict.get('content', '')))


def _make_prepare():
	from src.Prepare import Prepare
	fake = FakeHandle()
	p = Prepare({'handle': fake})
	return p, fake


class FakePersona:
	@staticmethod
	def plan():
		return "plan instructions text"

	@staticmethod
	def build():
		return "build workflow text\nAVAILABLE TOOLS\n- <Terminal>tool docs</Terminal>"


def test_prepare_saves_instruction_tips_as_system():
	p, fake = _make_prepare()
	p._save_instruction_tip(FakePersona, 'FakePersona')
	# All saved entries (both tips) must use role 'system'
	roles = []
	for title, source, entries in fake.hTM.saved:
		assert source == 'model'
		for e in entries:
			roles.append(e['role'])
	assert roles == ['system', 'system', 'system', 'system']
	titles = [t for t, _, _ in fake.hTM.saved]
	assert 'instruct_fakepersona' in titles
	assert 'tool_reference_build' in titles


def test_reinsert_coerces_legacy_model_role():
	from src.TipManager import TipManager
	fake = FakeHandle()
	tm = TipManager({'handle': fake})
	legacy = [{
		'entries': [
			{'role': 'model', 'content': '[PLAN MODE INSTRUCTIONS]\nlegacy'},
			{'role': 'user', 'content': 'plain user note'},
		],
	}]
	tm.get = lambda title, source=None: legacy
	count = tm.reinsert('legacy_tip')
	assert count == 2
	assert fake.responses[0][0] == 'system'
	assert fake.responses[0][1] == '[PLAN MODE INSTRUCTIONS]\nlegacy'
	assert fake.responses[1][0] == 'user'


def test_savetip_writes_system_role(tmp_path, monkeypatch):
	import tool_SaveTip
	monkeypatch.setattr(tool_SaveTip, 'Options', {'TIPS_PATH': str(tmp_path)})
	out = tool_SaveTip.SaveTip().run('test_tip', {}, 'some content')
	assert 'Saved tip' in out
	json_file = os.path.join(str(tmp_path), 'model', 'test_tip')
	files = os.listdir(json_file)
	with open(os.path.join(json_file, files[0])) as f:
		data = json.load(f)
	assert data['entries'][0]['role'] == 'system'
	assert data['entries'][0]['content'] == 'some content'


def test_sanitize_msgs_for_llm():
	from src.HandleChat import _sanitize_msgs_for_llm
	msgs = [
		{'role': 'user', 'content': 'hi'},
		{'role': 'model', 'content': '[PLAN MODE INSTRUCTIONS]\nx'},
		{'role': 'assistant', 'content': 'ok'},
		{'role': 'tool', 'content': 'result'},
		{'role': 'system', 'content': 'sys'},
		{'role': 'weird', 'content': 'drop me'},
		{'content': 'no role'},
		'not a dict',
	]
	out = _sanitize_msgs_for_llm(msgs)
	roles = [m['role'] for m in out]
	assert roles == ['user', 'system', 'assistant', 'tool', 'system']
	assert out[1]['content'] == '[PLAN MODE INSTRUCTIONS]\nx'


def test_updatesitescript_writes_system_role(tmp_path, monkeypatch):
	import tool_UpdateSiteScript
	monkeypatch.setattr(tool_UpdateSiteScript, 'Options', {'TIPS_PATH': str(tmp_path)})
	tool_UpdateSiteScript.UpdateSiteScript()._auto_tip('example.com', 'helper.js', '/some/path/helper.js')
	dest = os.path.join(str(tmp_path), 'model', 'site_script_example_com_helper')
	files = os.listdir(dest)
	with open(os.path.join(dest, files[0])) as f:
		data = json.load(f)
	assert data['entries'][0]['role'] == 'system'
	assert 'helper.js' in data['entries'][0]['content']
