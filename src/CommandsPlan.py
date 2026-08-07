#--
# class CommandsPlan — plan commands
import os, time
class CommandsPlan():
	#
	def CMD_START_BUILD(self, inp=""):
		from src.PlanManager import PlanBase, Plan
		parts = inp.strip().split()
		plan_id = parts[1] if len(parts) > 1 and not parts[1].startswith('!') else None
		if plan_id:
			self.handle.hLG.echo("Loading plan {} and starting build...".format(plan_id), {'color':True, 'colorValue':'cyan'})
		# Switch mode to build if currently in plan mode
		if self.handle.Options.get('MODE') == 'plan':
			self.handle.Options['MODE'] = 'build'
			self.handle._write_state({'mode': 'build'})
			self.handle._set_mode_instructions('build')
		self.handle.StartBuild(plan_id)
		return 0

	def CMD_PLAN(self, inp=""):
		plans_path = self.handle.Options.get('plans_path', 'plans')
		working_dir = self.handle.Options.get('working_dir')

		# Parse command
		parts = inp.strip().split()
		action = parts[1].upper() if len(parts) > 1 else 'PREVIEW'
		task_id = parts[2] if len(parts) > 2 else None

		if action == 'PREVIEW' or action == '':
			self._plan_preview()
		elif action == 'VIEW' or action == 'TASKS':
			self._plan_view()
		elif action == 'STATUS':
			self._plan_status()
		elif action == 'LIST':
			self._plan_list(plans_path)
		elif action == 'CLEAR':
			self._plan_clear(plans_path)
		elif action == 'DELETE' or action == 'RESET':
			self._plan_delete(plans_path)
		elif action == 'DONE':
			self._plan_done(plans_path, working_dir)
		else:
			self._plan_usage()

		return 2

	def _plan_preview(self):
		from src.PlanManager import PlanBase
		# Show current plan overview
		if PlanBase.draft:
			plan = PlanBase.draft
			print("\n=== CURRENT PLAN ===")
			print("Plan ID: {}".format(plan.id))
			print("Title: {}".format(plan.title))
			print("Status: {}".format("DRAFT (in progress)" if plan.endTimestamp is None else "COMPLETED"))
			print("\n--- TASKS ---")
			pending = completed = blocked = 0
			for tid, task in plan.tasks.items():
				status = task.status
				if status == 'pending': pending += 1
				elif status == 'completed': completed += 1
				elif status == 'blocked': blocked += 1
			print("Pending: {} | Completed: {} | Blocked: {}".format(pending, completed, blocked))
			if pending > 0:
				for tid, task in plan.tasks.items():
					if task.status == 'pending':
						print("\nNEXT TASK:")
						print("  ID: {}".format(tid))
						print("  Instruction: {}".format(task.instruction[:100] + "..." if len(task.instruction) > 100 else task.instruction))
						break
		else:
			print("\nNo active plan.")
			print("Plans in history: {}".format(len(PlanBase.done)))

	def _plan_view(self):
		from src.PlanManager import PlanBase
		if PlanBase.draft:
			plan = PlanBase.draft
			print("\n=== PLAN TASKS ===")
			for tid, task in plan.tasks.items():
				status_icon = {'pending': '⏳', 'completed': '✓', 'blocked': '✗'}.get(task.status, '?')
				print("\n{} Task ID: {}".format(status_icon, tid))
				print("   Status: {}".format(task.status))
				print("   Instruction: {}".format(task.instruction[:80] + "..." if len(task.instruction) > 80 else task.instruction))
				if task.log:
					print("   Log entries: {}".format(len(task.log)))
		else:
			print("\nNo active plan.")

	def _plan_status(self):
		from src.PlanManager import PlanBase
		if PlanBase.draft:
			plan = PlanBase.draft
			print("\n=== PLAN STATUS ===")
			print("MODE: {}".format(self.handle.Options.get('MODE', 'build')))
			print("Plan ID: {}".format(plan.id))
			print("Tasks: {} total".format(len(plan.tasks)))
			for tid, task in plan.tasks.items():
				if task.status == 'pending':
					print("- [PENDING] {}".format(tid))
				elif task.status == 'completed':
					print("- [DONE] {}".format(tid))
				elif task.status == 'blocked':
					print("- [BLOCKED] {}".format(tid))
		else:
			print("\nNo active plan.")

	def _plan_list(self, plans_path):
		from datetime import datetime
		from src.PlanManager import PlanBase, Plan
		all_plans = []
		# Active draft
		_plan_add_draft(all_plans, datetime, PlanBase)
		# Completed plans from done dict
		_plan_add_done(all_plans, datetime, PlanBase)
		# Scan plans/ dir for any not in done dict
		_plan_add_disk(all_plans, datetime, plans_path, PlanBase, Plan)
		_plan_render(all_plans)

	def _plan_clear(self, plans_path):
		from src.PlanManager import PlanBase
		if PlanBase.draft:
			count = len(PlanBase.draft.tasks)
			PlanBase.draft.tasks = {}
			PlanBase.draft.save(plans_path)
			print("Cleared {} tasks from current plan.".format(count))
		else:
			print("No active plan.")

	def _plan_delete(self, plans_path):
		from src.PlanManager import PlanBase
		if PlanBase.draft:
			plan_id = PlanBase.draft.id
			PlanBase.draft = None
			PlanBase.Delete(plan_id, plans_path)
			print("Plan {} deleted.".format(plan_id))
		else:
			print("No active plan.")

	def _plan_done(self, plans_path, working_dir):
		from src.PlanManager import PlanBase
		from src.PlanSaver import PlanSaver
		if PlanBase.draft:
			plan = PlanBase.draft
			plan_id = plan.id
			plan.endTimestamp = time.time()
			PlanBase.done[str(plan_id)] = plan.to_dict()
			PlanBase.draft = None
			plan.save(plans_path)
			PlanSaver.save_plan(plan, working_dir)
			print("\nPlan '{}' marked as DONE and saved.".format(plan.title or plan_id))
		else:
			print("\nNo active plan to mark as done.")

	def _plan_usage(self):
		print("\nUsage: !PLAN [PREVIEW|VIEW|TASKS|STATUS|LIST|CLEAR|DELETE|RESET|DONE]")
		print("  PREVIEW  - Show plan overview (default)")
		print("  VIEW     - Show all tasks with details")
		print("  TASKS    - Same as VIEW")
		print("  STATUS   - Show quick status")
		print("  LIST     - Show all plans (active + completed)")
		print("  CLEAR    - Remove all tasks from current plan")
		print("  DELETE   - Delete current plan entirely")
		print("  RESET    - Same as DELETE")
		print("  DONE     - Mark current plan as completed and save (keeps plan)")

