import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class _MockTP:
	"""Simple tool-invocation dispatcher used by HandleParse stubs."""
	def __init__(self, return_value):
		self.return_value = return_value

	def FireToolInvocation(self, invocations):
		return self.return_value


def _stub_handle_parse(tmp_path, return_value, mode='build'):
	from src.HandleParse import HandleParse

	class Stub(HandleParse):
		def __init__(self):
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self.Options = {'MODE': mode, 'plans_path': str(tmp_path / 'plans')}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hTP = _MockTP(return_value)
			self._write_current_task = lambda: None
	return Stub()


def _make_plan_with_tasks():
	from src.PlanManager import PlanBase, Plan
	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t2 = PlanBase.draft.createTask('Task two instruction', 'Task two')
	return t1.id, t2.id


def test_nexttask_includes_task_id_in_user_message(tmp_path):
	from src.PlanManager import PlanBase

	t1_id, t2_id = _make_plan_with_tasks()
	# First task already in progress; nextTask returns the second task.
	stub = _stub_handle_parse(tmp_path, "NEXT_TASK|{}|Task 2/2 - Task two instruction".format(t2_id))
	r = stub._fire_tool_invocations([{'name': 'nextTask', 'parameters': {}}],
		{'content': 'ok'}, None, None)
	assert r is not None
	assert stub.responses[-1][0] == 'user'
	content = stub.responses[-1][1]['content']
	assert content.startswith('<nextTask>\n\n')
	assert "Task ID: {}".format(t2_id) in content
	assert "Status: in_progress" in content
	assert "Your task:" in content
	assert "Task two instruction" in content
	PlanBase.draft = None



def test_startbuild_includes_task_id_in_system_message(tmp_path):
	from src.PlanManager import PlanBase

	t1_id, _ = _make_plan_with_tasks()
	stub = _stub_handle_parse(tmp_path, "START_BUILD|{}|Task 1/2|Task one instruction".format(t1_id))
	r = stub._fire_tool_invocations([{'name': 'startBuild', 'parameters': {}}],
		{'content': 'ok'}, None, None)
	assert stub.responses[-1][0] == 'system'
	content = stub.responses[-1][1]['content']
	assert "Mode changed to BUILD" in content
	assert "Task ID: {}".format(t1_id) in content
	assert "Task 1/2" in content
	assert "Task one instruction" in content
	PlanBase.draft = None


def test_startbuild_backwards_compatible_with_three_fields(tmp_path):
	from src.PlanManager import PlanBase

	t1_id, _ = _make_plan_with_tasks()
	stub = _stub_handle_parse(tmp_path, "START_BUILD|Task 1/2|Task one instruction")
	stub._fire_tool_invocations([{'name': 'startBuild', 'parameters': {}}],
		{'content': 'ok'}, None, None)
	content = stub.responses[-1][1]['content']
	assert "Mode changed to BUILD" in content
	assert "Task 1/2" in content
	assert "Task one instruction" in content
	PlanBase.draft = None


def test_logprogress_uses_explicit_task_id(tmp_path):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t1.status = 'in_progress'
	result = PlanBase.LogProgress(t1.id, 'did work', str(tmp_path / 'plans'))
	assert result['task_id'] == t1.id
	assert result['logged'] == 'did work'
	assert result['log_entries'] == 1
	PlanBase.draft = None


def test_logprogress_falls_back_to_current_in_progress_task(tmp_path):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t1.status = 'in_progress'
	result = PlanBase.LogProgress('wrong_id', 'did work anyway', str(tmp_path / 'plans'))
	assert result['task_id'] == t1.id
	assert result['logged'] == 'did work anyway'
	assert result['log_entries'] == 1
	assert result['note'] == "Task ID not found; logged to current in_progress task"
	PlanBase.draft = None


def test_logprogress_returns_error_when_no_active_plan(tmp_path):
	from src.PlanManager import PlanBase

	PlanBase.draft = None
	result = PlanBase.LogProgress('some_id', 'work', str(tmp_path / 'plans'))
	assert 'error' in result
	assert 'Task not found' in result['error']


