import os, json, time
from datetime import datetime

class TaskLog:
	def __init__(self, text):
		self.timestamp = time.time()
		self.text = text

class PlanTask:
	def __init__(self, task_id, instruction, title=""):
		self.id = task_id
		self.title = title
		self.status = "pending"
		self.instruction = instruction
		self.startTimestamp = None
		self.endTimestamp = None
		self.log = []

	def delete(self):
		return {"deleted": self.id}

	def update(self, status=None):
		if status:
			self.status = status
		return {"id": self.id, "status": self.status}

	def view(self):
		return {
			"id": self.id,
			"status": self.status,
			"instruction": self.instruction,
			"startTimestamp": self.startTimestamp,
			"endTimestamp": self.endTimestamp,
			"log": [l.__dict__ for l in self.log]
		}

	def to_dict(self):
		return {
			"id": self.id,
			"status": self.status,
			"instruction": self.instruction,
			"startTimestamp": self.startTimestamp,
			"endTimestamp": self.endTimestamp,
			"log": [l.__dict__ for l in self.log]
		}

	@staticmethod
	def from_dict(d):
		task = PlanTask(d.get("id", ""), d.get("instruction", ""))
		task.status = d.get("status", "pending")
		task.startTimestamp = d.get("startTimestamp")
		task.endTimestamp = d.get("endTimestamp")
		task.log = [TaskLog(l.get("text", "")) for l in d.get("log", [])]
		task.log_timestamp = d.get("timestamp")
		return task

class Plan:
	def __init__(self, plan_id, title="", instructions=""):
		self.id = plan_id
		self.title = title
		self.instructions = instructions
		self.startTimestamp = time.time()
		self.endTimestamp = None
		self.tasks = {}

	def createPlan(self, title=None, instructions=None):
		if title:
			self.title = title
		if instructions:
			self.instructions = instructions
		return {"id": self.id, "title": self.title, "instructions": self.instructions}

	def createTask(self, instruction, title=""):
		task_id = str(time.time())
		task = PlanTask(task_id, instruction, title)
		self.tasks[task_id] = task
		return task

	

	def nextTask(self, handle, status="completed"):
		task_id = None
		current_task = None
		for tid, t in self.tasks.items():
			if t.status == "pending":
				task_id = tid
				current_task = t
				break

		if current_task:
			current_task.status = status
			current_task.endTimestamp = time.time()
			next_instruction = current_task.instruction
			return {
				"done": False,
				"current_task_id": task_id,
				"status": status,
				"next_task_instruction": next_instruction
			}

		# No more pending tasks - check for blocked
		blocked_count = sum(1 for t in self.tasks.values() if t.status == "blocked")
		completed_count = sum(1 for t in self.tasks.values() if t.status == "completed")
		return {
			"done": True,
			"message": "No more pending tasks",
			"blocked_count": blocked_count,
			"completed_count": completed_count,
			"next_task_instruction": None
		}

	def jobDone(self, handle):
		self.endTimestamp = time.time()
		PlanBase.done[str(self.id)] = self.to_dict()
		PlanBase.draft = None
		self.save()
		return {"plan_id": self.id, "status": "completed", "summary": "Plan finished"}

	def view(self):
		return {
			"id": self.id,
			"title": self.title,
			"instructions": self.instructions,
			"startTimestamp": self.startTimestamp,
			"endTimestamp": self.endTimestamp,
			"tasks": {k: v.to_dict() for k, v in self.tasks.items()}
		}

	def to_dict(self):
		return {
			"id": self.id,
			"title": self.title,
			"instructions": self.instructions,
			"startTimestamp": self.startTimestamp,
			"endTimestamp": self.endTimestamp,
			"tasks": {k: v.to_dict() for k, v in self.tasks.items()}
		}

	@staticmethod
	def from_dict(d):
		plan = Plan(d.get("id", ""), d.get("title", ""), d.get("instructions", ""))
		plan.startTimestamp = d.get("startTimestamp")
		plan.endTimestamp = d.get("endTimestamp")
		plan.tasks = {}
		for tid, td in d.get("tasks", {}).items():
			plan.tasks[tid] = PlanTask.from_dict(td)
		return plan

	def save(self, plans_path="plans"):
		if not os.path.exists(plans_path):
			os.makedirs(plans_path, exist_ok=True)
		file_path = os.path.join(plans_path, "{}.json".format(self.id))
		with open(file_path, "w") as f:
			json.dump(self.to_dict(), f, indent=2)
		return file_path

	@staticmethod
	def load(plan_id, plans_path="plans"):
		file_path = os.path.join(plans_path, "{}.json".format(plan_id))
		if os.path.exists(file_path):
			with open(file_path, "r") as f:
				return Plan.from_dict(json.load(f))
		return None

class PlanBase:
	done = {}
	draft = None

	@staticmethod
	def Create(title="", instructions="", plans_path="plans"):
		plan_id = str(time.time())
		plan = Plan(plan_id, title, instructions)
		PlanBase.draft = plan
		plan.save(plans_path)
		return plan

	@staticmethod
	def Delete(plan_id, plans_path="plans"):
		if plan_id in PlanBase.done:
			del PlanBase.done[plan_id]
		file_path = os.path.join(plans_path, "{}.json".format(plan_id))
		if os.path.exists(file_path):
			os.remove(file_path)
		if PlanBase.draft and PlanBase.draft.id == plan_id:
			PlanBase.draft = None
		return {"deleted": plan_id}

	@staticmethod
	def View(plan_id=None, plans_path="plans"):
		if plan_id:
			plan = Plan.load(plan_id, plans_path)
			if plan:
				return plan.view()
			if plan_id in PlanBase.done:
				return PlanBase.done[plan_id]
			return {"error": "Plan not found"}
		if PlanBase.draft:
			return PlanBase.draft.view()
		return {"draft": None, "done": PlanBase.done}

	@staticmethod
	def List(plans_path="plans"):
		done_list = []
		if os.path.exists(plans_path):
			for f in os.listdir(plans_path):
				if f.endswith(".json"):
					plan_id = f[:-5]
					if plan_id not in PlanBase.done:
						plan = Plan.load(plan_id, plans_path)
						if plan:
							done_list.append({"id": plan.id, "title": plan.title, "status": "in_progress" if plan.endTimestamp is None else "completed"})
		for pid, pdata in PlanBase.done.items():
			done_list.append({"id": pid, "title": pdata.get("title", ""), "status": "completed"})
		return {"plans": done_list}

	@staticmethod
	def LoadAll(plans_path="plans"):
		if os.path.exists(plans_path):
			for f in os.listdir(plans_path):
				if f.endswith(".json"):
					plan_id = f[:-5]
					if plan_id not in PlanBase.done:
						plan = Plan.load(plan_id, plans_path)
						if plan and plan.endTimestamp:
							PlanBase.done[plan_id] = plan.to_dict()

	@staticmethod
	def LogProgress(task_id, what_was_done, plans_path="plans"):
		if PlanBase.draft and task_id in PlanBase.draft.tasks:
			task = PlanBase.draft.tasks[task_id]
			task.log.append(TaskLog(what_was_done))
			PlanBase.draft.save(plans_path)
			return {"task_id": task_id, "logged": what_was_done, "log_entries": len(task.log)}
		return {"error": "Task not found or no active plan"}