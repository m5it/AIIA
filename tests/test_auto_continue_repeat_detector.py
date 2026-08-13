import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_try_auto_continue_resets_last_response_hash(tmp_path):
	from src.HandleChat import HandleChat
	from src.PlanManager import PlanBase, Plan

	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'MODE': 'build',
				'AUTO_CONTINUE_TASKS': True,
				'plans_path': str(tmp_path / 'plans'),
				'working_dir': str(tmp_path),
			}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._write_current_task = lambda: None
			self._last_response_hash = 'previous_hash'

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Do the thing', 'Thing')
	t1.status = 'in_progress'

	stub = Stub()
	r = stub._try_auto_continue()
	assert r is True
	assert stub._last_response_hash is None
	assert stub.responses[-1][0] == 'user'

	PlanBase.draft = None


def test_auto_build_reenter_resets_last_response_hash(tmp_path):
	from src.HandleChat import HandleChat
	from src.PlanManager import PlanBase, Plan

	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'MODE': 'build',
				'plans_path': str(tmp_path / 'plans'),
				'working_dir': str(tmp_path),
			}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._write_current_task = lambda: None
			self._last_response_hash = 'previous_hash'

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Do the thing', 'Thing')
	t1.status = 'in_progress'

	stub = Stub()
	count, reenter = stub._auto_build_reenter(1)
	assert reenter is True
	assert stub._last_response_hash is None
	assert stub.responses[-1][0] == 'user'

	PlanBase.draft = None


def test_auto_continue_plan_resets_last_response_hash(tmp_path):
	from src.HandleChat import HandleChat

	class Stub(HandleChat):
		def __init__(self):
			self.Options = {
				'MODE': 'plan',
				'AUTO_CONTINUE_ALL_TASKS': True,
				'plans_path': str(tmp_path / 'plans'),
				'working_dir': str(tmp_path),
			}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.bg_log = lambda *a, **k: None
			self._last_response_hash = 'previous_hash'
			self._last_ai_had_tools = True

		def _is_plan_complete(self):
			return False

	stub = Stub()
	count, reenter = stub._handle_auto_continue(0)
	assert reenter is True
	assert stub._last_response_hash is None
	assert stub.responses[-1][0] == 'user'