def test_autoclean_nexttask_anchor_matches_new_format():
	from src.HandleContext import HandleContext

	stub = type('Stub', (), {})()
	stub._is_nexttask_msg = lambda m: HandleContext._is_nexttask_msg(stub, m)
	new_format = {
		'role': 'user',
		'content': '<nextTask>\n\nTask ID: 123.456\nStatus: in_progress\n\nYour task:\nDo thing'
	}
	old_format = {
		'role': 'user',
		'content': '<nextTask>\n\nYour task:\nDo thing'
	}
	assert stub._is_nexttask_msg(new_format)
	assert stub._is_nexttask_msg(old_format)
	assert not stub._is_nexttask_msg({'role': 'assistant', 'content': '<nextTask>\n\nDo thing'})


def test_try_auto_continue_includes_task_id(tmp_path):
	from src.HandleChat import HandleChat
	from src.PlanManager import PlanBase, Plan

	class Stub(HandleChat):
		def __init__(self):
			self.Options = {'plans_path': str(tmp_path / 'plans'), 'MODE': 'build'}
			self.responses = []
			self.Response = lambda role, content: self.responses.append((role, content))
			self.hLG = type('LG', (), {'echo': lambda *a, **k: None})()
			self._write_current_task = lambda: None
			self.bg_log = lambda *a, **k: None

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t1.status = 'in_progress'
	stub = Stub()
	stub._try_auto_continue()
	assert stub.responses[-1][0] == 'user'
	content = stub.responses[-1][1]['content']
	assert content.startswith('<nextTask>\n\n')
	assert "Task ID: {}".format(t1.id) in content
	assert "Status: in_progress" in content
	assert "continue task 1 / 1" in content
	PlanBase.draft = None


def test_jobdone_updates_plan_md_to_completed(tmp_path):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	PlanBase.draft.title = 'Test Plan'
	PlanBase.draft.instructions = 'Test instructions'
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t1.status = 'in_progress'
	(t1).__class__ = t1.__class__

	working_dir = str(tmp_path / 'project')
	os.makedirs(working_dir, exist_ok=True)
	plans_path = str(tmp_path / 'plans')
	os.makedirs(plans_path, exist_ok=True)

	# Save plan + PLAN.md as in-progress first
	PlanBase.draft.save(plans_path)
	from src.PlanSaver import PlanSaver
	PlanSaver.save_plan(PlanBase.draft, working_dir)

	plan_md_path = os.path.join(working_dir, 'PLAN.md')
	with open(plan_md_path) as f:
		before = f.read()
	assert '## Status: in_progress' in before

	class StubHandle:
		Options = {'working_dir': working_dir}
		file_buffer_cache = {}

	PlanBase.draft.jobDone(StubHandle())

	with open(plan_md_path) as f:
		after = f.read()
	assert '## Status: completed' in after
	PlanBase.draft = None


def _make_plan_command(tmp_path, mode='build', htp_return='NEXT_TASK|t2|Task 2/2 - Task two instruction'):
	from src.CommandsPlan import CommandsPlan

	class StubHandle:
		Options = {
			'MODE': mode,
			'plans_path': str(tmp_path / 'plans'),
		}
		responses = []
		wct_called = False

		@staticmethod
		def Response(role, content):
			StubHandle.responses.append((role, content))

		@staticmethod
		def _write_current_task():
			StubHandle.wct_called = True

	class StubTP:
		def __init__(self, return_value):
			self.return_value = return_value

		def HandlePlanTool(self, name, params):
			self.last_name = name
			self.last_params = params
			# When requested, actually advance the plan so tests verify state
			if name == 'nextTask':
				from src.PlanManager import PlanBase
				if PlanBase.draft:
					result = PlanBase.draft.nextTask(StubHandle, params.get('status', 'completed'))
					if result.get('done'):
						if result.get('blocked_count', 0):
							return "DONE_WITH_BLOCKED:{}".format(result.get('message', 'Some tasks blocked'))
						return "ALL_COMPLETED:Plan finished successfully"
					return "NEXT_TASK|{}|{}".format(
						result.get('current_task_id', ''),
						result.get('next_task_instruction', ''))
			return self.return_value

	stub_handle = StubHandle()
	stub_handle.hTP = StubTP(htp_return)
	cmd = CommandsPlan()
	cmd.handle = stub_handle
	return cmd, stub_handle


