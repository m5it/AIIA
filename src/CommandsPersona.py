#--
# class CommandsPersona — persona / tool-toggle commands
class CommandsPersona():
	#
	def CMD_INSTALL_DEPS(self, inp=""):
		parts = inp.strip().split()
		name = parts[1] if len(parts) > 1 else self.handle.Options.get('INSTRUCT_CLASS', '')
		if not name:
			print("No persona specified and no current persona set.")
			return 2
		cls_path = self.handle.Options.get('INSTRUCT_PATH', 'instruct')
		mod = importmodule(name, False, {'path': cls_path})
		if not mod:
			print("Persona '{}' not found.".format(name))
			return 2
		cls = None
		for n in [name, name.lower(), name.upper()]:
			try:
				cls = getattr(mod, n)
				if cls:
					break
			except Exception:
				continue
		if not cls:
			print("Could not load persona '{}'.".format(name))
			return 2
		requirements = getattr(cls, 'requirements', None)
		if not requirements:
			print("Persona '{}' has no dependency requirements.".format(name))
			return 2
		try:
			req_dict = requirements(cls)
		except Exception:
			print("Failed to read requirements for '{}'.".format(name))
			return 2
		if not req_dict:
			print("Persona '{}' has no dependency requirements.".format(name))
			return 2
		self.handle.hLG.echo("Installing dependencies for '{}'...".format(name),
			{'color':True, 'colorValue':'cyan','debugOnly':False})
		from src.DependencyInstaller import install as install_deps
		ok = install_deps(name, req_dict, self.handle)
		if ok:
			self.handle.hLG.echo("All dependencies installed for '{}'.".format(name),
				{'color':True, 'colorValue':'green','debugOnly':False})
		else:
			self.handle.hLG.echo("Some dependencies failed. Run !INSTALL_DEPS {} to retry.".format(name),
				{'color':True, 'colorValue':'orange','debugOnly':False})
		return 2
	#
	def CMD_PROJECT(self, inp=""):
		"""!PROJECT — view or modify project path approvals"""
		pa = self.handle.Options.get('path_approver')
		if not pa:
			print("No path approver configured.")
			return 2
		parts = inp.strip().split()
		if len(parts) < 2:
			self._project_show(pa)
			return 2
		action = parts[1].upper()
		if action == 'ADD' and len(parts) >= 4:
			self._project_add(pa, parts)
		elif action == 'DENY' and len(parts) >= 3:
			path = ' '.join(parts[2:])
			pa.deny(path)
			pa.save()
			print("Denied path '{}'".format(path))
		elif action == 'REMOVE' and len(parts) >= 4:
			self._project_remove(pa, parts)
		elif action == 'RESET':
			pa.approved_dirs = {'.'}
			pa.approved_files = set()
			pa.denied_paths = set()
			pa.save()
			print("Path approvals reset to default (only working directory).")
		else:
			self._project_usage()
		return 2

	def _project_show(self, pa):
		print("Project Path Approvals:")
		print("  Working dir:", pa.working_dir)
		print("  Approved dirs: {}".format(sorted(pa.approved_dirs) if pa.approved_dirs else "(none - defaults to .)"))
		print("  Approved files: {}".format(sorted(pa.approved_files) if pa.approved_files else "(none)"))
		print("  Denied paths: {}".format(sorted(pa.denied_paths) if pa.denied_paths else "(none)"))

	def _project_add(self, pa, parts):
		kind = parts[2].upper()
		path = ' '.join(parts[3:])
		if kind == 'DIR':
			pa.add_dir(path)
			pa.save()
			print("Approved directory '{}'".format(path))
		elif kind == 'FILE':
			pa.add_file(path)
			pa.save()
			print("Approved file '{}'".format(path))
		else:
			print("Usage: !PROJECT ADD DIR <path> or !PROJECT ADD FILE <path>")

	def _project_remove(self, pa, parts):
		kind = parts[2].upper()
		path = ' '.join(parts[3:])
		if kind == 'DIR':
			pa.approved_dirs.discard(path)
			pa.save()
			print("Removed approved directory '{}'".format(path))
		elif kind == 'FILE':
			pa.approved_files.discard(path)
			pa.save()
			print("Removed approved file '{}'".format(path))
		else:
			print("Usage: !PROJECT REMOVE DIR <path> or !PROJECT REMOVE FILE <path>")

	def _project_usage(self):
		print("Unknown command. Usage:")
		print("  !PROJECT — show current approvals")
		print("  !PROJECT ADD DIR <path> — approve a directory")
		print("  !PROJECT ADD FILE <path> — approve a file")
		print("  !PROJECT DENY <path> — block a path")
		print("  !PROJECT REMOVE DIR|FILE <path> — remove an approval")
		print("  !PROJECT RESET — reset to defaults")
	#
	def CMD_BUILD_THINK(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 2:
			current = self.handle.Options.get('BUILD_THINKING_DISABLED', True)
			print("Build thinking disabled: {}".format(current))
			print("Usage: !BUILD_THINK true  (disable thinking)")
			print("       !BUILD_THINK false (enable thinking)")
			return 2
		val = parts[1].strip().lower()
		if val == 'true':
			self.handle.Options['BUILD_THINKING_DISABLED'] = True
			print("Build thinking DISABLED. Model will be concise and direct.")
		elif val == 'false':
			self.handle.Options['BUILD_THINKING_DISABLED'] = False
			print("Build thinking ENABLED. Model can reason step by step.")
		else:
			print("Invalid value: {}. Use true or false.".format(val))
			return 2
		# Update system prompt with new thinking setting
		self.handle._replace_system_prompt(self.handle.hPP._get_mode_instructions(self.handle.Options['MODE']))
		return 2

	def CMD_AUTO_CONTINUE(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 2:
			current = self.handle.Options.get('AUTO_CONTINUE_ALL_TASKS', True)
			print("Auto-continue: {}".format("enabled" if current else "disabled"))
			return 2
		val = parts[1].strip().lower()
		if val == 'true':
			self.handle.Options['AUTO_CONTINUE_TASKS'] = True
			self.handle.Options['AUTO_CONTINUE_ALL_TASKS'] = True
			self.handle._write_state({'auto_continue': True})
			print("Auto-continue ENABLED")
		elif val == 'false':
			self.handle.Options['AUTO_CONTINUE_TASKS'] = False
			self.handle.Options['AUTO_CONTINUE_ALL_TASKS'] = False
			self.handle._write_state({'auto_continue': False})
			print("Auto-continue DISABLED — user input required after each task")
		else:
			print("Invalid. Use true or false.")
			return 2
		return 2

	def CMD_TOOLS(self, inp=""):
		parts = inp.strip().split()
		action = parts[1].upper() if len(parts) > 1 else 'ALL'
		#
		# Get all known tool names
		all_tools = sorted(self.handle.hTP.get_known_tools())
		# Remove internal/non-executable tool names
		all_tools = [t for t in all_tools if t not in ('startBuild',)]
		#
		user_blocked = set(self.handle.Options.get('TOOL_BLOCKED', []))
		user_allowed = set(self.handle.Options.get('TOOL_ALLOWED', []))
		plan_blocked = self.handle.hTP._plan_blocked
		is_plan = self.handle.Options.get('MODE') == 'plan'
		#
		def effective_status(tool):
			if tool in user_blocked:
				return "User Blocked"
			if is_plan and tool in plan_blocked and tool not in user_allowed:
				return "Plan Blocked"
			if tool in user_allowed:
				return "User Allowed"
			return "Allowed"
		#
		if action == 'ALLOWED':
			allowed = [t for t in all_tools if effective_status(t) == 'Allowed' or effective_status(t) == 'User Allowed']
			print("\n=== Allowed Tools ({}) ===".format(len(allowed)))
			for t in allowed:
				print("  {}".format(t))
		elif action == 'DISALLOWED':
			disallowed = [t for t in all_tools if effective_status(t) in ('User Blocked', 'Plan Blocked')]
			if not disallowed:
				print("\nNo tools disallowed.")
			else:
				print("\n=== Disallowed Tools ({}) ===".format(len(disallowed)))
				for t in disallowed:
					print("  {} ({})".format(t, effective_status(t)))
		else:
			# Show all with effective status
			print("\n=== All Tools ({}) ===".format(len(all_tools)))
			for t in all_tools:
				status = effective_status(t)
				if status == 'User Allowed':
					status = 'Allowed (override)'
				elif status == 'Plan Blocked':
					status = 'Blocked (plan mode)'
				elif status == 'User Blocked':
					status = 'Blocked (user)'
				print("  {} ({})".format(t, status))
		print("")
		return 2

	def CMD_TOOL(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 3:
			print("Usage: !TOOL ALLOW|DISALLOW <toolName>")
			return 2
		action = parts[1].upper()
		tool_name = parts[2]
		#
		# Find the canonical tool name (case-insensitive match)
		all_tools = self.handle.hTP.get_known_tools()
		canonical = None
		for t in all_tools:
			if t.lower() == tool_name.lower():
				canonical = t
				break
		if not canonical:
			print("Tool '{}' not found. Use !TOOLS to see available tools.".format(tool_name))
			return 2
		#
		blocked = set(self.handle.Options.get('TOOL_BLOCKED', []))
		allowed = set(self.handle.Options.get('TOOL_ALLOWED', []))
		#
		if action == 'DISALLOW':
			if canonical in ('startBuild',):
				print("Cannot disallow internal tool '{}'.".format(canonical))
				return 2
			blocked.add(canonical)
			allowed.discard(canonical)
			self.handle.Options['TOOL_BLOCKED'] = blocked
			self.handle.Options['TOOL_ALLOWED'] = allowed
			self.handle._write_state({'tool_blocked': list(blocked), 'tool_allowed': list(allowed)})
			self.handle._pending_tool_notice = (
				"[Auto notice: Tool '{}' is now DISALLOWED. "
				"It cannot be used until re-enabled with !TOOL ALLOW {}.]"
				.format(canonical, canonical))
			print("Tool '{}' DISALLOWED. ({} allowed, {} disallowed)".format(
				canonical, len(all_tools) - len(blocked), len(blocked)))
		elif action == 'ALLOW':
			blocked.discard(canonical)
			allowed.add(canonical)
			self.handle.Options['TOOL_BLOCKED'] = blocked
			self.handle.Options['TOOL_ALLOWED'] = allowed
			self.handle._write_state({'tool_blocked': list(blocked), 'tool_allowed': list(allowed)})
			self.handle._pending_tool_notice = (
				"[Auto notice: Tool '{}' is now ALLOWED. "
				"You may use it in your next response.]"
				.format(canonical))
			print("Tool '{}' ALLOWED. ({} allowed, {} disallowed)".format(
				canonical, len(all_tools) - len(blocked), len(blocked)))
		else:
			print("Unknown action '{}'. Use ALLOW or DISALLOW.".format(action))
		return 2

	def CMD_INSTRUCT_LIST(self, inp=""):
		print("Available personas:")
		self.handle.hIM.Available()
		return 2

	def CMD_INSTRUCT_SWITCH(self, inp=""):
		parts = inp.strip().split()
		if len(parts) < 2:
			print("Usage: !INSTRUCT_SWITCH <persona_name>")
			return 2
		name = parts[1]
		if not self.handle.hIM.Exists(name):
			print("Persona '{}' not found. Use !INSTRUCT_LIST to see available personas.".format(name))
			return 2
		self.handle.Options['INSTRUCT_CLASS'] = name
		self.handle.hIM.ApplyPersonaModel(name)
		mode = self.handle.Options.get('MODE', 'build')
		system_content = self.handle.hPP._get_mode_instructions(mode)
		if self.handle.hHM.msgs and self.handle.hHM.msgs[-1]['role'] == 'system':
			self.handle.hHM.msgs[-1]['content'] = system_content
		else:
			self.handle.Response('system', {'content': system_content})
		self.handle.hLG.echo("Switched persona to '{}'".format(name), {'color':True, 'colorValue':'green'})
		return 2

