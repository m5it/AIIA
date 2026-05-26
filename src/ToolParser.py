"""
ToolParser - Handles parsing of XML tool invocations and job completion detection
"""
import re
import os
from src.functions import initmodule,importmodule,splitFileNameExtension

class ToolParser:
	"""
	Parses AI responses for XML tool invocations and job_done tags
	"""
	_current_handle = None  # Set before tool.run() for tools that need handle access
	#--
	def __init__(self, opts={}):
		self.logger = opts['logger'] if 'logger' in opts else None
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
	#--
	def ParseTextToolInvocation(self, text):
		print("ToolParser().ParseTextToolInvocation() START! text.len: {}".format( len(text) ))
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
		results = []
		#
		# First, find all self-closing tags: <TagName/>
		self_closing_pattern = r'<(\w+)\s*/>'
		for match in re.finditer(self_closing_pattern, text):
			toolName = match.group(1)
			results.append({
				'name': toolName,
				'parameters': {}
			})
		#
		# Then, find all regular tags with content: <TagName>...</TagName>
		i = 0
		text_lower = text.lower()
		#
		while i < len(text):
			# Find next opening tag (case-insensitive)
			open_match = re.search(r'<(\w+)>', text[i:])
			if not open_match:
				break
			#
			toolName = open_match.group(1)
			start_pos = i + open_match.start()
			inner_start = i + open_match.end()
			#
			# Find matching closing tag (case-insensitive)
			close_tag = '</{}>'.format(toolName)
			close_tag_lower = '</{}>'.format(toolName.lower())
			#
			pos = text_lower.find(close_tag_lower, inner_start)
			if pos == -1:
				pos = text.find(close_tag, inner_start)
			#
			if pos == -1:
				i = inner_start
				continue
			#
			# Extract inner content and parse parameters
			inner_content = text[inner_start:pos]
			params = {}
			for pm in re.finditer(r'<(\w+)>(.*?)</\1>', inner_content, re.DOTALL | re.IGNORECASE):
				params[pm.group(1)] = pm.group(2).strip()
			#
			results.append({
				'name': toolName,
				'parameters': params
			})
			#
			i = pos + len(close_tag)
		#
		return results
	
	#
	def CheckJobDone(self, text):
		print("ToolParser().CheckJobDone() START!")
		# Check if response contains <job_done/> or <job_done></job_done>
		pattern1 = r'<job_done\s*/?>'
		pattern2 = r'<job_done>.*?</job_done>'
		#
		if re.search(pattern1, text, re.IGNORECASE) or re.search(pattern2, text, re.IGNORECASE):
			return True
		return False
	
	#
	def ExtractToolResult(self, text):
		print("ToolParser().ExtractToolResult() START! text.len: {}".format( len(text) ))
		# Remove all tool invocations from text, return clean text
		# Used to get the actual response without XML tool calls
		#import re
		#
		# Remove self-closing tags
		text = re.sub(r'<\w+\s*/>', '', text)
		#
		# Remove opening and closing tags with content
		text = re.sub(r'<\w+>.*?</\w+>', '', text, flags=re.DOTALL | re.IGNORECASE)
		#
		return text.strip()
	
	#
	def ExecuteTextTool(self, toolName, params):
		print("DEBUG ExecuteTextTool START, toolName: {}".format( toolName ))
		# Execute a tool based on XML invocation
		#
		# ROUTING: If ExecuteScript is called with a non-script file, route to Terminal
		if toolName.lower() == 'executescript':
			fileName = params.get('fileName', '')
			script_extensions = ['.py', '.sh', '.js', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1']
			is_script = any(fileName.lower().endswith(ext) for ext in script_extensions)
			#
			if not is_script and fileName:
				# Route to Terminal tool
				print("Routing ExecuteScript({}) to Terminal tool".format(fileName))
				# Build args for Terminal: arg1=fileName, arg2=args, etc.
				terminal_args = {}
				terminal_args['arg1'] = fileName
				#
				# Add additional args if provided
				if 'args' in params:
					args = params['args']
					# Handle if args is a string (could be JSON array, Python list repr, or space-separated)
					if isinstance(args, str):
						import json
						# Try to parse as JSON array first
						try:
							parsed_args = json.loads(args)
							if isinstance(parsed_args, list):
								for i, arg in enumerate(parsed_args, start=2):
									terminal_args['arg{}'.format(i)] = str(arg)
								args = None  # Mark as processed
						except:
							pass
						#
						if args:  # Not JSON, try other formats
							# Check if it looks like a Python list representation: [item1, item2, ...]
							if args.strip().startswith('[') and args.strip().endswith(']'):
								# Strip brackets and split by comma
								inner = args.strip()[1:-1].strip()
								if inner:  # Not empty
									# Split by comma and clean up
									parts = [p.strip().strip('"\'') for p in inner.split(',')]
									for i, arg in enumerate(parts, start=2):
										if arg:  # Skip empty parts
											terminal_args['arg{}'.format(i)] = arg
								args = None
						#
						if args:  # Still not processed, treat as space-separated
							import shlex
							try:
								parsed_args = shlex.split(args)
								for i, arg in enumerate(parsed_args, start=2):
									terminal_args['arg{}'.format(i)] = arg
							except:
								terminal_args['arg2'] = args
					elif isinstance(args, list):
						for i, arg in enumerate(args, start=2):
							terminal_args['arg{}'.format(i)] = str(arg)
					#
					toolName = 'Terminal'
					params = terminal_args
		#
		# Load tool dynamically if not already loaded
		if toolName not in self.handle.hTC.handles:
			self.handle.hLG.echo("Tool {} not loaded, loading dynamically...".format(toolName), {'color':True, 'colorValue':'orange'})
			#
			try:
				# Find tool file by name
				tool_file = None
				for f in os.listdir(self.handle.Options['tools_path']):
					# Check if file matches tool_XXX.py pattern
					if f.startswith("tool_") and f.endswith(".py"):
						file_tool_name = f[5:-3]  # Extract name from tool_XXX.py
						# Try to match with toolName (case-insensitive)
						if file_tool_name.lower() == toolName.lower():
							tool_file = f
							break
				#
				if tool_file is None:
					return "Tool `{}` not found in tools/".format(toolName)
				#
				# Load the tool
				tmp = splitFileNameExtension(tool_file)
				mod = importmodule(tmp['name'], True, {'path':self.handle.Options['tools_path']})
				#
				# Initialize with proper class name (try toolName or file name)
				h = None
				for cls_name in [toolName, tmp['name']]:
					try:
						h = initmodule(mod, cls_name)
						if h:
							break
					except:
						continue
				#
				if h is None:
					return "Failed to initialize tool `{}`".format(toolName)
				#
				# Store in handles
				self.handle.hTC.handles[toolName] = {'handle': h}
				self.handle.hLG.echo("Tool {} loaded successfully".format(toolName), {'color':True, 'colorValue':'green'})
			except Exception as E:
				return "Error loading tool {}: {}".format(toolName, E)
		#
		# Validate and execute the tool
		h = None
		try:
			h = self.handle.hTC.handles[toolName]['handle']
			info = getattr(h, 'info', {})
			required = info.get('parameters', {}).get('required', [])
			missing = [r for r in required if r not in params or params[r] in (None, '')]
			if missing:
				self.handle.tool_errors += 1
				return "Error: Missing required parameter(s): {}{}".format(
					', '.join(missing), self._tool_usage(info))
			#
			# Cache check: if tool has cache_ttl and caching enabled, try cache
			cache_ttl = getattr(h, 'cache_ttl', 0)
			cache_enabled = self.handle.Options.get('TOOL_CACHE_ENABLED', True)
			cached = None
			if cache_ttl > 0 and cache_enabled:
				key = self._cache_key(toolName, params)
				cached = self.handle.hTM.get_cache(toolName, key)
			if cached is not None:
				self.handle.hLG.echo("Cache HIT for {} — returning cached result".format(toolName), {'color':True, 'colorValue':'cyan'})
				return cached
			#
			ToolParser._current_handle = self.handle
			try:
				result = h.run(**params)
			finally:
				ToolParser._current_handle = None
			#
			# Cache save: if tool has cache_ttl and result is not an error, save it
			if cache_ttl > 0 and cache_enabled and result and not str(result).startswith('Error'):
				key = self._cache_key(toolName, params)
				self.handle.hTM.set_cache(toolName, key, result, cache_ttl)
				self.handle.hLG.echo("Cached {} result (TTL: {}s)".format(toolName, cache_ttl), {'color':True, 'colorValue':'cyan'})
			#
			return result
		except Exception as E:
			self.handle.tool_errors += 1
			info = getattr(h, 'info', {}) if h else {}
			return "Error executing {}: {}{}".format(toolName, E, self._tool_usage(info))
	#
	def _cache_key(self, toolName, params):
		import hashlib, json
		raw = "{}:{}".format(toolName, json.dumps(params, sort_keys=True))
		return hashlib.md5(raw.encode()).hexdigest()[:16]

	def _tool_usage(self, info):
		name = info.get('name', 'Tool')
		params = info.get('parameters', {})
		props = params.get('properties', {})
		required = params.get('required', [])
		parts = []
		for pname, pinfo in props.items():
			parts.append("<{pname}>{type_hint}</{pname}>".format(pname=pname, type_hint=pinfo.get('type', 'value')))
		usage = "\nUsage:\n<{name}>\n{params}\n</{name}>".format(name=name, params='\n'.join(parts))
		return usage
	
	#
	def FireToolInvocation(self, tool_invocations):
		print("DEBUG FireToolInvocation() START, tool_invocations: {}".format(tool_invocations))
		#
		is_plan_mode = self.handle.Options.get('MODE') == 'plan'
		plan_tools = ['createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks']
		build_tools = ['LogProgress', 'nextTask', 'viewTask', 'listTasks', 'jobDone', 'startBuild', 'createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask']
		#
		# Sort to process createTask before other tools
		def sort_key(inv):
			name = inv['name']
			if name == 'createTask':
				return -1
			elif name == 'createPlan':
				return -2
			return 0
		tool_invocations = sorted(tool_invocations, key=sort_key)
		#
		job_done = False
		for inv in tool_invocations:
			print("DEBUG FireToolInvocation() name: {}".format(inv['name']))
			toolName = inv['name']
			params   = inv['parameters']
			#
			self.handle.tool_iteration += 1
			#
			# Show user what tool is being called (preview)
			params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
			self.handle.hLG.echo("🔧 Executing: {} ({})".format(toolName, params_str if params_str else 'no params'), {'color':True, 'colorValue':'cyan'})
			#
			# Route to plan tools if in plan mode, or build tools (like LogProgress)
			if (is_plan_mode and toolName in plan_tools) or (toolName in build_tools):
				result = self.HandlePlanTool(toolName, params)
			else:
				result = self.ExecuteTextTool(toolName, params)
			print("DEBUG FireToolInvocation() result: ",result)
			#
			self.handle.Response('tool',{'content':str(result),'name':toolName})
			#
			# (Just on print to console. Chat History should have always original data!) Truncate result if too long
			MAX_PREVIEW = 500
			result_str = str(result)
			if len(result_str) > MAX_PREVIEW:
				result_str = result_str[:MAX_PREVIEW] + "... (truncated, {} chars total)".format(len(str(result)))
			#
			self.handle.hLG.echo("✓ Result: {}".format(result_str), {'color':True, 'colorValue':'green'})
			#
			# Track jobDone to signal Parse/AI loop
			if toolName == 'jobDone':
				job_done = True
			# Reset error counter on success
			if not str(result).startswith('Error'):
				self.handle.tool_errors = 0
		self.handle.hLG.echo("--- Tool iterations: {} | errors: {}".format(self.handle.tool_iteration, self.handle.tool_errors), {'color':True, 'colorValue':'cyan'})
		return result
	#
	def HandlePlanTool(self, toolName, params):
		print("DEBUG HandlePlanTool() START, toolName: {}, params: {}".format(toolName, params))
		from src.PlanManager import PlanBase, Plan, PlanTask

		plans_path = self.handle.Options.get('plans_path', 'plans')

		if toolName == 'createTask':
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

		elif toolName == 'createPlan':
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

		elif toolName == 'deleteTask':
			plan_id = params.get('id')
			if plan_id:
				return str(PlanBase.Delete(plan_id, plans_path))
			return "Error: plan id required"

		elif toolName == 'deletePlan':
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

		elif toolName == 'deleteDraft':
			if not PlanBase.draft:
				return "No draft plan to delete"
			plan_id = PlanBase.draft.id
			if plan_id in PlanBase.done:
				del PlanBase.done[plan_id]
			PlanBase.draft = None
			PlanBase.Delete(plan_id, plans_path)
			return "Draft plan {} deleted".format(plan_id)

		elif toolName == 'deleteAllPlans':
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

		elif toolName == 'updateTask':
			task_id = params.get('id')
			status = params.get('status')
			if PlanBase.draft and task_id in PlanBase.draft.tasks:
				task = PlanBase.draft.tasks[task_id]
				if status:
					task.status = status
					PlanBase.draft.save(plans_path)
				return str(task.view())
			return "Task not found"

		elif toolName == 'viewTask':
			plan_id = params.get('id')
			return str(PlanBase.View(plan_id, plans_path))

		elif toolName == 'listTasks':
			return str(PlanBase.List(plans_path))

		elif toolName == 'nextTask':
			if not PlanBase.draft:
				return "No active plan. Use createPlan first to create a new plan."
			status = params.get('status', 'completed')
			result = PlanBase.draft.nextTask(self.handle, status)
			if result.get('done'):
				blocked_count = result.get('blocked_count', 0)
				if blocked_count > 0:
					return "DONE_WITH_BLOCKED:{}".format(result.get('message', 'Some tasks were blocked'))
				else:
					PlanBase.draft.jobDone(self.handle)
					return "ALL_COMPLETED:Plan finished successfully"
			return "NEXT_TASK:{}".format(result.get('next_task_instruction', ''))

		elif toolName == 'jobDone':
			if PlanBase.draft:
				return str(PlanBase.draft.jobDone(self.handle))
			return "No active plan. Use createPlan first to create a new plan."

		elif toolName == 'startBuild':
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

		elif toolName == 'LogProgress':
			task_id = params.get('taskId')
			what_was_done = params.get('whatWasDone', '')
			return str(PlanBase.LogProgress(task_id, what_was_done, plans_path))

		return "Unknown plan tool: {}".format(toolName)