def test_plan_next_no_active_plan(tmp_path, capsys):
	from src.PlanManager import PlanBase
	PlanBase.draft = None

	cmd, handle = _make_plan_command(tmp_path)
	ret = cmd._plan_next(str(tmp_path / 'plans'), str(tmp_path))

	assert ret == 2
	assert 'No active plan' in capsys.readouterr().out
	assert len(handle.responses) == 0


def test_plan_next_in_plan_mode(tmp_path, capsys):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	PlanBase.draft.createTask('Task one instruction', 'Task one')
	cmd, handle = _make_plan_command(tmp_path, mode='plan')
	ret = cmd._plan_next(str(tmp_path / 'plans'), str(tmp_path))

	assert ret == 2
	assert 'Use !START_BUILD first' in capsys.readouterr().out
	assert len(handle.responses) == 0
	PlanBase.draft = None


def test_plan_next_no_task_in_progress(tmp_path, capsys):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	PlanBase.draft.createTask('Task one instruction', 'Task one')
	cmd, handle = _make_plan_command(tmp_path)
	ret = cmd._plan_next(str(tmp_path / 'plans'), str(tmp_path))

	assert ret == 2
	assert 'No task in progress' in capsys.readouterr().out
	assert len(handle.responses) == 0
	PlanBase.draft = None


def test_plan_next_advances_and_injects_prompt(tmp_path, capsys):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t2 = PlanBase.draft.createTask('Task two instruction', 'Task two')
	t1.status = 'in_progress'

	cmd, handle = _make_plan_command(tmp_path, htp_return='NEXT_TASK|{}|Task 2/2 - Task two instruction'.format(t2.id))
	ret = cmd._plan_next(str(tmp_path / 'plans'), str(tmp_path))

	assert ret == 0
	assert handle.wct_called

	# First response: user message showing the model what the user did
	assert handle.responses[0][0] == 'user'
	assert 'User called <nextTask>completed</nextTask>' in handle.responses[0][1]['content']

	# Second response: next task prompt
	assert handle.responses[1][0] == 'user'
	content = handle.responses[1][1]['content']
	assert content.startswith('<nextTask>\n\n')
	assert 'Task ID: {}'.format(t2.id) in content
	assert 'Status: in_progress' in content
	assert 'Task two instruction' in content

	# Plan state updated
	assert t1.status == 'completed'
	assert t2.status == 'in_progress'
	PlanBase.draft = None


def test_plan_next_all_completed(tmp_path, capsys):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t1.status = 'in_progress'

	cmd, handle = _make_plan_command(tmp_path, htp_return='ALL_COMPLETED:Plan finished successfully')
	ret = cmd._plan_next(str(tmp_path / 'plans'), str(tmp_path))

	assert ret == 0
	assert handle.responses[0][0] == 'user'
	assert 'User called <nextTask>completed</nextTask>' in handle.responses[0][1]['content']
	assert 'Plan finished successfully' in capsys.readouterr().out
	PlanBase.draft = None


def test_plan_cmd_next_parses_command(tmp_path, capsys):
	from src.PlanManager import PlanBase, Plan

	PlanBase.draft = Plan('test_plan')
	t1 = PlanBase.draft.createTask('Task one instruction', 'Task one')
	t2 = PlanBase.draft.createTask('Task two instruction', 'Task two')
	t1.status = 'in_progress'

	cmd, handle = _make_plan_command(tmp_path, htp_return='NEXT_TASK|{}|Task 2/2 - Task two instruction'.format(t2.id))
	ret = cmd.CMD_PLAN('!PLAN NEXT')

	assert ret == 0
	assert handle.responses[1][0] == 'user'
	assert 'Task two instruction' in handle.responses[1][1]['content']
	PlanBase.draft = None
