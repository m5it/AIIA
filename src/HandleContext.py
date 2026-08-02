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

	def _summarize_context(self, msgs, limit, threshold):
		"""Summarize older messages, keeping last 5 exchanges + all system prompts.
		Returns True if summarization was performed."""
		# Strip malformed entries (no `role` key) that slipped into history
		msgs = [m for m in msgs if isinstance(m, dict) and m.get('role')]
		if not msgs:
			return False
		# Collect indices to keep
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
		if not idx:
			return False

		build = []
		for i in idx:
			role = msgs[i]['role']
			content = msgs[i].get('content', '')
			build.append("[{}]: {}".format(role, content[:600]))
		to_summarize = "\n\n".join(build)

		prompt = (
			"Summarize the key facts, decisions, file states, and progress "
			"from this conversation concisely. Focus on:\n"
			"- What has been built or changed\n"
			"- What decisions were made\n"
			"- Current state of files and code\n"
			"- What remains to be done\n\n"
			"Keep the summary under 500 words.\n\n"
			"---\n" + to_summarize
		)

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
		except Exception as e:
			self.hLG.echo("Context summarization failed: {}".format(e),
				{'color': True, 'colorValue': 'red'})
			return False

		new_msgs = [msgs[i] for i in sorted(keep)]
		# Insert summary right after the last system prompt in new_msgs
		last_sys = sum(1 for m in new_msgs if m['role'] == 'system') - 1
		summary_msg = {
			'role': 'system',
			'content': "[Context summary: {}]".format(summary),
			'sessionId': self.Options['AI_SESS_ID'],
			'rowId': self.Options['AI_ROW_ID'] + 1,
			'timestamp': time.time(),
			'date': str(date.today()),
		}
		new_msgs.insert(last_sys + 1, summary_msg)

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

	def _auto_clear(self):
		"""Keep only system messages, clear everything else.  Resets counters."""
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
		self.hLG.echo("Context limit reached — auto-cleared chat history",
			{'color': True, 'colorValue': 'orange', 'debugOnly': False})

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
