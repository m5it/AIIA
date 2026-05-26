import os, json, time
from datetime import datetime

class PlanSaver:
	@staticmethod
	def rebuild_history(file_path, msgs):
		"""Rewrite HISTORY.md from scratch with given messages."""
		try:
			os.remove(file_path)
		except:
			pass
		for msg in msgs:
			PlanSaver.save_history_to_file(msg, file_path)

	@staticmethod
	def save_plan_to_file(plan, file_path):
		timestamp = datetime.fromtimestamp(plan.startTimestamp).strftime('%Y-%m-%d %H:%M:%S')
		status = "in_progress" if plan.endTimestamp is None else "completed"
		
		content = "# Plan: {}\n".format(plan.title)
		content += "## ID: {}\n".format(plan.id)
		content += "## Created: {}\n".format(timestamp)
		content += "## Status: {}\n\n".format(status)
		
		if plan.instructions:
			content += "### Goal:\n{}\n\n".format(plan.instructions)
		
		if plan.tasks:
			content += "### Tasks ({}):\n".format(len(plan.tasks))
			task_num = 1
			for tid, task in plan.tasks.items():
				content += "{}. [{}] {}\n".format(task_num, task.status, task.title if hasattr(task, 'title') and task.title else task.instruction[:60])
				content += "   ID: {}\n".format(tid)
				if hasattr(task, 'log') and task.log:
					content += "   Progress logs: {} entries\n".format(len(task.log))
				content += "\n"
				task_num += 1
		
		content += "---\n\n"
		
		# Prepend to file (newest first)
		if os.path.exists(file_path):
			with open(file_path, 'r') as f:
				existing = f.read()
			content = content + existing
		
		with open(file_path, 'w') as f:
			f.write(content)
	
	@staticmethod
	def save_history_to_file(msg, file_path):
		role = msg.get('role', 'unknown')
		content = msg.get('content', '')
		tool_name = msg.get('name', '')
		
		# Get timestamp
		ts = msg.get('timestamp', time.time())
		time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
		
		# Format the entry
		entry = "## [{}] {}\n".format(time_str, role.upper())
		if tool_name:
			entry = "## [{}] {}: {}\n".format(time_str, role, tool_name)
		
		# Truncate long content for preview
		if len(content) > 500:
			display = content[:500] + "...\n(truncated, {} chars total)".format(len(content))
		else:
			display = content
		
		entry += display.replace('\n', '\n> ') if '\n' in content else display
		entry += "\n\n---\n\n"
		
		# JSON comment for machine parsing (full content, not truncated)
		json_comment = "<!-- {} -->\n\n".format(json.dumps(msg, default=str))
		
		# Append to file
		with open(file_path, 'a') as f:
			f.write(entry)
			f.write(json_comment)
	
	@staticmethod
	def save_plan(plan, working_dir=None):
		if not plan:
			return
		
		# Save to working directory only
		if working_dir:
			plan_file = os.path.join(working_dir, 'PLAN.md')
			PlanSaver.save_plan_to_file(plan, plan_file)
	
	@staticmethod
	def save_history(msg, working_dir=None):
		if not msg:
			return
		
		# Save to working directory only
		if working_dir:
			history_file = os.path.join(working_dir, 'HISTORY.md')
			PlanSaver.save_history_to_file(msg, history_file)
	
	@staticmethod
	def load_plan_from_file(file_path):
		if not os.path.exists(file_path):
			return None
		
		with open(file_path, 'r') as f:
			content = f.read()
		
		# Parse first plan from file (newest)
		# This is a simple parser - extracts title and ID
		lines = content.split('\n')
		plan_data = {
			'id': None,
			'title': 'Unknown',
			'instructions': '',
			'status': 'in_progress',
			'tasks': {}
		}
		
		for line in lines:
			if line.startswith('# Plan:'):
				plan_data['title'] = line.replace('# Plan:', '').strip()
			elif line.startswith('## ID:'):
				plan_data['id'] = line.replace('## ID:', '').strip()
			elif line.startswith('## Status:'):
				status = line.replace('## Status:', '').strip()
				if status == 'completed':
					return None  # Plan is finished, don't load
			elif line.startswith('### Goal:'):
				idx = lines.index(line)
				if idx + 1 < len(lines):
					plan_data['instructions'] = lines[idx + 1].strip()
		
		if not plan_data['id']:
			return None
		
		return plan_data
	
	@staticmethod
	def load_history_from_file(file_path):
		if not os.path.exists(file_path):
			return []
		
		with open(file_path, 'r') as f:
			content = f.read()
		
		# Parse history entries - this returns raw content
		# The actual msg parsing would need to happen in HistoryManager
		return content
	
	@staticmethod
	def load_plan(working_dir=None, framework_dir=None):
		# Try working directory first
		if working_dir:
			plan_file = os.path.join(working_dir, 'PLAN.md')
			result = PlanSaver.load_plan_from_file(plan_file)
			if result:
				return result
		
		# Fall back to framework directory
		if framework_dir:
			plan_file = os.path.join(framework_dir, 'PLAN.md')
			result = PlanSaver.load_plan_from_file(plan_file)
			if result:
				return result
		
		return None