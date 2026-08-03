#--
# class CommandsConfig — config / model / backend commands
import json
class CommandsConfig():
	#
	def CMD_SET(self, inp=""):
		a = inp.split(None, 1)
		if len(a) < 2:
			self._set_show_config()
			return 2
		parts = a[1].split(None, 1)
		if len(parts) < 2:
			print("Usage: !SET <key> <value>  or  !SET <key>=<value>")
			return 2
		key = parts[0].rstrip('=')
		raw = parts[1]
		if self._set_check_readonly(key):
			return 2
		val = _parse_set_value(raw)
		self._set_apply(key, val)
		return 2

	def _set_show_config(self):
		# No args — dump the full current config (secrets masked)
		print("\nCurrent config (use !SET <key> <value> to change):")
		for k in sorted(self.handle.Options.keys()):
			v = self._mask_secret(k, self.handle.Options[k])
			if isinstance(v, dict):
				print("  {} = {}".format(k, json.dumps(v)))
			elif isinstance(v, list):
				print("  {} = {}".format(k, v))
			else:
				print("  {} = {}".format(k, v))
		print("\nRead-only keys: VERSION, VERSION_NAME, AI_SESS_ID, AI_ROW_ID, path, tools_path, NUM_*_TOKENS")

	def _set_check_readonly(self, key):
		readonly = {
			'VERSION', 'VERSION_NAME', 'AI_FILE_STATE', 'AI_FILE_HISTORY',
			'AI_SESS_ID', 'AI_ROW_ID', 'path', 'tools_path',
			'NUM_PROMPT_TOKENS', 'NUM_RESPONSE_TOKENS',
			'NUM_LAST_PROMPT_TOKENS', 'NUM_LAST_RESPONSE_TOKENS',
			'DRAFT_CONTENT', 'BACKGROUND_LOG',
		}
		if key in readonly:
			print("Cannot set read-only key '{}'.".format(key))
			return True
		return False

	def _set_apply(self, key, val):
		# Validate AI_BACKEND values (unknown names silently fall back to ollama)
		if key == 'AI_BACKEND':
			if not isinstance(val, str) or val.lower() not in ('ollama', 'vllm'):
				print("Invalid AI_BACKEND '{}' — must be 'ollama' or 'vllm'. Use !BACKEND <name>.".format(val))
				return False
			val = val.lower()
		# Special handling for AI_OPTIONS (dict deep-merge)
		if key == 'AI_OPTIONS':
			if not isinstance(val, dict):
				print("AI_OPTIONS requires a JSON dict, e.g.: !SET AI_OPTIONS '{\"temperature\":0.8,\"num_predict\":16384}'")
				return False
			self.handle.Options['AI_OPTIONS'].update(val)
			print("AI_OPTIONS updated: {}".format(json.dumps(self.handle.Options['AI_OPTIONS'])))
		else:
			self.handle.Options[key] = val
			print("Set {} = {}".format(key, val))
		# Persist key settings to state.aiia
		if key == 'WWW_USER_AGENT':
			self.handle._write_state({'WWW_USER_AGENT': val})
		return True
	#
	def CMD_GET(self, inp=""):
		a = inp.split(None, 1)
		if len(a) < 2:
			print("Usage: !GET <key>")
			return 2
		key = a[1].strip()
		val = self._mask_secret(key, self.handle.Options.get(key))
		if val is None and key not in self.handle.Options:
			print("Unknown key '{}'.".format(key))
		elif isinstance(val, dict):
			print("{} = {}".format(key, json.dumps(val)))
		else:
			print("{} = {}".format(key, val))
		return 2
	#
	def CMD_MODE(self, inp=""):
		print("CMD_MODE() START, inp: {}".format(inp))
		#
		ret = 2 # 2=repeat You(), 5=Start Build
		a = inp.split(" ")
		if len(a) < 2:
			# Show current mode
			mode = self.handle.Options.get('MODE', 'build')
			print("Current mode: {}".format(mode))
			return ret
		#
		new_mode = a[1].strip().lower()
		if new_mode not in ['plan', 'build']:
			print("Invalid mode: {}. Use 'plan' or 'build'".format(new_mode))
			return ret
		#
		if new_mode == 'plan':
			ret = self._mode_switch_plan(ret)
		else:  # build
			ret = self._mode_switch_build(ret)
		#
		# Persist mode to state
		self.handle._write_state({'mode': new_mode})
		#
		#--
		# Update System message with new mode!
		# Find last system message in history and replace it; append if none.
		# Ollama support multiple system prompts in one chat history!
		#--
		self.handle._replace_system_prompt(self.handle.hPP._get_mode_instructions(self.handle.Options['MODE']))
		#--
		# Optionally inject plan-mode tool training
		if new_mode == 'plan' and self.handle.Options.get('TOOL_TRAINING_PLAN', True):
			self.handle.Response('user', {'content':
				"[Tool Training — Plan Mode]\n"
				"You are now in PLAN mode. List all tools available to you in plan mode "
				"and demonstrate at least 3 of them with complete XML examples showing "
				"the required parameters. "
				"Do NOT use GetTip — use TreeView, ReadFile, and WriteFile instead."})
			self.handle._train_skip_you = True
		# Depend if plan contain tasks then StartBuild() || <startBuild/> and auto continue to AI
		return ret

	def _mode_switch_plan(self, ret):
		# Switch to plan mode (read-only)
		if self.handle.Options['MODE']=='plan':
			print("ERROR: Already in plan mode. Skip.")
			return ret
		self.handle.Options['MODE'] = 'plan'
		print("Mode changed to PLAN. You are now in read-only mode.")
		return ret

	def _mode_switch_build(self, ret):
		# Switch to build mode — auto-load latest plan if a draft exists
		if self.handle.Options['MODE']=='build':
			print("ERROR: Already in build mode. Skip.")
			return ret
		self.handle.Options['MODE'] = 'build'
		print("Mode changed to BUILD. You can now make changes.")
		# Check if plan has tasks - if yes, return 5 to trigger startBuild
		from src.PlanManager import PlanBase, Plan
		if not PlanBase.draft:
			# Auto-load latest plan from disk
			plans_dir = self.handle.Options.get('plans_path', 'plans')
			import os
			if os.path.isdir(plans_dir):
				json_files = sorted(
					[f for f in os.listdir(plans_dir) if f.endswith('.json')],
					key=lambda f: os.path.getmtime(os.path.join(plans_dir, f)),
					reverse=True)
				if json_files:
					latest_id = json_files[0].replace('.json', '')
					plan = Plan.load(latest_id, plans_dir)
					if plan:
						PlanBase.draft = plan
						print("Loaded latest plan from disk: {}".format(plan.title))
		if PlanBase.draft and len(PlanBase.draft.tasks) > 0:
			ret = 5  # startBuild signal
			print("Plan has {} tasks. Starting build...".format(len(PlanBase.draft.tasks)))
		else:
			print("No active plan. Use createPlan first.")
		return ret

	def CMD_BACKEND(self, inp=""):
		"""Switch LLM backend mid-session: ollama | vllm."""
		a = inp.strip().split()
		current = self.handle.Options.get('AI_BACKEND', 'ollama')
		if len(a) < 2:
			print("Current backend: {}".format(current))
			print("Usage: !BACKEND <ollama|vllm>")
			print("Tip: vLLM uses the OpenAI-compatible API at VLLM_HOST (config.py)")
			return 2
		new_backend = a[1].strip().lower()
		if new_backend not in ('ollama', 'vllm'):
			print("Invalid backend '{}' — must be 'ollama' or 'vllm'".format(new_backend))
			return 2
		if new_backend == current:
			print("Already using '{}'".format(current))
			return 2
		self.handle.Options['AI_BACKEND'] = new_backend
		# Force backend re-creation on next use
		self.handle.hBackend = None
		backend = self.handle._get_backend()
		print("Backend changed: '{}' -> '{}'".format(current, new_backend))
		# Validate connectivity / list a few models
		try:
			models = backend.list_models()
			print("  {} model(s) available".format(len(models)))
			if models:
				print("  first 5: {}".format(", ".join(models[:5])))
		except Exception as e:
			print("  Warning: could not contact {} backend: {}".format(new_backend, e))
		return 2

	def CMD_MODEL(self, inp=""):
		"""Switch AI model mid-session."""
		a = inp.strip().split()
		if len(a) < 2:
			print("Current model: {}".format(self.handle.Options.get('AI_MODEL', '(not set)')))
			print("Usage: !MODEL <model_name>")
			print("Tip: use !MODELS to see available models")
			return 2
		new_model = a[1].strip()
		old = self.handle.Options.get('AI_MODEL', '')
		if new_model == old:
			print("Already using '{}'".format(old))
			return 2
		self.handle.Options['AI_MODEL'] = new_model
		# Track in used_models
		models = self.handle.Options.get('used_models', [])
		if new_model not in models:
			models.append(new_model)
			self.handle._save_used_models(models)
		print("Model changed: '{}' -> '{}'".format(old, new_model))
		# Apply model registry
		from src.ModelRegistry import apply as apply_registry
		reg_changes = apply_registry(self.handle.Options, new_model)
		if reg_changes:
			for c in reg_changes:
				print("  {}".format(c))
		# Stop any loaded model that differs from the new one (free GPU memory)
		# Only applies to the ollama backend — vLLM manages GPU memory itself.
		if not self.handle._get_backend().is_vllm:
			try:
				import subprocess
				r = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
				if r.returncode == 0:
					for line in r.stdout.strip().split('\n')[1:]:
						parts = line.split()
						if parts and parts[0] and parts[0] != new_model:
							subprocess.run(['ollama', 'stop', parts[0]], capture_output=True, timeout=10)
							print("  Freed memory: stopped {}".format(parts[0]))
			except Exception:
				pass
		return 2

	def CMD_STATS(self, inp):
		print("Stats            :")
		print("-----------------")
		print("history.msgs.len : {}".format( len(self.handle.hHM.msgs) ))
		print("row_id           : {}".format( self.handle.Options['AI_ROW_ID'] ))
		print("sess_id          : {}_{}".format( self.handle.Options['AI_SESS_PREFIX'], self.handle.Options['AI_SESS_ID'] ))
		print("history          : {} / {}".format( self.handle.Options['AI_FILE_HISTORY'], self.handle.hHM.history ))
		_fname = self.handle.Options.get('AI_FILE_HISTORY', '')
		if _fname:
			_key = _fname[:-4] if _fname.endswith('.dbk') else _fname
			_alias = self.handle.hHM.get_name(_key)
			if _alias:
				print("  display name   : {}".format(_alias))
		print("user.history     : {}".format( self.handle.Options['AI_USER_HISTORY'] ))
		#
		print("available history: {}".format( len(self.handle.hHM.available) ))
		print("available tools  : {}".format( len(self.handle.hTC.available) ))
		print("imported tools   : {}".format( len(self.handle.hTC.prepared) ))
		print("-----------------")
		print("Tokens          :")
		print("  last_prompt    : {}".format( self.handle.Options['NUM_LAST_PROMPT_TOKENS'] ))
		print("  last_response  : {}".format( self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] ))
		print("  total_prompt   : {}".format( self.handle.Options['NUM_PROMPT_TOKENS'] ))
		print("  total_response : {}".format( self.handle.Options['NUM_RESPONSE_TOKENS'] ))
		print("  context_usage  :")
		_limit = self.handle.Options.get('AI_CONTEXT_LIMIT', 262144)
		_estimate = self.handle._estimate_tokens(self.handle.hHM.msgs) if hasattr(self.handle, '_estimate_tokens') else 0
		_pct = _estimate / _limit * 100 if _limit else 0
		print("    estimate / limit: {}/{} ({:.1f}%)".format(_estimate, _limit, _pct))
		print("-----------------")
		print("Options         :")
		print("-----------------")
		for k in self.handle.Options:
			print("{} => {}".format( k, self._mask_secret(k, self.handle.Options[ k ]) ))
		return 2 # as continue
	#
	def CMD_OLLAMA_LIST(self, inp=""):
		"""List available models on the active backend, with previously used ones at top."""
		try:
			backend = self.handle._get_backend()
			used = self.handle.Options.get('used_models', [])
			res = backend.list_models()

			if used:
				print("Previously used models:")
				for m in used:
					print("  ★ {}".format(m))
				print("")

			print("All available {} models:".format(backend.name))
			all_names = list(res)
			for name in all_names:
				if name not in used:
					print("  {}".format(name))
		except Exception as e:
			print("Error listing models: {}".format(e))
		return 2

	@staticmethod
	def _mask_secret(key, val):
		"""Mask values of secret-looking keys (API keys, tokens) for display."""
		if isinstance(val, str) and val and any(s in key.upper() for s in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD')):
			return val[:4] + '...' if len(val) > 4 else '***'
		return val
	#

#--

def _parse_set_value(raw):
	# Parse a raw !SET value string into bool/None/int/float/json/string
	val = raw
	if raw.lower() == 'true':
		val = True
	elif raw.lower() == 'false':
		val = False
	elif raw.lower() == 'none' or raw.lower() == 'null':
		val = None
	else:
		try:
			val = int(raw)
		except ValueError:
			try:
				val = float(raw)
			except ValueError:
				try:
					val = json.loads(raw)
				except (json.JSONDecodeError, ValueError):
					val = raw
	return val
