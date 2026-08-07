#--
# class PlanToolHandler — handle plan-mode tool calls
import time
from src.PlanManager import PlanBase, Plan, PlanTask
class PlanToolHandler():
	#
	def HandlePlanTool(self, toolName, params):
		plans_path = self.handle.Options.get('plans_path', 'plans')

		handlers = {
			'addTask': self._plan_addTask,
			'createTask': self._plan_createTask,
			'createPlan': self._plan_createPlan,
			'CreatePlan': self._plan_createPlan,
			'CreateTask': self._plan_addTask,
			'AppendTask': self._plan_addTask,
			'deleteTask': self._plan_deleteTask,
			'deletePlan': self._plan_deletePlan,
			'deleteDraft': self._plan_deleteDraft,
			'clearAllTasks': self._plan_clearAllTasks,
			'cancelPlan': self._plan_cancelPlan,
			'deleteAllPlans': self._plan_deleteAllPlans,
			'updateTask': self._plan_updateTask,
			'viewTask': self._plan_viewTask,
			'listTasks': self._plan_listTasks,
			'nextTask': self._plan_nextTask,
			'jobDone': self._plan_jobDone,
			'planDone': self._plan_planDone,
			'startBuild': self._plan_startBuild,
			'LogProgress': self._plan_LogProgress,
		}
		if toolName in handlers:
			return handlers[toolName](params, plans_path)
		return "Unknown plan tool: {}".format(toolName)
	#--
	#
	def _plan_addTask(self, params, plans_path):
		# Alias for createTask — normalizes XML param names the model hallucinates
		if 'taskTitle' in params and 'title' not in params:
			params['title'] = params.pop('taskTitle')
		if 'taskDescription' in params and 'instruction' not in params:
			params['instruction'] = params.pop('taskDescription')
		# Fallthrough to createTask
		return self._plan_createTask(params, plans_path)
	#--
	#
	def _plan_createTask(self, params, plans_path):
		# Normalize common param name variations the model sends
		if 'name' in params and 'title' not in params:
			params['title'] = params.pop('name')
		if 'description' in params and 'instruction' not in params:
			params['instruction'] = params.pop('description')
		title = params.get('title', '')
		instruction = params.get('instruction', '')
		if not PlanBase.draft:
			return "No active plan. Use createPlan first to create a new plan."
		else:
			task = PlanBase.draft.createTask(instruction, title)
			PlanBase.draft.save(plans_path)
			# Save plan to PLAN.md (working dir only)
			working_dir = self.handle.Options.get('working_dir')
			from src.PlanSaver import PlanSaver
			PlanSaver.save_plan(PlanBase.draft, working_dir)
			return "Task created: {} | ID: {}".format(title if title else instruction[:50], task.id)
		return "Plan created. Plan ID: {}".format(plan.id)
	#--
	#
	def _plan_createPlan(self, params, plans_path):
		title = params.get('title', '')
		instructions = params.get('instructions', '')
		if not PlanBase.draft:
			plan = PlanBase.Create(title, instructions, plans_path)
			# Save plan to PLAN.md (working dir only)
			working_dir = self.handle.Options.get('working_dir')
			from src.PlanSaver import PlanSaver
			PlanSaver.save_plan(plan, working_dir)
			return "Plan created. Plan ID: {}".format(plan.id)
		else:
			return str(PlanBase.draft.createPlan(title, instructions))
	#--
	#
	def _plan_deleteTask(self, params, plans_path):
		task_id = params.get('id')
		if task_id and PlanBase.draft:
			task = PlanBase.draft.tasks.get(task_id)
			if task:
				result = task.delete()
				del PlanBase.draft.tasks[task_id]
				PlanBase.draft.save(plans_path)
				return str(result)
		return "Error: task id required or no active plan"
	#--
	#
	def _plan_deletePlan(self, params, plans_path):
		plan_id = params.get('id')
		if plan_id:
			# Delete specific plan by ID
			if PlanBase.draft and PlanBase.draft.id == plan_id:
				PlanBase.draft = None
			if plan_id in PlanBase.done:
				del PlanBase.done[plan_id]
			PlanBase.Delete(plan_id, plans_path)
			return "Plan {} deleted".format(plan_id)
		elif PlanBase.draft:
			# Delete current draft
			plan_id = PlanBase.draft.id
			if plan_id in PlanBase.done:
				del PlanBase.done[plan_id]
			PlanBase.draft = None
			PlanBase.Delete(plan_id, plans_path)
			return "Draft plan {} deleted".format(plan_id)
		return "No active plan to delete"
	#--
	#
	def _plan_deleteDraft(self, params, plans_path):
		if not PlanBase.draft:
			return "No draft plan to delete"
		plan_id = PlanBase.draft.id
		if plan_id in PlanBase.done:
			del PlanBase.done[plan_id]
		PlanBase.draft = None
		PlanBase.Delete(plan_id, plans_path)
		return "Draft plan {} deleted".format(plan_id)
	#--
	#
	def _plan_clearAllTasks(self, params, plans_path):
		if PlanBase.draft:
			count = len(PlanBase.draft.tasks)
			PlanBase.draft.tasks = {}
			PlanBase.draft.save(plans_path)
			return "Cleared {} tasks from current plan".format(count)
		return "No active plan"
	#--
	#
	def _plan_cancelPlan(self, params, plans_path):
		plan_id = params.get('id')
		if plan_id:
			PlanBase.Delete(plan_id, plans_path)
			return "Plan {} cancelled and deleted".format(plan_id)
		if PlanBase.draft:
			plan_id = PlanBase.draft.id
			PlanBase.draft = None
			PlanBase.Delete(plan_id, plans_path)
			return "Current plan cancelled and deleted"
		return "No active plan to cancel"
	#--
	#
	def _plan_deleteAllPlans(self, params, plans_path):
		import os
		deleted = 0
		if os.path.exists(plans_path):
			for f in os.listdir(plans_path):
				if f.endswith('.json'):
					os.remove(os.path.join(plans_path, f))
					deleted += 1
		PlanBase.done = {}
		PlanBase.draft = None
		return "Deleted {} plan files".format(deleted)
	#--
	#
	def _plan_updateTask(self, params, plans_path):
		task_id = params.get('id')
		status = params.get('status')
		if PlanBase.draft and task_id in PlanBase.draft.tasks:
			task = PlanBase.draft.tasks[task_id]
			if status:
				task.status = status
				PlanBase.draft.save(plans_path)
			return str(task.view())
		return "Task not found"
	#--
	#
	def _plan_viewTask(self, params, plans_path):
		plan_id = params.get('id')
		return str(PlanBase.View(plan_id, plans_path))
	#--
	#
	def _plan_listTasks(self, params, plans_path):
		return str(PlanBase.List(plans_path))
	#--
	#
	def _plan_nextTask(self, params, plans_path):
		if not PlanBase.draft:
			return "No active plan. Use createPlan first to create a new plan."
		status = params.get('status', 'completed')
		result = PlanBase.draft.nextTask(self.handle, status)
		# Persist task state to disk right away
		PlanBase.draft.save(plans_path)
		if hasattr(self.handle, '_write_current_task'):
			self.handle._write_current_task()
		if result.get('done'):
			blocked_count = result.get('blocked_count', 0)
			if blocked_count > 0:
				return "DONE_WITH_BLOCKED:{}".format(result.get('message', 'Some tasks were blocked'))
			else:
				PlanBase.draft.jobDone(self.handle)
				return "ALL_COMPLETED:Plan finished successfully"
		return "NEXT_TASK:{}".format(result.get('next_task_instruction', ''))
	#--
	#
	def _plan_jobDone(self, params, plans_path):
		if PlanBase.draft:
			result = str(PlanBase.draft.jobDone(self.handle))
			if hasattr(self.handle, '_write_current_task'):
				self.handle._write_current_task()
			return result
		return "No active plan. Use createPlan first to create a new plan."
	#--
	#
	def _plan_planDone(self, params, plans_path):
		if not PlanBase.draft:
			return "No active plan. Use createPlan first."
		first_task = None
		for tid, task in PlanBase.draft.tasks.items():
			if task.status == "pending":
				first_task = task
				task.status = "in_progress"
				task.startTimestamp = time.time()
				break
		if first_task:
			PlanBase.draft.save(plans_path)
			PlanBase.LogProgress(first_task.id, "Build started", plans_path)
			task_number = sum(1 for t in PlanBase.draft.tasks.values() if t.status in ["completed", "in_progress"])
			total_tasks = len(PlanBase.draft.tasks)
			if hasattr(self.handle, '_write_current_task'):
				self.handle._write_current_task()
			return "PLAN_DONE|Task {}/{}|{}".format(task_number, total_tasks, first_task.instruction)
		return "No pending tasks in plan."
	#--
	#
	def _plan_startBuild(self, params, plans_path):
		plan_id = params.get('planId')
		if not PlanBase.draft:
			if plan_id:
				plan = Plan.load(plan_id, plans_path)
				if plan:
					PlanBase.draft = plan
				else:
					return "Plan {} not found".format(plan_id)
			else:
				return "No active plan. Use createPlan first."
		first_task = None
		# Don't double-start — if a task is already in_progress, do nothing
		already_started = any(t.status == "in_progress" for t in PlanBase.draft.tasks.values())
		if already_started:
			return "Build already started — task already in progress."
		for tid, task in PlanBase.draft.tasks.items():
			if task.status == "pending":
				first_task = task
				task.status = "in_progress"
				task.startTimestamp = time.time()
				break
		if first_task:
			PlanBase.draft.save(plans_path)
			PlanBase.LogProgress(first_task.id, "Build started", plans_path)
			task_number = sum(1 for t in PlanBase.draft.tasks.values() if t.status in ["completed", "in_progress"])
			total_tasks = len(PlanBase.draft.tasks)
			return "START_BUILD|Task {}/{}|{}".format(task_number, total_tasks, first_task.instruction)
		return "No pending tasks in plan"
	#--
	#
	def _plan_LogProgress(self, params, plans_path):
		task_id = params.get('taskId')
		what_was_done = params.get('whatWasDone', '')
		return str(PlanBase.LogProgress(task_id, what_was_done, plans_path))
	#--
