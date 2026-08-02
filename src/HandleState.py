import json, os
from src.functions import fread, fwrite
from src.PlanManager import PlanBase, Plan
from src.PlanSaver import PlanSaver
#
class HandleState():

	#

	def _load_continue_session(self):
		working_dir = self.Options.get('working_dir')
		framework_dir = self.Options.get('path', '').rstrip('/')
		if not working_dir or working_dir == framework_dir:
			working_dir = None

		# Load all persisted state from state.aiia
		state = self._read_state()

		self._restore_mode(state)
		self._restore_persona(state)
		self._restore_backend(state)
		self._restore_model(state)
		self._restore_used_models(state)
		self._restore_auto_continue(state)
		self._restore_user_agent(state)
		self._restore_tool_lists(state)
		self._ensure_num_predict()
		self._load_plan_md(working_dir, framework_dir)
		self._load_history_md(working_dir, state)

	def _restore_mode(self, state):
		"""Restore MODE from state.aiia if it holds a valid value."""
		saved_mode = state.get('mode', '')
		if saved_mode in ('plan', 'build'):
			self.Options['MODE'] = saved_mode
			self.hLG.echo("Restored MODE: {}".format(saved_mode),
				{'color': True, 'colorValue': 'green'})

	def _restore_persona(self, state):
		"""Restore the persona class + override flag from state.aiia."""
		saved_persona = state.get('persona', '')
		if saved_persona:
			self.Options['INSTRUCT_CLASS'] = saved_persona
			self.Options['INSTRUCT_CLASS_OVERRIDE'] = True
			self.hLG.echo("Restored persona: {}".format(saved_persona),
				{'color': True, 'colorValue': 'green'})

	def _restore_backend(self, state):
		"""Restore backend (before model, so the model lands on the right backend)."""
		saved_backend = state.get('backend', '')
		if saved_backend in ('ollama', 'vllm'):
			if saved_backend != self.Options.get('AI_BACKEND', 'ollama'):
				self.Options['AI_BACKEND'] = saved_backend
				self.hLG.echo("Restored backend: {}".format(saved_backend),
					{'color': True, 'colorValue': 'green'})

	def _restore_model(self, state):
		"""Restore the active model, applying the model registry when it changes."""
		saved_model = state.get('model', '')
		if saved_model:
			old = self.Options.get('AI_MODEL', '')
			self.Options['AI_MODEL'] = saved_model
			if saved_model != old:
				self.hLG.echo("Restored model: {}".format(saved_model),
					{'color': True, 'colorValue': 'green'})
				from src.ModelRegistry import apply as apply_registry
				_changes = apply_registry(self.Options, saved_model)
				if _changes:
					for _c in _changes:
						self.hLG.echo("  Model config: {}".format(_c),
							{'color': True, 'colorValue': 'cyan'})

	def _restore_used_models(self, state):
		"""Restore the used-models list, appending the current model if new."""
		used_models = state.get('used_models', [])
		current = self.Options.get('AI_MODEL', '')
		if current and current not in used_models:
			used_models.append(current)
			self._write_state({'used_models': used_models})
		self.Options['used_models'] = used_models

	def _restore_auto_continue(self, state):
		"""Restore the auto-continue task settings from state.aiia."""
		auto_continue = state.get('auto_continue')
		if auto_continue is not None:
			self.Options['AUTO_CONTINUE_TASKS'] = auto_continue
			self.Options['AUTO_CONTINUE_ALL_TASKS'] = auto_continue

	def _restore_user_agent(self, state):
		"""Restore the WWW user-agent string from state.aiia."""
		saved_ua = state.get('WWW_USER_AGENT')
		if saved_ua:
			self.Options['WWW_USER_AGENT'] = saved_ua
			self.hLG.echo("Restored user-agent: {}".format(saved_ua[:60]),
				{'color': True, 'colorValue': 'cyan'})

	def _restore_tool_lists(self, state):
		"""Restore tool allow/disallow lists from state.aiia."""
		saved_blocked = state.get('tool_blocked', [])
		saved_allowed = state.get('tool_allowed', [])
		if saved_blocked:
			self.Options['TOOL_BLOCKED'] = set(saved_blocked)
			self.hLG.echo("Restored tool blocked list: {} tool(s)".format(len(saved_blocked)),
				{'color': True, 'colorValue': 'cyan'})
		if saved_allowed:
			self.Options['TOOL_ALLOWED'] = set(saved_allowed)

	def _ensure_num_predict(self):
		"""Ensure num_predict is set for continued sessions (prevents truncation)."""
		if self.Options.get('NUM_PREDICT') is None:
			self.Options['NUM_PREDICT'] = 16384
			self.hLG.echo("Set NUM_PREDICT=16384 for continued session (use !SET NUM_PREDICT <value> to change)",
				{'color': True, 'colorValue': 'cyan'})

	def _load_plan_md(self, working_dir, framework_dir):
		"""Load the current plan from PLAN.md (via its JSON on disk)."""
		plan_data = PlanSaver.load_plan(working_dir, framework_dir)
		if plan_data and plan_data.get('id'):
			# Load the plan from JSON
			loaded_plan = Plan.load(plan_data['id'], self.Options.get('plans_path', 'plans'))
			if loaded_plan:
				PlanBase.draft = loaded_plan
				PlanBase.LoadAll(self.Options.get('plans_path', 'plans'))
				self.hLG.echo("Loaded plan: {} ({} tasks)".format(loaded_plan.title, len(loaded_plan.tasks)), {'color':True, 'colorValue':'green'})

	def _load_history_md(self, working_dir, state):
		"""Load session history from HISTORY.md, syncing token counts and
		injecting fresh persona instructions on mode mismatch."""
		if working_dir is None:
			return
		history_md = os.path.join(working_dir, 'HISTORY.md')
		total_prompt = total_response = 0
		last_prompt = last_response = 0
		if os.path.exists(history_md):
			self.hHM.Get(path=history_md)
			self.Options['CONTINUING'] = True
			self.Options['AI_FILE_LOAD_HISTORY'] = True
			self.hLG.echo("Loaded session history from {}".format(history_md), {'color':True, 'colorValue':'green'})
			# Sync AI_ROW_ID to last loaded row + 1
			if self.hHM.msgs:
				last_row = max((m.get('rowId', 0) for m in self.hHM.msgs), default=0)
				self.Options['AI_ROW_ID'] = last_row + 1
			# Recalculate token counts from loaded history
			for m in self.hHM.msgs:
				if m.get('role') == 'assistant':
					pt = m.get('prompt_tokens', 0)
					rt = m.get('response_tokens', 0)
					total_prompt += pt
					total_response += rt
					if pt or rt:
						last_prompt = pt
						last_response = rt
			self.Options['NUM_PROMPT_TOKENS'] = total_prompt
			self.Options['NUM_RESPONSE_TOKENS'] = total_response
			self.Options['NUM_LAST_PROMPT_TOKENS'] = last_prompt
			self.Options['NUM_LAST_RESPONSE_TOKENS'] = last_response
		# Fallback: if per-message scan found nothing, load from state
		if total_prompt == 0 and total_response == 0:
			state = self._read_state()
			for key in ('NUM_PROMPT_TOKENS', 'NUM_RESPONSE_TOKENS',
						'NUM_LAST_PROMPT_TOKENS', 'NUM_LAST_RESPONSE_TOKENS'):
				if key in state:
					self.Options[key] = state[key]

		# Check if loaded system messages match current mode instructions.
		# If mode changed (different persona or plan↔build), inject fresh
		# instructions so the model gets the correct behavior.
		# Runs whenever history was loaded (not just when token scan is empty).
		if self.hHM.msgs:
			current_mode = self.Options.get('MODE', 'plan')
			current_text = self.hPP._get_mode_instructions(current_mode)
			header = current_text.strip()[:80]
			mode_matches = any(
				header in m.get('content', '')
				for m in self.hHM.msgs if m.get('role') == 'system'
			)
			if not mode_matches:
				self.hLG.echo(
					"Mode mismatch detected — injecting fresh {} persona instructions".format(current_mode),
					{'color': True, 'colorValue': 'yellow'})
				self.Response('system', {'content': current_text})

	#

	def _read_state(self):
		"""Load full state dict from state.aiia, with migration from legacy files."""
		path = self.Options.get('AI_FILE_STATE')
		if path and os.path.exists(path):
			try:
				raw = fread(path)
				return json.loads(raw)
			except Exception as e:
				self.hLG.echo("Failed to read state: {} (will migrate)".format(e),
					{'color': True, 'colorValue': 'yellow'})
		# No state.aiia yet — migrate from legacy per-file .aiia files
		migrated = self._migrate_old_state()
		if migrated:
			self._write_state(migrated)
		return migrated

	#

	def _write_state(self, updates=None):
		"""Atomically write state.aiia, merging `updates` into existing state."""
		path = self.Options.get('AI_FILE_STATE')
		if not path:
			return
		state = {}
		if os.path.exists(path):
			try:
				raw = fread(path)
				state = json.loads(raw)
			except Exception:
				pass
		if updates:
			state.update(updates)
		try:
			tmp = path + '.tmp'
			fwrite(tmp, json.dumps(state), True)
			os.replace(tmp, path)
		except Exception as e:
			self.hLG.echo("Failed to write state: {}".format(e),
				{'color': True, 'colorValue': 'red'})

	#

	def _migrate_old_state(self):
		"""Import values from legacy per-file .aiia files into a single dict."""
		fw_dir = self.Options.get('path', '').rstrip('/')
		state = {}
		legacy = [
			('sess_id', '{}/sessid.aiia', lambda r: int(r.strip())),
			('mode', '{}/mode.aiia', lambda r: r.strip() if r.strip() in ('plan','build') else None),
			('model', '{}/model.aiia', lambda r: r.strip() or None),
			('persona', '{}/persona.aiia', lambda r: r.strip() or None),
			('used_models', '{}/used_models.aiia', lambda r: json.loads(r)),
		]
		token_keys = ['NUM_PROMPT_TOKENS', 'NUM_RESPONSE_TOKENS',
					  'NUM_LAST_PROMPT_TOKENS', 'NUM_LAST_RESPONSE_TOKENS']
		found = False
		for key, tmpl, parse in legacy:
			p = tmpl.format(fw_dir)
			if os.path.exists(p):
				try:
					raw = fread(p)
					val = parse(raw)
					if val is not None:
						state[key] = val
						found = True
				except Exception:
					pass
		# Migrate tokens.aiia (JSON file with separate keys)
		tokens_path = '{}/tokens.aiia'.format(fw_dir)
		if os.path.exists(tokens_path):
			try:
				tdata = json.loads(fread(tokens_path))
				for k in token_keys:
					if k in tdata:
						state[k] = tdata[k]
						found = True
			except Exception:
				pass
		if found:
			self.hLG.echo("Migrated legacy .aiia files to state.aiia",
				{'color': True, 'colorValue': 'cyan'})
		return state

	#

	def _save_used_models(self, models):
		"""Persist the used-models list to state.aiia."""
		self._write_state({'used_models': models})