#--

def _plan_add_draft(all_plans, datetime, PlanBase):
	# Active draft
	if not PlanBase.draft:
		return
	p = PlanBase.draft
	pending = sum(1 for t in p.tasks.values() if t.status == 'pending')
	completed = sum(1 for t in p.tasks.values() if t.status == 'completed')
	blocked = sum(1 for t in p.tasks.values() if t.status == 'blocked')
	in_prog = sum(1 for t in p.tasks.values() if t.status == 'in_progress')
	total = len(p.tasks)
	parts = []
	if completed: parts.append("{} done".format(completed))
	if in_prog: parts.append("{} active".format(in_prog))
	if pending: parts.append("{} pending".format(pending))
	if blocked: parts.append("{} blocked".format(blocked))
	counts = " ({} tasks: {})".format(total, ", ".join(parts)) if total else ""
	created = datetime.fromtimestamp(p.startTimestamp).strftime('%Y-%m-%d %H:%M') if p.startTimestamp else "?"
	all_plans.append(("draft", p.id, p.title or "(untitled)", counts, created, None))

#--

def _plan_add_done(all_plans, datetime, PlanBase):
	# Completed plans from done dict
	for pid, pdata in PlanBase.done.items():
		tasks = pdata.get("tasks", {})
		total = len(tasks)
		done_count = sum(1 for t in tasks.values() if t.get("status") == "completed")
		parts = ["{} done".format(done_count)] if done_count else []
		remaining = total - done_count
		if remaining: parts.append("{} other".format(remaining))
		counts = " ({} tasks: {})".format(total, ", ".join(parts)) if total else ""
		created = datetime.fromtimestamp(pdata.get("startTimestamp", 0)).strftime('%Y-%m-%d %H:%M') if pdata.get("startTimestamp") else "?"
		completed_at = datetime.fromtimestamp(pdata.get("endTimestamp", 0)).strftime('%Y-%m-%d %H:%M') if pdata.get("endTimestamp") else None
		all_plans.append(("done", pid, pdata.get("title", "(untitled)"), counts, created, completed_at))

#--

def _plan_add_disk(all_plans, datetime, plans_path, PlanBase, Plan):
	# Scan plans/ dir for any not in done dict
	if not os.path.exists(plans_path):
		return
	for f in os.listdir(plans_path):
		if not f.endswith(".json"):
			continue
		plan_id = f[:-5]
		if plan_id in PlanBase.done or (PlanBase.draft and PlanBase.draft.id == plan_id):
			continue
		try:
			plan = Plan.load(plan_id, plans_path)
			if not plan:
				continue
			tasks = plan.tasks
			total = len(tasks)
			done_count = sum(1 for t in tasks.values() if t.status == "completed")
			parts = ["{} done".format(done_count)] if done_count else []
			remaining = total - done_count
			if remaining: parts.append("{} other".format(remaining))
			counts = " ({} tasks: {})".format(total, ", ".join(parts)) if total else ""
			created = datetime.fromtimestamp(plan.startTimestamp).strftime('%Y-%m-%d %H:%M') if plan.startTimestamp else "?"
			status = "done" if plan.endTimestamp else "archived"
			all_plans.append((status, plan.id, plan.title or "(untitled)", counts, created, None))
		except Exception:
			pass

#--

def _plan_render(all_plans):
	if not all_plans:
		print("\nNo plans found.")
		return
	print("\n=== ALL PLANS ({}) ===\n".format(len(all_plans)))
	G = '\033[1;32m'  # green
	C = '\033[1;36m'  # cyan
	Y = '\033[1;33m'  # yellow/orange
	R = '\033[0m'     # reset
	for status, pid, title, counts, created, completed_at in all_plans:
		if status == "draft":
			label = "{}[DRAFT]{}{}".format(C, R, title)
		elif status == "done":
			label = "{}[DONE]{}{}".format(G, R, title)
		else:
			label = "{}[{}]{}{}".format(Y, status.upper(), R, title)
		print("  {}{}".format(label, counts))
		date_str = "    Created: {}".format(created)
		if completed_at:
			date_str += " | Completed: {}".format(completed_at)
		print(date_str)
		print("    ID: {}".format(pid))
		print()
