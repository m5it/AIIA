import json, os, time
from datetime import date
from src.functions import fwrite
from src.PlanSaver import PlanSaver
#
class HandleContext():

	#

	def _estimate_tokens(self, msgs):
		"""Rough token estimate: ~4 chars per token on average.
		Image refs are counted as a small fixed cost (actual bytes only
		resolved transiently for the API call, not stored in history)."""
		total = 0
		for m in msgs:
			content = m.get('content', '')
			thinking = m.get('thinking', '')
			total += len(content) // 4
			total += len(thinking) // 4
			total += 8  # overhead per message (role label, newlines)
			# Lightweight image refs: count as small fixed overhead
			refs = m.get('image_refs', [])
			if refs:
				total += 50 * len(refs)  # ~50 "tokens" per image ref
			# Direct base64 images (legacy/fallback — shouldn't appear in stored history)
			for img_b64 in m.get('images', []):
				total += len(img_b64) // 3
		return total

	#

	def _rewrite_history(self, msgs):
		"""Rewrite the on-disk history files to match in-memory state."""
		main_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)

		framework_dir = self.Options.get('path', '').rstrip('/')
		proj_dir = self.Options.get('working_dir')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, msgs)

	#

	def _archive_history(self, suffix):
		"""Copy current .dbk to an archive file before destructive operations.
		Archive is saved as {prefix}_{sid}.{suffix}.{timestamp}.dbk in the history dir.
		Returns the archive filename (or None if nothing was archived)."""
		main_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), self.Options['AI_FILE_HISTORY'])
		if not os.path.exists(main_path):
			return None
		try:
			with open(main_path) as f:
				lines = f.readlines()
			# Only archive if there's more than just a few messages
			if len(lines) <= 3:
				return None
		except Exception:
			return None

		ts = int(time.time())
		_prefix = self.Options.get('AI_SESS_PREFIX', '')
		sid = self.Options['AI_SESS_ID']
		archive_name = "{}_{}.{}.{}.dbk".format(_prefix, sid, suffix, ts)
		archive_path = "{}/{}".format("{}/history".format(self.Options.get('path', '')), archive_name)
		try:
			fwrite(archive_path, "".join(lines), True)
			self.hLG.echo("Archived history to {}".format(archive_name),
				{'color': True, 'colorValue': 'cyan'})
			return archive_name
		except Exception as e:
			self.hLG.echo("Failed to archive history: {}".format(e),
				{'color': True, 'colorValue': 'red'})
			return None

	#

	def _pb_anchor_indices(self, msgs):
		"""Return the indices of task-instruction anchors in history order:
		the first user message, then every injected plan/build instruction
		(planDone → 'Plan is ready!...' system msg, startBuild/mode-switch
		system msg, and each '<nextTask>' user msg). Anchors are detected by
		content marker so they survive pruning (indices shift) and restarts."""
		anchors = []
		for idx, m in enumerate(msgs):
			if not isinstance(m, dict):
				continue
			role = m.get('role')
			content = m.get('content', '')
			if role == 'user' and not anchors:
				anchors.append(idx)
			elif role == 'system' and content.startswith('Plan is ready! Starting first task.'):
				anchors.append(idx)
			elif role == 'system' and content.startswith('Mode changed to BUILD.'):
				anchors.append(idx)
			elif role == 'user' and content.startswith('<nextTask>\n\n'):
				anchors.append(idx)
		return anchors

	#

	def _pb_autoclean(self):
		"""AI_PLANBUILD_AUTOCLEAN: prune finished plan/build task work from the
		model context with a sliding window between task-instruction anchors.
		Keeps all system messages and the planning phase (first user message
		through the 'Plan is ready!' and 'Mode changed to BUILD' anchors) so
		the model remembers the plan it created; only drops the OLDEST uncleaned
		block of non-system messages strictly between anchors that come AFTER the
		'Mode changed to BUILD' anchor (i.e., the work of each completed task in
		order). Only HISTORY.md is rewritten — the raw session .dbk in
		root/history/ keeps all rows, and '-c' continue restores the cleaned
		view. Returns True if a clean was performed."""
		wait = int(self.Options.get('AI_PLANBUILD_WAIT', 5) or 1)
		wait = max(wait, 1)
		msgs = getattr(self.hHM, 'msgs', None)
		if not msgs:
			return False
		anchors = self._pb_anchor_indices(msgs)
		if len(anchors) < 2:
			return False
		# Locate the 'Mode changed to BUILD' anchor: preserve everything before
		# it (the planning phase), and only clean blocks of finished task work.
		start_idx = None
		for i, idx in enumerate(anchors):
			m = msgs[idx]
			if m.get('role') == 'system' and m.get('content', '').startswith('Mode changed to BUILD.'):
				start_idx = i
				break
		if start_idx is None:
			return False
		for i in range(start_idx, len(anchors) - 1):
			previous, current = anchors[i], anchors[i+1]
			if current - previous < 2:
				continue
			removed = 0
			new_msgs = []
			for idx, m in enumerate(msgs):
				if previous < idx < current and m.get('role') != 'system':
					removed += 1
					continue
				new_msgs.append(m)
			if removed == 0:
				continue
			self.hHM.msgs = new_msgs
			framework_dir = self.Options.get('path', '').rstrip('/')
			proj_dir = self.Options.get('working_dir')
			if proj_dir and proj_dir != framework_dir:
				proj_history = os.path.join(proj_dir, 'HISTORY.md')
				PlanSaver.rebuild_history(proj_history, new_msgs)
			sync = getattr(self, '_sync_row_id_and_tokens', None)
			if sync:
				sync()
			self.hLG.echo("Plan/build autoclean: removed {} message(s) before task anchor".format(removed),
				{'color': True, 'colorValue': 'cyan', 'debugOnly': False})
			return True
		return False

	#

	def _summarize_context(self, msgs, limit, threshold):
		"""Summarize older messages, keeping last 5 exchanges + all system prompts.
		Returns True if summarization was performed."""
		# Strip malformed entries and pick the older messages to summarize
		msgs, idx = self._collect_drop_indices(msgs)
		if not idx:
			return False
		prompt = self._build_summary_prompt(msgs, idx)
		summary = self._request_summary(prompt)
		if summary is None:
			return False
		keep = set(range(len(msgs))) - set(idx)
		new_msgs = self._insert_summary(msgs, keep, summary)
		return self._finalize_summarize(new_msgs, idx, summary)

	#

	def _collect_drop_indices(self, msgs):
		"""Strip malformed entries (no `role` key) that slipped into history.
		Collect indices of the older messages to drop, keeping the last 5
		exchanges + all system prompts. Returns (msgs, idx) where idx is the
		sorted list of indices to summarize away."""
		msgs = [m for m in msgs if isinstance(m, dict) and m.get('role')]
		keep = set()
		exchange_count = 0
		for i in range(len(msgs) - 1, -1, -1):
			role = msgs[i]['role']
			if role == 'system':
				keep.add(i)
			elif exchange_count < 5 and role in ('user', 'assistant'):
				keep.add(i)
				if role == 'user':
					exchange_count += 1
		idx = sorted(i for i in range(len(msgs)) if i not in keep)
		return msgs, idx

	#

	def _build_summary_prompt(self, msgs, idx):
		"""Build the summarization prompt from the older messages."""
		build = []
		for i in idx:
			role = msgs[i]['role']
			content = msgs[i].get('content', '')
			build.append("[{}]: {}".format(role, content[:600]))
		to_summarize = "\n\n".join(build)
		return (
			"Summarize the key facts, decisions, file states, and progress "
			"from this conversation concisely. Focus on:\n"
			"- What has been built or changed\n"
			"- What decisions were made\n"
			"- Current state of files and code\n"
			"- What remains to be done\n\n"
			"Keep the summary under 500 words.\n\n"
			"---\n" + to_summarize
		)

	#

	def _request_summary(self, prompt):
		"""Ask the backend to summarize. Returns the summary string, or None
		on failure."""
		try:
			res = self._get_backend().chat(
				model=self.Options['AI_MODEL'],
				messages=[{'role': 'user', 'content': prompt}],
				options={'num_predict': 1024},
				stream=False,
				think=False,
			)
			summary = res.message.content.strip()
			if len(summary) > 3000:
				summary = summary[:3000] + "…"
			return summary
		except Exception as e:
			self.hLG.echo("Context summarization failed: {}".format(e),
				{'color': True, 'colorValue': 'red'})
			return None

	#

	def _insert_summary(self, msgs, keep, summary):
		"""Rebuild history: keep the older messages, insert the summary right
		after the standing mode-instructions block (before the recent exchanges).

		The summary is a concise system-level recap only.  Active-plan details
		and file-cache buffers are kept in the surviving recent exchanges, so
		we avoid duplicating them into a single large system message that would
		defeat the purpose of summarization.

		If one or more `[Context summary:]` system messages already exist, the
		new summary is merged into a single summary row (capped, newest kept,
		legacy rows collapsed) instead of adding yet another row — so repeated
		summarizes don't pile summary messages at the head of history."""
		from src.HandleChat import _merge_summary_content
		new_msgs = [msgs[i] for i in sorted(keep)]
		cap = self.Options.get('CONTEXT_SUMMARY_CAP', 5000)
		# Collect existing summary texts in chronological (oldest-first) order.
		chunks = []
		has_existing = False
		for m in new_msgs:
			if isinstance(m, dict) and m.get('role') == 'system':
				c = m.get('content', '') or ''
				if c.startswith('[Context summary:'):
					chunks.append(c[len('[Context summary:'):].strip())
					has_existing = True
		chunks.append(summary)  # newest last
		merged = ''
		for chunk in chunks:
			merged = _merge_summary_content(merged, chunk, cap)
		summary_msg = {
			'role': 'system',
			'content': merged,
			'sessionId': self.Options['AI_SESS_ID'],
			'rowId': self.Options['AI_ROW_ID'] + 1,
			'timestamp': time.time(),
			'date': str(date.today()),
		}
		# Drop old summary rows; keep everything else in original order.
		kept = [
			m for m in new_msgs
			if not (isinstance(m, dict) and m.get('role') == 'system'
					and (m.get('content', '') or '').startswith('[Context summary:'))
		]
		# Place the summary right after the standing instructions block (the
		# contiguous run of system messages at the head of the kept history),
		# before the recent exchanges — not hoisted above unrelated system rows.
		insert_idx = 0
		for i, m in enumerate(kept):
			if isinstance(m, dict) and m.get('role') == 'system':
				insert_idx = i + 1
			else:
				break
		kept.insert(insert_idx, summary_msg)
		return kept

	#

	def _finalize_summarize(self, new_msgs, idx, summary):
		"""Archive raw history, swap in the summarized history, and report."""
		# Archive raw history before rewriting
		self._archive_history('summarized')
		self.hHM.msgs = new_msgs
		self._rewrite_history(new_msgs)
		self.hLG.echo(
			"Context summarized: {} messages replaced with summary ({} chars)".format(
				len(idx), len(summary)),
			{'color': True, 'colorValue': 'green'})
		return True

	#

	def _active_plan_text(self):
		"""Render the active plan to a text block, or '' when none is available.
		Uses PlanBase.draft when set; otherwise falls back to the most recently
		saved plan on disk (without mutating PlanBase.draft)."""
		try:
			from src.PlanManager import PlanBase, Plan
		except Exception:
			return ""
		plan = getattr(PlanBase, 'draft', None)
		if plan is None:
			try:
				plans_dir = self.Options.get('plans_path', 'plans')
				if os.path.isdir(plans_dir):
					json_files = sorted(
						[f for f in os.listdir(plans_dir) if f.endswith('.json')],
						key=lambda f: os.path.getmtime(os.path.join(plans_dir, f)),
						reverse=True)
					if json_files:
						plan = Plan.load(json_files[0].replace('.json', ''), plans_dir)
			except Exception:
				plan = None
		if plan is None:
			return ""
		return PlanSaver.plan_to_text(plan)

	def _build_continue_prompt(self, base="Continue with the task."):
		"""Build a user-message prompt for post-clear/post-summarize continuation.

		Includes the active mode, the active plan and cached file buffers so the
		model can pick up exactly where it left off, without inflating the
		system-prompt area."""
		mode = self.Options.get('MODE', 'plan')
		parts = ["Current mode: {}.\n".format(mode.upper())]
		parts.append(base)
		plan_text = self._active_plan_text()
		if plan_text:
			parts.append("\n\n[ACTIVE PLAN]\n" + plan_text.rstrip() + "\n")
		cache_section = self._file_cache_section()
		if cache_section:
			parts.append("\n\n" + cache_section)
		return "".join(parts)

	def _auto_clear(self):
		"""Keep only system messages, clear everything else.  Resets counters.

		This method is intentionally pure: it does NOT inject any new system,
		user, or tool messages.  Callers are responsible for adding the next
		appropriate turn so the conversation role alternation is preserved."""
		msg_count = len(self.hHM.msgs)
		archive_name = self._archive_history('cleared')
		if archive_name:
			self._save_clear_tip(archive_name, msg_count)
		system_msgs = [m for m in self.hHM.msgs if isinstance(m, dict) and m.get('role') == 'system']
		self.hHM.msgs = system_msgs[:]
		self._rewrite_history(system_msgs)
		self.Options['AI_ROW_ID'] = 0
		self.Options['NUM_PROMPT_TOKENS'] = 0
		self.Options['NUM_RESPONSE_TOKENS'] = 0
		self.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		self._auto_clear_this_turn = True
		self.hLG.echo("Context limit reached — auto-cleared chat history",
			{'color': True, 'colorValue': 'orange', 'debugOnly': False})

	#

	def _file_cache_section(self):
		"""Build a '[CACHED FILE BUFFERS]' block from self.file_buffer_cache, or
		'' when disabled/empty.  Per-file content is capped at
		TOOL_FILE_CACHE_REINJECT_MAX chars; once the block reaches
		TOOL_FILE_CACHE_REINJECT_TOTAL chars, the remaining files are listed as
		one-line manifest entries (path + size) so the model can ReadFile them."""
		if not self.Options.get('TOOL_FILE_CACHE_REINJECT', True):
			return ''
		cache = getattr(self, 'file_buffer_cache', None)
		if not cache:
			return ''
		per_file = int(self.Options.get('TOOL_FILE_CACHE_REINJECT_MAX', 5000))
		total = int(self.Options.get('TOOL_FILE_CACHE_REINJECT_TOTAL', 30000))
		out = []
		used = 0
		items = list(cache.items())
		for i, (fileName, content) in enumerate(items):
			header = "### {} ({} chars)".format(fileName, len(content))
			trunc = len(content) > per_file
			body = content[:per_file] if trunc else content
			block_size = len(header) + len(body) + 2
			if used + block_size > total:
				for name, cnt in items[i:]:
					out.append("- {} ({} chars)".format(name, len(cnt)))
				break
			out.append(header)
			out.append(body)
			if trunc:
				out.append("... truncated ({} chars total, use <ReadFile>)".format(len(content)))
			used += block_size
		return "\n".join(["[CACHED FILE BUFFERS]"] + out)

	#

	def _show_context_usage(self, label=""):
		"""Print context usage: estimate / limit (percent%)."""
		limit = self.Options.get('AI_CONTEXT_LIMIT', 262144)
		threshold = self.Options.get('AI_CLEAR_THRESHOLD', 0.8)
		msgs = self.hHM.msgs
		if not msgs:
			return
		estimate = self._estimate_tokens(msgs)
		pct = estimate / limit * 100 if limit else 0
		max_allowed = int(limit * threshold)
		if pct < 70:
			color = 'green'
		elif pct < threshold * 100:
			color = 'yellow'
		else:
			color = 'red'
		self.hLG.echo(
			"{}[Context: {}/{} ({:.1f}%)]".format(
				"[{}] ".format(label) if label else "",
				estimate, limit, pct),
			{'color': True, 'colorValue': color, 'debugOnly': False})

	#

	def _manage_context(self):
		"""Check estimated token count against limit.  Summarize first, clear as
		fallback.  Called at the start of AI() before any model request."""
		# Drop expired transient read results first — frees context before the
		# next model call and can prevent summarization/auto-clear entirely.
		self._sweep_transient_rows()
		#
		# Prevent a cascade: once we auto-cleared this turn, trust the remaining
		# system messages + the user message we injected below.  Re-clearing
		# would wipe the user turn and produce assistant-after-system sequences.
		if getattr(self, '_auto_clear_this_turn', False):
			return

		limit = self.Options.get('AI_CONTEXT_LIMIT', 262144)
		threshold = self.Options.get('AI_CLEAR_THRESHOLD', 0.8)
		max_allowed = int(limit * threshold)

		msgs = self.hHM.msgs
		if not msgs:
			return

		estimate = self._estimate_tokens(msgs)
		if estimate <= max_allowed:
			return

		self.hLG.echo(
			"Context estimate {} exceeds limit {} (threshold {}), managing…".format(
				estimate, limit, threshold),
			{'color': True, 'colorValue': 'yellow'})

		if self._summarize_context(msgs, limit, threshold):
			# Re-check after summarization
			if self._estimate_tokens(self.hHM.msgs) <= max_allowed:
				return

		self._auto_clear()
		# Preserve the user→assistant turn order by inserting the continuation
		# prompt as a user message after the clear.
		self.Response('user', {'content': self._build_continue_prompt()})

	#

	def _sweep_transient_rows(self):
		"""Decrement the 'transient' step counter on history rows and remove the
		rows that reached zero (their content has been consumed).  Called before
		every model request so transient read results free context automatically."""
		msgs = getattr(self.hHM, 'msgs', None)
		if not msgs:
			return
		remove = []
		for i, m in enumerate(msgs):
			steps = m.get('transient')
			if steps is None or steps is False or steps == 0:
				continue
			try:
				steps = int(steps)
			except (ValueError, TypeError):
				m.pop('transient', None)
				continue
			if steps > 1:
				m['transient'] = steps - 1
			else:
				remove.append(i)
		if remove:
			for i in reversed(remove):
				del msgs[i]
			self._rewrite_history(msgs)
			self.hLG.echo("Transient results removed ({} row(s))".format(len(remove)),
				{'color': True, 'colorValue': 'green', 'debugOnly': False})
