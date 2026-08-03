#--
# class ToolExecutor — load, validate and execute tool invocations
import os, time, json, subprocess, shlex
from src.functions import initmodule, importmodule, splitFileNameExtension
class ToolExecutor():
	#
	_write_tools_validate = {'WriteFile', 'CreateFile', 'AppendFile', 'ReplaceLine', 'Sed'}
	#
	def ExecuteTextTool(self, toolName, params):
		# Execute a tool based on XML invocation
		routed = self._route_execute_script(toolName, params)
		if isinstance(routed, tuple):
			toolName, params = routed
		else:
			return routed
		err = self._load_tool_dynamic(toolName)
		if err is not None:
			return err
		return self._execute_tool_call(toolName, params)

	def _route_execute_script(self, toolName, params):
		# ROUTING: If ExecuteScript is called with a non-script file, route to Terminal
		if toolName.lower() == 'executescript':
			fileName = params.get('fileName', '')
			script_extensions = ['.py', '.sh', '.js', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1']
			is_script = any(fileName.lower().endswith(ext) for ext in script_extensions)
			#
			if not is_script and fileName:
				# Check for shell syntax in args — if found, let ExecuteScript handle it directly
				args_str = params.get('args', '')
				shell_chars = set('|;&><`$')
				has_shell = isinstance(args_str, str) and any(c in args_str for c in shell_chars)
				#
				if has_shell:
					# Shell syntax detected — execute via bash -c directly (skip Terminal routing)
					print("ExecuteScript({}) — shell syntax detected, running via bash -c".format(fileName))
					return _run_shell_command(fileName, args_str)
				#
				# No shell syntax — route to Terminal tool
				print("Routing ExecuteScript({}) to Terminal tool".format(fileName))
				terminal_args = _build_terminal_args(params)
				if 'args' in params:
					return 'Terminal', terminal_args
		return toolName, params

	#

	def _load_tool_dynamic(self, toolName):
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
		return None

	def _execute_tool_call(self, toolName, params):
		# Validate and execute the tool
		h = None
		try:
			h = self.handle.hTC.handles[toolName]['handle']
			info = getattr(h, 'info', {})
			required = info.get('parameters', {}).get('required', [])
			missing = [r for r in required if r not in params or params[r] in (None, '')]
			if missing:
				self._track_tool_failure(toolName, "missing parameter(s): " + ', '.join(missing), info)
				return "Error: Missing required parameter(s): {}{}".format(
					', '.join(missing), self._tool_usage(info))
			#
			return self._execute_cached_or_run(toolName, params, h)
		except Exception as E:
			info = getattr(h, 'info', {}) if h else {}
			self._track_tool_failure(toolName, "errors", info)
			return "Error executing {}: {}{}".format(toolName, E, self._tool_usage(info))

	def _track_tool_failure(self, toolName, details, info):
		# Record a tool failure, tracking consecutive same-tool failures.
		# After 2 consecutive failures, echo + respond with a correct-usage hint.
		self.handle.tool_errors += 1
		if self.handle._last_failed_tool == toolName:
			self.handle._last_failed_tool_count += 1
		else:
			self.handle._last_failed_tool = toolName
			self.handle._last_failed_tool_count = 1
		if self.handle._last_failed_tool_count >= 2:
			usage_hint = (
				"Tool `{}` failed {} times with {}. "
				"Correct format:\n{}"
			).format(toolName, self.handle._last_failed_tool_count, details, self._tool_usage(info))
			self.handle.hLG.echo(usage_hint, {'color':True, 'colorValue':'orange','debugOnly':False})
			self.handle.Response('user', {'content': usage_hint})

	def _execute_cached_or_run(self, toolName, params, h):
		from src.ToolParser import ToolParser
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
	#
	def FireToolInvocation(self, tool_invocations):
		#
		is_plan_mode = self.handle.Options.get('MODE') == 'plan'
		plan_tools = ['addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask', 'viewTask', 'listTasks']
		build_tools = ['LogProgress', 'nextTask', 'viewTask', 'listTasks', 'jobDone', 'startBuild', 'planDone', 'addTask', 'createTask', 'createPlan', 'deleteTask', 'deletePlan', 'deleteDraft', 'deleteAllPlans', 'updateTask']
		#
		# Sort to process createTask before other tools
		tool_invocations = sorted(tool_invocations, key=self._fire_sort_key)
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
			_tool_start, _input_size = self._fire_show_load(toolName, params, action_msg, show_load)
			#
			# File size guard — prevent creating/modifying files larger than AI_MAX_FILE_SIZE
			if self._guard_file_size(toolName, params) is not None:
				continue
			#
			# Path sandbox guard — restrict file access to approved directories
			self._guard_path_sandbox(toolName, params)
			#
			# User tool allow/disallow guard — user overrides plan blocking
			user_blocked = set(self.handle.Options.get('TOOL_BLOCKED', []))
			user_allowed = set(self.handle.Options.get('TOOL_ALLOWED', []))
			if self._guard_user_blocked(toolName, user_blocked) is not None:
				break
			#
			# PLAN mode guard — block write/execute tools and intercept startBuild
			# (user's TOOL_ALLOWED overrides plan blocking)
			if self._guard_plan_mode(toolName, user_allowed, is_plan_mode) is not None:
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
			result = self._fire_post_write_validate(toolName, params, result)
			last_result = result
			#
			# Truncation detection — warn model if response hit num_predict limit
			result = self._fire_truncation_warning(toolName, params, result)
			last_result = result
			#
			# Show loaded message with timing and sizes (verbose mode)
			self._fire_show_loaded(toolName, result, show_load, _tool_start, _input_size)
			#
			self._fire_respond_result(toolName, result)
			#
			self._fire_echo_result(toolName, result)
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

	def _fire_show_load(self, toolName, params, action_msg, show_load):
		if show_load:
			_tool_start = time.time()
			_input_size = len(json.dumps(params))
			self.handle.hLG.echo("Loading tool call {} {}".format(toolName, action_msg), {'color':True, 'colorValue':'cyan'})
		else:
			_tool_start = None
			_input_size = 0
			self.handle.hLG.echo("⚙️ {} {}".format(toolName, action_msg), {'color':True, 'colorValue':'green'})
		return _tool_start, _input_size

	def _fire_post_write_validate(self, toolName, params, result):
		# Post-write syntax validation — warn model immediately if edit broke syntax
		if (toolName in self._write_tools_validate
			and not str(result).startswith('Error')
			and self.handle.Options.get('TOOL_CODE_VALIDATE', True)):
			file_path = params.get('fileName', '')
			if file_path:
				warn = self._validate_file(file_path)
				if warn:
					result = warn + "\n" + str(result)
		return result

	def _fire_truncation_warning(self, toolName, params, result):
		# Truncation detection — warn model if response hit num_predict limit
		if toolName in ('WriteFile', 'CreateFile', 'AppendFile'):
			response_tokens = self.handle.Options.get('NUM_LAST_RESPONSE_TOKENS', 0)
			num_predict = self.handle.Options.get('NUM_PREDICT')
			if num_predict and response_tokens and response_tokens >= num_predict - 200:
				warn = ("⚠ TRUNCATION: File may be incomplete (model hit {} token limit). "
					"Use <WriteFile> for first ~200 lines, then <AppendFile> for subsequent chunks.").format(num_predict)
				result = warn + "\n" + str(result)
				self.handle.Options['CHUNKED_WRITE_HINT'] = True
		return result

	def _fire_show_loaded(self, toolName, result, show_load, _tool_start, _input_size):
		# Show loaded message with timing and sizes (verbose mode)
		if show_load:
			_elapsed = time.time() - _tool_start
			_output_size = len(str(result))
			self.handle.hLG.echo("Loaded in {:.3f}s — Input: {} bytes, Output: {} bytes".format(
				_elapsed, _input_size, _output_size),
				{'color':True, 'colorValue':'green'})

	def _fire_respond_result(self, toolName, result):
		if self.handle.Options.get('TOOL_RESULT_AS_SYSTEM', False):
			self.handle.Response('system',{'content':"☰ Tool [{}] returned:\n{}".format(toolName, str(result))})
		elif self.handle.Options.get('TOOL_RESULT_AS_USER', False):
			self.handle.Response('user',{'content':"☰ Tool [{}] returned:\n{}".format(toolName, str(result))})
		else:
			self.handle.Response('tool',{'content':str(result),'name':toolName})

	def _fire_echo_result(self, toolName, result):
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

	@staticmethod
	def _fire_sort_key(inv):
		name = inv['name']
		if name in ('addTask', 'createTask'):
			return -1
		elif name == 'createPlan':
			return -2
		return 0

	def _guard_file_size(self, toolName, params):
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
				return err
		return None

	def _guard_path_sandbox(self, toolName, params):
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
				if blocked:
					return err
		return None

	def _guard_user_blocked(self, toolName, user_blocked):
		if toolName in user_blocked:
			err = "Error: Tool '{}' is disallowed by user configuration. Ask the user to allow it via the !TOOL command.".format(toolName, toolName)
			self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
			self.handle.Response('tool', {'content': err, 'name': toolName})
			return err
		return None

	def _guard_plan_mode(self, toolName, user_allowed, is_plan_mode):
		if is_plan_mode and (toolName in self._plan_blocked or toolName == 'startBuild'):
			if toolName in user_allowed:
				return None
			elif toolName == 'startBuild':
				err = "Model requested build mode via <startBuild/>. Switch to BUILD mode to start executing."
				self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
				self.handle.Response('tool', {'content': err, 'name': toolName})
				self.handle._plan_blocked_tool = toolName
				return err
			else:
				err = ("Error: {} cannot be used in PLAN mode. "
					   "Switch to BUILD mode with !MODE build to use this tool, "
					   "or use !TOOL ALLOW {} to override.".format(toolName, toolName))
				self.handle.hLG.echo(err, {'color': True, 'colorValue': 'red', 'debugOnly': False})
				self.handle.Response('tool', {'content': err, 'name': toolName})
				self.handle._plan_blocked_tool = toolName
				return err
		return None

#--

def _run_shell_command(fileName, args_str):
	"""Execute a non-script command via bash -c directly. Returns output."""
	full_cmd = "{} {}".format(fileName, args_str)
	try:
		result = subprocess.run(
			["bash", "-c", full_cmd],
			capture_output=True, text=True, timeout=30, cwd="."
		)
		output = ""
		if result.stdout:
			output += result.stdout
		if result.stderr:
			output += "\nSTDERR:\n{}".format(result.stderr)
		return output if output else "(no output)"
	except subprocess.TimeoutExpired:
		return "Error: Script execution timed out (30s limit)"
	except Exception as E:
		return "Error: {}".format(E)

#--

def _build_terminal_args(params):
	"""Convert ExecuteScript params into Terminal arg1/arg2/... args."""
	terminal_args = {}
	terminal_args['arg1'] = params.get('fileName', '')
	#
	# Add additional args if provided
	if 'args' in params:
		args = params['args']
		# Handle if args is a string (could be JSON array, Python list repr, or space-separated)
		if isinstance(args, str):
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
					try:
						parsed_args = shlex.split(args)
						for i, arg in enumerate(parsed_args, start=2):
							terminal_args['arg{}'.format(i)] = arg
					except (ValueError, TypeError):
						terminal_args['arg2'] = args
		elif isinstance(args, list):
			for i, arg in enumerate(args, start=2):
				terminal_args['arg{}'.format(i)] = str(arg)
	return terminal_args
