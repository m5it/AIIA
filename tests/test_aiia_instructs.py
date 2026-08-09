import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PL = "instruct"


def _im_handle():
	class FakeLG:
		def echo(self, *a, **k):
			pass

	class FakeHandle:
		Options = {'INSTRUCT_PATH': PL, 'path': ''}
		hLG = FakeLG()

		def _write_state(self, *a, **k):
			pass

	return FakeHandle()


def test_aiia_instruct_classes_exist_with_category():
	from src.functions import importmodule, initmodule
	for n in ('AIIACoderCompact', 'AIIACoderListTools', 'AIIACoderRole'):
		mod = importmodule(n, False, {'path': PL})
		cls = initmodule(mod, n)
		assert getattr(cls, 'category', 'other') == 'aiia'
		assert cls.plan().strip()
		assert cls.build().strip()


def test_existing_instructs_default_to_other():
	from src.functions import importmodule
	mod = importmodule('Developer', False, {'path': PL})
	assert getattr(getattr(mod, 'Developer'), 'category', 'other') == 'other'


def test_update_groups_by_category():
	from src.InstructManager import InstructManager
	im = InstructManager({'handle': _im_handle()})
	im.Update()
	aiia = [p['class_name'] for p in im.available if p['category'] == 'aiia']
	other = [p['class_name'] for p in im.available if p['category'] == 'other']
	assert set(aiia) == {'AIIACoderCompact', 'AIIACoderListTools', 'AIIACoderRole'}
	assert 'Developer' in other
	assert len(other) >= 17


def test_category_helper():
	from src.InstructManager import InstructManager
	im = InstructManager({'handle': _im_handle()})
	assert im.Category('AIIACoderCompact') == 'aiia'
	assert im.Category('Developer') == 'other'


def test_choose_picks_from_category():
	from unittest.mock import patch
	from src.InstructManager import InstructManager
	h = _im_handle()
	im = InstructManager({'handle': h})
	inputs = ['0', '0']  # category 0 (AIIA) -> first AIIA persona (alphabetical)
	with patch('src.InstructManager.user_input', lambda *a, **k: inputs.pop(0)):
		im.Choose()
	assert h.Options['INSTRUCT_CLASS'] == 'AIIACoderCompact'


def test_choose_cancel_at_category():
	from unittest.mock import patch
	from src.InstructManager import InstructManager
	h = _im_handle()
	im = InstructManager({'handle': h})
	with patch('src.InstructManager.user_input', lambda *a, **k: 'x'):
		im.Choose()
	assert im.choosed is True


def test_tool_training_skipped_for_aiia():
	from src.HandleChat import HandleChat

	class FakeLG:
		def echo(self, *a, **k):
			pass

	class FakeIM:
		def Category(self, name):
			return 'aiia' if name.startswith('AIIA') else 'other'

	class FakeHM:
		msgs = []

	class FakeH:
		hLG = FakeLG()
		hIM = FakeIM()
		hHM = FakeHM()
		Options = {'INSTRUCT_CLASS': 'AIIACoderCompact', 'TOOL_TRAINING': True,
				   'CONTINUE': False, 'MODE': 'build', 'AI_ROW_ID': 0}

		def Response(self, *a, **k):
			self.called = True

		def AI(self):
			self.aicalled = True

	h = FakeH()
	HandleChat._chat_tool_training(h)
	assert not hasattr(h, 'called')
	assert not hasattr(h, 'aicalled')


def test_tool_training_runs_for_other():
	from src.HandleChat import HandleChat

	class FakeLG:
		def echo(self, *a, **k):
			pass

	class FakeIM:
		def Category(self, name):
			return 'aiia' if name.startswith('AIIA') else 'other'

	class FakeHM:
		msgs = []

	class FakeH:
		hLG = FakeLG()
		hIM = FakeIM()
		hHM = FakeHM()
		Options = {'INSTRUCT_CLASS': 'Developer', 'TOOL_TRAINING': True,
				   'CONTINUE': False, 'MODE': 'build', 'AI_ROW_ID': 0}

		def Response(self, *a, **k):
			self.called = True

		def AI(self):
			self.aicalled = True

	h = FakeH()
	HandleChat._chat_tool_training(h)
	assert getattr(h, 'called', False) is True
	assert getattr(h, 'aicalled', False) is True


def test_tool_reference_tip_skipped_for_aiia():
	from src.functions import importmodule, initmodule
	from src.Prepare import Prepare

	class FakeTM:
		def __init__(self):
			self.saved = {}
			self.deleted = []

		def delete(self, t, s):
			self.deleted.append(t)

		def save(self, t, s, entries):
			self.saved[t] = entries

	class FakeH:
		def __init__(self):
			self.hTM = FakeTM()

	h = FakeH()
	cls = initmodule(importmodule('AIIACoderRole', False, {'path': PL}), 'AIIACoderRole')
	Prepare({'handle': h})._save_instruction_tip(cls, 'AIIACoderRole')
	assert 'tool_reference_build' not in h.hTM.saved
	assert 'instruct_aiiacoderrole' in h.hTM.saved


def test_tool_reference_tip_kept_for_other():
	from src.functions import importmodule, initmodule
	from src.Prepare import Prepare

	class FakeTM:
		def __init__(self):
			self.saved = {}
			self.deleted = []

		def delete(self, t, s):
			self.deleted.append(t)

		def save(self, t, s, entries):
			self.saved[t] = entries

	class FakeH:
		def __init__(self):
			self.hTM = FakeTM()

	h = FakeH()
	cls = initmodule(importmodule('Developer', False, {'path': PL}), 'Developer')
	Prepare({'handle': h})._save_instruction_tip(cls, 'Developer')
	assert 'tool_reference_build' in h.hTM.saved
