"""
ToolParser - Handles parsing of XML tool invocations and job completion detection
"""
import re
import os
import time
import json
from src.functions import initmodule,importmodule,splitFileNameExtension

class ToolParser:
	"""
	Parses AI responses for XML tool invocations and job_done tags
	"""
	_current_handle = None  # Set before tool.run() for tools that need handle access
	_plan_blocked = {
		'WriteFile', 'CreateFile', 'AppendFile', 'ReplaceLine', 'Sed',
		'Sort', 'Terminal', 'ExecuteScript',
		'WWW', 'WWWExec', 'WWWJS', 'WWWScript',
		'SiteScript', 'UpdateSiteScript',
		'startBuild',
	}
	_plan_tools = {
		'addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan',
		'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks',
		'nextTask', 'jobDone', 'planDone', 'startBuild', 'LogProgress',
	}
	#--
	def __init__(self, opts={}):
		self.logger = opts['logger'] if 'logger' in opts else None
		self.handle = opts['handle'] if 'handle' in opts else None # to master class / Handle()
		self._known_tools = None

	def get_known_tools(self):
		"""Return set of all known tool names (file-based + built-in plan/blocked)."""
		if self._known_tools is not None:
			return self._known_tools
		tools = set()
		tools.update(self._plan_blocked)
		tools.update(self._plan_tools)
		tools_path = self.handle.Options.get('tools_path', 'tools') if self.handle else 'tools'
		if os.path.exists(tools_path):
			for f in os.listdir(tools_path):
				if f.startswith("tool_") and f.endswith(".py"):
					tools.add(f[5:-3])
		self._known_tools = tools
		return tools
	#--
	def ParseTextToolInvocation(self, text):
		# Parse XML-style tool invocations like: <ReadFile><fileName>test.txt</fileName></ReadFile>
		# Also handles self-closing tags: <listTools/>
		# Returns: [{'name':'ReadFile', 'parameters':{'fileName':'test.txt'}}, ...]
		#
		# Strip HTML comments first — the model may regurgitate HISTORY.md which
		# contains old tool calls embedded in <!-- ... --> blocks. These are NOT
		# new tool invocations and should not be detected.
		text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
		#
		# Strip <think>...</think> tags — the model may include these in the
		# content field (separate from the native thinking API).  They should
		# NOT be treated as tool calls.
		text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
		# Also strip orphan </think> closing tags that appear without openers
		text = re.sub(r'</think>', '', text)
		#
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
				raw = pm.group(2)
				if pm.group(1) in ('replacement', 'contentOfFile'):
					params[pm.group(1)] = raw
				else:
					params[pm.group(1)] = raw.strip('\n').rstrip('\r')
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
		# Check if response contains <job_done/> or <job_done></job_done>
		pattern1 = r'<job_done\s*/?>'
		pattern2 = r'<job_done>.*?</job_done>'
		#
		if re.search(pattern1, text, re.IGNORECASE) or re.search(pattern2, text, re.IGNORECASE):
			return True
		return False
	
	#
	def ExtractToolResult(self, text):
		# Remove all tool invocations from text, return clean text
		# Used to get the actual response without XML tool calls
		#import re
		#
		# Remove self-closing tags
		text = re.sub(r'<\w+\s*/>', '', text)
		#
		# Remove opening and closing tags with content (greedy match to handle nested same-name tags)
		text = re.sub(r'<(\w+)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
		# Remove any remaining orphaned closing tags
		text = re.sub(r'</\w+>', '', text)
		#
		return text.strip()
	
	#
	def _format_action(self, toolName, params):
		"""Return a human-readable action description for a tool invocation."""
		if toolName == 'ReplaceLine':
			fileName = params.get('fileName', '?')
			fl = params.get('fromLine', '?')
			tl = params.get('toLine', fl)
			return "Editing '{}' lines {}-{}".format(fileName, fl, tl)
		elif toolName == 'WriteFile':
			fileName = params.get('fileName', '?')
			content = params.get('contentOfFile', '')
			return "Writing {} bytes to '{}'".format(len(content), fileName)
		elif toolName == 'AppendFile':
			fileName = params.get('fileName', '?')
			fl = params.get('fromLineNumber', '-1')
			if fl is None or fl == -1 or str(fl) == '-1':
				fl = 'end'
			elif str(fl) == '0':
				fl = 'start'
			else:
				fl = 'line {}'.format(fl)
			content = params.get('contentOfFile', '')
			return "Appending {} bytes to '{}' at {}".format(len(content), fileName, fl)
		elif toolName == 'CreateFile':
			fileName = params.get('fileName', '?')
			return "Creating new file '{}'".format(fileName)
		elif toolName == 'ReadFile':
			fileName = params.get('fileName', '?')
			return "Reading '{}'".format(fileName)
		elif toolName == 'Terminal':
			args = [params.get('arg{}'.format(i), '') for i in range(1, 6)]
			args = [a for a in args if a]
			return "$ {}".format(' '.join(args)) if args else "Running terminal command"
		elif toolName == 'WWW':
			url = params.get('url', '?')
			return "Fetching: {}".format(url)
		elif toolName == 'Grep':
			pat = params.get('pattern', '?')
			fn = params.get('fileName', '')
			return "Searching '{}' in {}".format(pat, fn if fn else 'all files')
		elif toolName == 'listTools':
			return "Listing available tools"
		elif toolName == 'TreeView':
			path = params.get('path', '.')
			depth = params.get('depth', '3')
			return "Tree view of '{}' (depth={})".format(path, depth)
		elif toolName == 'List':
			path = params.get('path', '.')
			return "Listing '{}'".format(path)
		elif toolName == 'Find':
			pat = params.get('pattern', '*')
			path = params.get('path', '.')
			return "Finding '{}' in '{}'".format(pat, path)
		elif toolName == 'ExecuteScript':
			fn = params.get('fileName', '?')
			args = params.get('args', '')
			return "Running script '{}' {}".format(fn, args)
		elif toolName == 'Head':
			fn = params.get('fileName', '?')
			n = params.get('lines', '10')
			return "First {} lines of '{}'".format(n, fn)
		elif toolName == 'Tail':
			fn = params.get('fileName', '?')
			n = params.get('lines', '10')
			return "Last {} lines of '{}'".format(n, fn)
		elif toolName == 'Sed':
			pat = params.get('pattern', '?')
			fn = params.get('fileName', '?')
			return "Replacing '{}' in '{}'".format(pat, fn)
		elif toolName == 'Diff':
			f1 = params.get('file1', '?')
			f2 = params.get('file2', '?')
			return "Comparing '{}' vs '{}'".format(f1, f2)
		elif toolName == 'Sort':
			fn = params.get('fileName', '?')
			return "Sorting '{}'".format(fn)
		elif toolName == 'SaveTip':
			title = params.get('title', '?')
			return "Saving tip '{}'".format(title)
		elif toolName == 'GetTip':
			title = params.get('title', '?')
			return "Loading tip '{}'".format(title)
		elif toolName == 'ListTips':
			return "Listing saved tips"
		elif toolName == 'DeleteTip':
			title = params.get('title', '?')
			return "Deleting tip '{}'".format(title)
		elif toolName == 'ReinsertTip':
			title = params.get('title', '?')
			return "Reinserting tip '{}' into context".format(title)
		elif toolName in ('createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks', 'nextTask', 'jobDone', 'planDone', 'startBuild', 'LogProgress'):
			title = params.get('title', params.get('instruction', ''))
			if title:
				return "{}: {}".format(toolName, title[:60])
			return "{}".format(toolName)
		else:
			params_str = ', '.join(['{}={}'.format(k, v) for k, v in params.items()])
			return "{} {}".format(toolName, params_str if params_str else '')
	#
	def ExecuteTextTool(self, toolName, params):
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
						except (ValueError, TypeError):
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
							except (ValueError, TypeError):
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
					except Exception:
						continue
				# Fallback: scan module for any class matching case-insensitively
				if h is None:
					import inspect
					for attr_name, attr_val in inspect.getmembers(mod, inspect.isclass):
						if attr_name.lower() == toolName.lower():
							try:
								h = attr_val()
								break
							except Exception:
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
				# Track consecutive same-tool failures and inject correct-usage hint
				if self.handle._last_failed_tool == toolName:
					self.handle._last_failed_tool_count += 1
				else:
					self.handle._last_failed_tool = toolName
					self.handle._last_failed_tool_count = 1
				if self.handle._last_failed_tool_count >= 2:
					usage_hint = (
						"Tool `{}` failed {} times with missing parameter(s): {}. "
						"Correct format:\n{}"
					).format(toolName, self.handle._last_failed_tool_count,
						', '.join(missing), self._tool_usage(info))
					self.handle.hLG.echo(usage_hint, {'color':True, 'colorValue':'orange','debugOnly':False})
					self.handle.Response('user', {'content': usage_hint})
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
			if self.handle.Options.get('TOOL_SHOW_LOAD', True):
				self.handle.hLG.echo("Executing tool call {}...".format(toolName),
					{'color':True, 'colorValue':'yellow'})
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
			# Track consecutive same-tool failures for exception path too
			if self.handle._last_failed_tool == toolName:
				self.handle._last_failed_tool_count += 1
			else:
				self.handle._last_failed_tool = toolName
				self.handle._last_failed_tool_count = 1
			info = getattr(h, 'info', {}) if h else {}
			if self.handle._last_failed_tool_count >= 2:
				usage_hint = (
					"Tool `{}` failed {} times with errors. "
					"Correct format:\n{}"
				).format(toolName, self.handle._last_failed_tool_count, self._tool_usage(info))
				self.handle.hLG.echo(usage_hint, {'color':True, 'colorValue':'orange','debugOnly':False})
				self.handle.Response('user', {'content': usage_hint})
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
	_write_tools_validate = {'WriteFile', 'CreateFile', 'AppendFile', 'ReplaceLine', 'Sed'}
	#
	@staticmethod
	def _validate_file(path):
		"""Check syntax of a file after write-tools edit it. Returns warning string or None."""
		if not path or not os.path.isfile(path):
			return None
		ext = os.path.splitext(path)[1].lower()
		# Read validate mapping from config
		try:
			from config import Options as _opts
			mapping = _opts.get('TOOL_CODE_VALIDATE_EXT', {'.py': 'python', '.js': 'javascript', '.sh': 'bash'})
		except Exception:
			mapping = {'.py': 'python', '.js': 'javascript', '.sh': 'bash'}
		vtype = mapping.get(ext)
		if not vtype:
			return None
		try:
			if vtype == 'python':
				import py_compile
				py_compile.compile(path, doraise=True)
			elif vtype == 'javascript':
				import subprocess
				r = subprocess.run(['node', '--check', path],
					capture_output=True, text=True, timeout=10)
				if r.returncode != 0:
					return "⚠ Syntax error in '{}' (JS): {}".format(
						os.path.basename(path), r.stderr.strip() or r.stdout.strip())
			elif vtype == 'bash':
				import subprocess
				r = subprocess.run(['bash', '-n', path],
					capture_output=True, text=True, timeout=10)
				if r.returncode != 0:
					return "⚠ Syntax error in '{}' (Bash): {}".format(
						os.path.basename(path), r.stderr.strip() or r.stdout.strip())
		except py_compile.PyCompileError as e:
			return "⚠ Syntax error in '{}': {}".format(os.path.basename(path), str(e))
		except Exception:
			pass  # validator not available (e.g. node not installed) — skip silently
		return None
	#
	def FireToolInvocation(self, tool_invocations):
		#
		is_plan_mode = self.handle.Options.get('MODE') == 'plan'
		plan_tools = ['addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks']
		build_tools = ['LogProgress', 'nextTask', 'viewTask', 'listTasks', 'jobDone', 'startBuild', 'planDone', 'addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask']
		#
		# Sort to process createTask before other tools
		def sort_key(inv):
			name = inv['name']
			if name in ('addTask', 'createTask'):
				return -1
			elif name == 'createPlan':
				return -2
			return 0
		tool_invocations = sorted(tool_invocations, key=sort_key)
		#
		job_done = False
		last_result = None
		for inv in tool_invocations:
			toolName = inv['name']
			params   = inv['parameters']
			#
			self.handle.tool_iteration += 1
			#
			# Show user what tool is being called (human-readable preview)
			action_msg = self._format_action(toolName, params)
			show_load = self.handle.Options.get('TOOL_SHOW_LOAD', True)
			if show_load:
				_tool_start = time.time()
				_input_size = len(json.dumps(params))
				self.handle.hLG.echo("Loading tool call {} {}".format(toolName, action_msg), {'color':True, 'colorValue':'cyan'})
			else:
				self.handle.hLG.echo("⚙️ {} {}".format(toolName, action_msg), {'color':True, 'colorValue':'green'})
			#
			# File size guard — prevent creating/modifying files larger than AI_MAX_FILE_SIZE
			_write_tools = {
				'WriteFile': 'contentOfFile',
				'CreateFile': 'contentOfFile',
				'AppendFile': 'contentOfFile',
				'ReplaceLine': 'replacement',
			}
			if toolName in _write_tools:
				content_param = _write_tools[toolName]
				content = params.get(content_param, '')
				content_bytes = len(content.encode('utf-8'))
				max_size = self.handle.Options.get('AI_MAX_FILE_SIZE', 2097152)
				total_bytes = content_bytes
				existing_bytes = 0
				if toolName == 'AppendFile':
					file_path = params.get('fileName', '')
					if file_path and os.path.exists(file_path):
						existing_bytes = os.path.getsize(file_path)
						total_bytes += existing_bytes
				if total_bytes > max_size:
					err = ("Error: {} not executed — content exceeds AI_MAX_FILE_SIZE "
						   "({} bytes). Total would be: {} bytes "
						   "(existing: {}, new: {}). "
						   "Split the content or reduce file size."
						   .format(toolName, max_size, total_bytes, existing_bytes, content_bytes))
					self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
					self.handle.Response('tool', {'content': err, 'name': toolName})
					continue
			#
			# Path sandbox guard — restrict file access to approved directories
			_path_approver = self.handle.Options.get('path_approver')
			if _path_approver:
				_path_tools = {
					'ReadFile': ['fileName'],
					'WriteFile': ['fileName'],
					'CreateFile': ['fileName'],
					'AppendFile': ['fileName'],
					'ReplaceLine': ['fileName'],
					'Grep': ['fileName'],
					'Sed': ['fileName'],
					'Head': ['fileName'],
					'Tail': ['fileName'],
					'Sort': ['fileName'],
					'Diff': ['file1', 'file2'],
					'TreeView': ['path'],
					'List': ['path'],
					'Find': ['path'],
					'ExecuteScript': ['fileName'],
				}
				if toolName in _path_tools:
					blocked = False
					for param in _path_tools[toolName]:
						raw = params.get(param, '')
						if raw and not _path_approver.is_allowed(raw):
							err = ("Error: {} param '{}' = '{}' is not in an approved path. "
								   "Ask the user to approve this path via the !PROJECT command."
								   .format(toolName, param, raw))
							self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
							self.handle.Response('tool', {'content': err, 'name': toolName})
							blocked = True
							break
						if blocked:
							continue
			#
			# User tool allow/disallow guard — user overrides plan blocking
			user_blocked = set(self.handle.Options.get('TOOL_BLOCKED', []))
			user_allowed = set(self.handle.Options.get('TOOL_ALLOWED', []))
			if toolName in user_blocked:
				err = "Error: Tool '{}' is disallowed by user configuration. Ask the user to allow it via the !TOOL command.".format(toolName, toolName)
				self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
				self.handle.Response('tool', {'content': err, 'name': toolName})
				break
			#
			# PLAN mode guard — block write/execute tools and intercept startBuild
			# (user's TOOL_ALLOWED overrides plan blocking)
			if is_plan_mode and (toolName in self._plan_blocked or toolName == 'startBuild'):
				if toolName in user_allowed:
					pass  # user explicitly allowed — skip plan block
				elif toolName == 'startBuild':
					err = "Model requested build mode via <startBuild/>. Switch to BUILD mode to start executing."
					self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
					self.handle.Response('tool', {'content': err, 'name': toolName})
					self.handle._plan_blocked_tool = toolName
					break
				else:
					err = ("Error: {} cannot be used in PLAN mode. "
						   "Switch to BUILD mode with !MODE build to use this tool, "
						   "or use !TOOL ALLOW {} to override.".format(toolName, toolName))
					self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
					self.handle.Response('tool', {'content': err, 'name': toolName})
					self.handle._plan_blocked_tool = toolName
					break
			#
			# Route to plan tools if in plan mode, or build tools (like LogProgress)
			if (is_plan_mode and toolName in plan_tools) or (toolName in build_tools):
				result = self.HandlePlanTool(toolName, params)
			else:
				result = self.ExecuteTextTool(toolName, params)
			last_result = result
			#
			# Post-write syntax validation — warn model immediately if edit broke syntax
			if (toolName in self._write_tools_validate
				and not str(result).startswith('Error')
				and self.handle.Options.get('TOOL_CODE_VALIDATE', True)):
				file_path = params.get('fileName', '')
				if file_path:
					warn = self._validate_file(file_path)
					if warn:
						result = warn + "\n" + str(result)
						last_result = result
			#
			# Show loaded message with timing and sizes (verbose mode)
			if show_load:
				_elapsed = time.time() - _tool_start
				_output_size = len(str(result))
				self.handle.hLG.echo("Loaded in {:.3f}s — Input: {} bytes, Output: {} bytes".format(
					_elapsed, _input_size, _output_size),
					{'color':True, 'colorValue':'green'})
			#
			if self.handle.Options.get('TOOL_RESULT_AS_SYSTEM', False):
				self.handle.Response('system',{'content':"☰ Tool [{}] returned:\n{}".format(toolName, str(result))})
			elif self.handle.Options.get('TOOL_RESULT_AS_USER', False):
				self.handle.Response('user',{'content':"☰ Tool [{}] returned:\n{}".format(toolName, str(result))})
			else:
				self.handle.Response('tool',{'content':str(result),'name':toolName})
			#
			# (Just on print to console. Chat History should have always original data!) Truncate result if too long
			MAX_PREVIEW = 500
			result_str = str(result)
			if len(result_str) > MAX_PREVIEW:
				result_str = result_str[:MAX_PREVIEW] + "... (truncated, {} chars total)".format(len(str(result)))
			#
			echo_opts = {'color':True, 'colorValue':'green'}
			if result_str.startswith('Error: ') or result_str.startswith('Warning: '):
				echo_opts['debugOnly'] = False
				if result_str.startswith('Error: '):
					echo_opts['colorValue'] = 'red'
				else:
					echo_opts['colorValue'] = 'orange'
			self.handle.hLG.echo("✓ {}: {}".format(toolName, result_str), echo_opts)
			#
			# Track jobDone to signal Parse/AI loop
			if toolName == 'jobDone':
				job_done = True
			# Reset error counter on success
			if not str(result).startswith('Error'):
				self.handle.tool_errors = 0
				self.handle._last_failed_tool = None
				self.handle._last_failed_tool_count = 0
			self.handle.hLG.echo("--- Tool iterations: {} | errors: {}".format(self.handle.tool_iteration, self.handle.tool_errors), {'color':True, 'colorValue':'cyan'})
		return last_result
	#
	def HandlePlanTool(self, toolName, params):
		from src.PlanManager import PlanBase, Plan, PlanTask

		plans_path = self.handle.Options.get('plans_path', 'plans')

		if toolName == 'addTask':
			# Alias for createTask — normalizes XML param names the model hallucinates
			toolName = 'createTask'
			if 'taskTitle' in params and 'title' not in params:
				params['title'] = params.pop('taskTitle')
			if 'taskDescription' in params and 'instruction' not in params:
				params['instruction'] = params.pop('taskDescription')
			# Fallthrough to createTask

		if toolName == 'createTask':
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
			task_id = params.get('id')
			if task_id and PlanBase.draft:
				task = PlanBase.draft.tasks.get(task_id)
				if task:
					result = task.delete()
					del PlanBase.draft.tasks[task_id]
					PlanBase.draft.save(plans_path)
					return str(result)
			return "Error: task id required or no active plan"

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

		elif toolName == 'clearAllTasks':
			if PlanBase.draft:
				count = len(PlanBase.draft.tasks)
				PlanBase.draft.tasks = {}
				PlanBase.draft.save(plans_path)
				return "Cleared {} tasks from current plan".format(count)
			return "No active plan"

		elif toolName == 'cancelPlan':
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

		elif toolName == 'jobDone':
			if PlanBase.draft:
				result = str(PlanBase.draft.jobDone(self.handle))
				if hasattr(self.handle, '_write_current_task'):
					self.handle._write_current_task()
				return result
			return "No active plan. Use createPlan first to create a new plan."

		elif toolName == 'planDone':
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

		elif toolName == 'LogProgress':
			task_id = params.get('taskId')
			what_was_done = params.get('whatWasDone', '')
			return str(PlanBase.LogProgress(task_id, what_was_done, plans_path))

		return "Unknown plan tool: {}".format(toolName)
