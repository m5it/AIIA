#--
# class CommandsSession — session & history commands
import os, json, zlib, time
from datetime import datetime
from src.functions import fwrite

_REHEAT_MSG = (
	"[Tool Reheat Session]\n"
	"Refresh your knowledge of this environment:\n"
	"1) Call <listTools> to reload all available tools and their parameters.\n"
	"2) Use <GetTip> or <ReinsertTip> to reload your important tips "
	"(instruction tips, tool reference tips, and any others you use).\n"
	"3) Demonstrate at least 2 tools with complete XML examples to confirm."
)

_SUMMARIZE_MSG = (
	"[Context Summarized]\n"
	"The chat history was summarized to free context. Recent rows and any standing "
	"system instructions were kept.\n"
	"Rebuild your working knowledge of this environment:\n"
	"1) Call <listTools> to reload all available tools and their parameters.\n"
	"2) Retrieve your core instructions and any tips you rely on with <GetTip>, "
	"e.g. <GetTip><title>instruct_developer</title></GetTip>, "
	"and reload them via <ReinsertTip>.\n"
	"3) Continue the current task using the tools."
)

class CommandsSession():
	#
	def CMD_NEW_SESSION(self, inp):
		# Clear in-memory history
		self.handle.hHM.msgs = []
		# Clear main history file on disk
		history_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(history_path)
		except Exception:
			pass
		# Clear project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			try:
				os.remove(proj_history)
			except Exception:
				pass
		# Reset counters
		self.handle.Options['AI_ROW_ID'] = 0
		self.handle.Options['NUM_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_RESPONSE_TOKENS'] = 0
		self.handle.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		# Reset tools
		self.handle.Options['current_tools'] = []
		self.handle.Options['handle_tools'] = {}
		self.handle.hTC.selected = []
		self.handle.hTC.prepared = []
		# Clear plan state
		from src.PlanManager import PlanBase
		PlanBase.draft = None
		PlanBase.done = {}
		# Reset draft response
		self.handle.Options['DRAFT_CONTENT'] = None
		self.handle.Options['DRAFT_RESPONSE'] = None
		# Reset continuation flags
		self.handle.Options['CONTINUING'] = False
		self.handle.Options['AI_FILE_LOAD_HISTORY'] = False
		# Clear caches and consumed tips
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		self.handle._pb_clean_counter = 0
		return 6
	#
	def CMD_CLEAR(self, inp):
		from src.PlanSaver import PlanSaver
		# Archive raw history before clearing — preserves training data
		msg_count = len(self.handle.hHM.msgs)
		archive_name = self.handle._archive_history('cleared')
		if archive_name:
			self.handle._save_clear_tip(archive_name, msg_count)
		# Keep system message(s), clear everything else
		system_msgs = [m for m in self.handle.hHM.msgs if m['role'] == 'system']
		self.handle.hHM.msgs = system_msgs[:]
		# Clear main history file on disk and rewrite system msgs
		main_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in system_msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rewrite project HISTORY.md with system msgs only
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, system_msgs)
		# Reset row ID and tokens
		self.handle.Options['AI_ROW_ID'] = 0
		self.handle.Options['NUM_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_RESPONSE_TOKENS'] = 0
		self.handle.Options['NUM_LAST_PROMPT_TOKENS'] = 0
		self.handle.Options['NUM_LAST_RESPONSE_TOKENS'] = 0
		print("Chat history cleared. System prompt preserved.")
		return 2
	#
	def CMD_REMOVE(self, inp):
		from src.PlanSaver import PlanSaver
		a = inp.strip().split()
		if len(a) < 2 or len(a) > 3:
			print("Usage: !RH <row_num> | !RH <from_row> <to_row>")
			return 2
		try:
			nums = [int(x) for x in a[1:]]
		except ValueError:
			print("Row numbers must be integers.")
			return 2
		if len(nums) == 1:
			from_row = to_row = nums[0]
		else:
			from_row, to_row = nums
			if from_row > to_row:
				from_row, to_row = to_row, from_row
		msgs = self.handle.hHM.msgs
		if from_row < 0 or to_row >= len(msgs):
			print("Rows {}-{} out of range. History has {} rows.".format(from_row, to_row, len(msgs)))
			return 2
		removed = msgs[from_row:to_row + 1]
		del msgs[from_row:to_row + 1]
		if len(removed) == 1:
			print("Removed row {}: [{}] {}".format(from_row, removed[0].get('role','?'), removed[0].get('content','')[:80]))
		else:
			roles = {}
			for m in removed:
				roles[m.get('role','?')] = roles.get(m.get('role','?'), 0) + 1
			parts = ', '.join("{} {}".format(n, r) for r, n in sorted(roles.items()))
			print("Removed rows {}-{} ({} rows: {}).".format(from_row, to_row, len(removed), parts))
		# Rebuild main history file on disk
		main_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rebuild project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, msgs)
		return 2
	#
	def CMD_MOVE_HISTORY(self, inp=""):
		"""!MH <from_row> <to_row> — move a chat history row to a new position.
		Row numbers are 0-indexed and match the output of !PH / !SH."""
		from src.PlanSaver import PlanSaver
		a = inp.strip().split()
		if len(a) != 3:
			print("Usage: !MH <from_row> <to_row>")
			return 2
		try:
			from_row = int(a[1])
			to_row = int(a[2])
		except ValueError:
			print("Row numbers must be integers.")
			return 2
		msgs = self.handle.hHM.msgs
		if from_row < 0 or from_row >= len(msgs) or to_row < 0 or to_row >= len(msgs):
			print("Rows {}-{} out of range. History has {} rows (0-{}).".format(from_row, to_row, len(msgs), len(msgs) - 1))
			return 2
		if from_row == to_row:
			print("Row {} is already at position {}.".format(from_row, to_row))
			return 2
		moved = msgs.pop(from_row)
		msgs.insert(to_row, moved)
		role = moved.get('role', '?')
		content = (moved.get('content', '') or '')[:80]
		print("Moved row {} to position {} [{}] {}".format(from_row, to_row, role, content))
		# Rebuild main history file on disk
		main_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rebuild project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, msgs)
		return 2
	#
	def CMD_SAVE_HISTORY(self, inp=""):
		"""!SAVE_HISTORY [filename] — save current chat history as a reloadable
		.dbk-style file (one JSON msg per line, like history/*.dbk) in the
		history/ folder and the framework root. Default filename uses the
		session prefix so it appears in !AH / the history chooser."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history to save.")
			return 2
		a = inp.strip().split()
		if len(a) > 2:
			print("Usage: !SAVE_HISTORY [filename]")
			return 2
		if len(a) == 2:
			filename = a[1]
			if not os.path.splitext(filename)[1]:
				filename = "{}.dbk".format(filename)
		else:
			_prefix = self.handle.Options.get('AI_SESS_PREFIX', '')
			sid = self.handle.Options.get('AI_SESS_ID', 0)
			filename = "{}_{}.save.{}.dbk".format(_prefix, sid, int(time.time()))
		if '/' in filename or '\\' in filename or filename in ('.', '..'):
			print("Filename must be a simple name (no path separators).")
			return 2
		# Never overwrite the active session history file
		active = self.handle.Options.get('AI_FILE_HISTORY', '')
		if filename == active:
			filename = "save_{}".format(filename)
		# Write main copy into history/ dir
		history_dir = "{}/history".format(self.handle.Options.get('path', '').rstrip('/'))
		main_path = os.path.join(history_dir, filename)
		self._write_history_lines(main_path, msgs)
		# Second copy in the framework root
		root_path = os.path.join(self.handle.Options.get('path', '').rstrip('/'), filename)
		self._write_history_lines(root_path, msgs)
		print("Saved history to {} and {}".format(main_path, root_path))
		return 2
	#
	@staticmethod
	def _write_history_lines(path, msgs):
		"""Write messages as plain JSON-lines (one msg per line) — same layout
		as history/*.dbk so HistoryManager.Get() can reload them."""
		import os as _os
		dir_name = _os.path.dirname(path)
		if dir_name:
			try:
				_os.makedirs(dir_name, exist_ok=True)
			except Exception:
				pass
		try:
			_os.remove(path)
		except Exception:
			pass
		for m in msgs:
			fwrite(path, "{}\n".format(json.dumps(m)), False)
	#
	#
	def CMD_SUMMARIZE(self, inp=""):
		"""!SUMMARIZE — summarize older chat history, keep the most recent rows
		(controlled by SUMMARIZE_LEAVE), then warm the model back up via a single
		user message. SUMMARIZE_LEAVE=0 keeps current behavior: clear everything
		except system messages. SUMMARIZE_LEAVE=N keeps the last N rows of history
		and summarizes the rest. The active plan and cached file buffers are
		appended to the user message so they survive the summary."""
		leave = int(self.handle.Options.get('SUMMARIZE_LEAVE', 0))
		if leave > 0:
			self.handle.hLG.echo("Summarizing — keeping last {} rows...".format(leave),
				{'color':True,'colorValue':'orange','debugOnly':False})
			self.handle._summarize_context(self.handle.hHM.msgs, 0, 0)
		else:
			self.handle.hLG.echo("Summarizing — clearing history, keeping system messages...",
				{'color':True,'colorValue':'orange','debugOnly':False})
			self.handle._auto_clear()
		continue_msg = self.handle._build_continue_prompt(base=_SUMMARIZE_MSG)
		self.handle.Response('user', {'content': continue_msg})
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		return 0

	def CMD_PREVIEW_HISTORY(self, inp=""):
		"""!PH — compact color-coded preview of chat history."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history.")
			return 2
		a = inp.split()
		row = int(a[1]) if len(a) > 1 else None
		# Single row view — full content, no truncation
		if row is not None:
			return _ph_row_view(msgs, row)
		# Full history list
		return _ph_list_view(msgs)
	#
	def CMD_SEARCH_HISTORY(self, inp=""):
		"""!SH <term> — search chat history, printing matching row numbers."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history.")
			return 2
		a = inp.split()
		if len(a) < 2:
			print("Usage: !SH <term>   (or !SH -r <regex>)")
			return 2
		use_regex = False
		parts = a[1:]
		if parts and parts[0] == '-r':
			use_regex = True
			parts = parts[1:]
		if not parts:
			print("Usage: !SH <term>   (or !SH -r <regex>)")
			return 2
		term = ' '.join(parts)
		matches = _ph_search(msgs, term, regex=use_regex)
		return _ph_search_view(msgs, matches, term, use_regex)
	#
	def CMD_NAME_HISTORY(self, inp=""):
		"""!NH <name> — give a human-readable name to the current history session."""
		parts = inp.strip().split()
		if len(parts) < 2:
			print("Usage: !NH <name>")
			print("  name   — human-readable label (spaces become underscores)")
			return 2
		name = ' '.join(parts[1:])
		result = self.handle.hHM.set_current_name(name)
		print(result)
		return 2
	#
	def CMD_VIEW_HISTORY(self, inp=""):
		"""!AH [term] — list all available history files, or search them by term
		(same grep-based search as the startup history chooser)."""
		h = self.handle.hHM
		h.Update()
		a = inp.split()
		if len(a) > 1:
			term = ' '.join(a[1:])
			results = h._search(term)
			if not results:
				print("No history files matching '{}'.".format(term))
			else:
				h._show_list(results, h._load_names())
		else:
			h.Available()
		return 2
	#
	def CMD_UPDATE_HANDLE(self, inp):
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		return 4 # update class Handle()
	#
	def CMD_REHEAT(self, inp):
		"""!REHEAT — re-run the startup warm-up: refresh tool infos and reload tips.
		Clears tool caches (e.g. listTools) and resets consumed tips so the model
		can re-collect everything, then injects the warm-up message. Returns 0 so
		the outer Chat() loop calls AI() (which appends the [Tips: ...] notice)."""
		self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		self.handle.hLG.echo("Reheat — refreshing tool infos and reloading tips...",
			{'color':True, 'colorValue':'cyan','debugOnly':False})
		self.handle.Response('user', {'content': _REHEAT_MSG})
		return 0
	#
	def CMD_QUIT(self, inp):
		self.handle.Options['AI_LIVE']=False
		return 3 # as break
	#
	#

#--
# ANSI color codes used by the !PH history preview
_PH_R = '\033[0m'     # reset
_PH_G = '\033[1;32m'  # green — assistant
_PH_C = '\033[1;36m'  # cyan — user
_PH_Y = '\033[1;33m'  # yellow — system
_PH_B = '\033[1;34m'  # blue — tool
_PH_W = '\033[1;37m'  # white — header
_PH_D = '\033[2m'     # dim
_PH_BG = '\033[48;5;236m'  # dark gray background

def _ph_crc32(content):
	"""CRC32B (zlib) hex digest of message content — identical content shares a hash."""
	return '{:08x}'.format(zlib.crc32((content or '').encode('utf-8')))

def _ph_label(role, tool_name):
	if role == 'user':
		return _PH_C, 'USER'
	elif role == 'assistant':
		return _PH_G, 'ASSISTANT'
	elif role == 'system':
		return _PH_Y, 'SYSTEM'
	elif role == 'tool':
		return _PH_B, 'TOOL:{}'.format(tool_name) if tool_name else 'TOOL'
	else:
		return _PH_R, role.upper()

#--

def _ph_row_view(msgs, row):
	# Single row view — full content, no truncation
	if row < 0 or row >= len(msgs):
		print("Row {} out of range (0-{}).".format(row, len(msgs) - 1))
		return 2
	msg = msgs[row]
	role = msg.get('role', '?')
	content = msg.get('content', '')
	ts = msg.get('timestamp', 0)
	tool_name = msg.get('name', '')
	thinking = msg.get('thinking', '')
	time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S') if ts else '??:??:??'
	color, label = _ph_label(role, tool_name)
	# Header
	print()
	print("{}{}═{} {}[{}]{} {} {}{} {}═{}{}".format(
		_PH_D, '═' * 3, _PH_R, _PH_D, time_str, _PH_R, color + label + _PH_R, _PH_W, row, _PH_D, '═' * (40 - len(label)), _PH_R))
	# Thinking block
	if thinking:
		print("\n{}💡 Thinking:{}\n{}".format(_PH_D, _PH_R, thinking))
	# Content — full, not truncated
	if content:
		print("\n{}\n".format(content))
	else:
		print("\n{}(empty){}\n".format(_PH_D, _PH_R))
	# Footer
	print("{}{}═{} ({} chars) {} crc32b:{}{}".format(_PH_D, '═' * 50, _PH_R, len(content), _PH_D, _ph_crc32(content), _PH_R))
	return 2

#--

def _ph_format_row(i, msg, seen_hashes=None):
	role = msg.get('role', '?')
	content = msg.get('content', '')
	ts = msg.get('timestamp', 0)
	tool_name = msg.get('name', '')
	time_str = datetime.fromtimestamp(ts).strftime('%H:%M') if ts else '??:??'
	color, label = _ph_label(role, tool_name)
	# Truncate content to 80 chars, single-line
	preview = content.replace('\n', ' ').replace('\r', '')
	if len(preview) > 80:
		preview = preview[:80] + '...'
	elif not preview:
		preview = '(empty)'
	hash_str = _ph_crc32(content)
	# Mark duplicate content with a DUP label so repeated tool results are visible
	dup_marker = ''
	if seen_hashes is not None:
		if hash_str in seen_hashes:
			dup_marker = ' {}DUP{}'.format(_PH_D, _PH_R)
		seen_hashes.add(hash_str)
	return " {:>3} {} {}[{}]{} {:<14} {} {:>6} chars{}{} {}".format(
		i, _PH_D + hash_str + _PH_R, _PH_D, time_str, _PH_R, color + label + _PH_R,
		_PH_D, len(content), _PH_R, dup_marker, _PH_D + preview + _PH_R)

def _ph_stats(msgs):
	"""Compute per-role stats from history rows.
	Returns a dict: role -> (count, chars, tokens), plus 'all'.
	Tokens are the per-message attributed cost (prompt+response tokens stored
	on the row, e.g. assistant rows)."""
	stats = {}
	total_count = 0
	total_chars = 0
	total_tokens = 0
	for msg in msgs:
		if not isinstance(msg, dict):
			continue
		role = msg.get('role', '?') or '?'
		chars = len(msg.get('content', '') or '')
		tokens = int(msg.get('prompt_tokens', 0) or 0) + int(msg.get('response_tokens', 0) or 0)
		count, acc_chars, acc_tokens = stats.get(role, (0, 0, 0))
		stats[role] = (count + 1, acc_chars + chars, acc_tokens + tokens)
		total_count += 1
		total_chars += chars
		total_tokens += tokens
	stats['all'] = (total_count, total_chars, total_tokens)
	return stats

def _ph_stats_view(stats):
	"""Render the !PH statistics block — message counts, char totals and
	attributed tokens per role."""
	if not stats:
		return
	order = ['all', 'system', 'user', 'assistant', 'tool']
	colors = {
		'all': _PH_W,
		'system': _PH_Y,
		'user': _PH_C,
		'assistant': _PH_G,
		'tool': _PH_B,
	}
	print("{}=== STATISTICS ==={}\n".format(_PH_W, _PH_R))
	for role in order:
		entry = stats.get(role)
		if entry is None:
			continue
		count, chars, tokens = entry
		label = role.upper()
		msg_word = 'msg' if count == 1 else 'msgs'
		print("  {}{:<10}{} {}{:>5} {} / {}{:>7} chars / {}{:>8} tok{}".format(
			colors.get(role, _PH_R), label, _PH_R,
			_PH_D, count, msg_word,
			_PH_D, chars,
			_PH_D, tokens, _PH_R))
	print()

def _ph_list_view(msgs):
	# Full history list
	print("\n{}=== CHAT HISTORY ({} messages) ==={}\n".format(_PH_W, len(msgs), _PH_R))
	seen_hashes = set()
	for i, msg in enumerate(msgs):
		print(_ph_format_row(i, msg, seen_hashes))
	_ph_stats_view(_ph_stats(msgs))
	return 2

#--

def _ph_search(msgs, term, regex=False):
	"""Search history rows. Returns list of (index, msg) matching the term.

	Matches against content, thinking, and tool name. Substring (case-insensitive)
	by default, or a regex pattern when regex=True."""
	import re as _re
	matches = []
	if regex:
		try:
			pattern = _re.compile(term)
		except _re.error as e:
			print("Invalid regex: {}".format(e))
			return matches
		match = lambda text: bool(pattern.search(text or ''))
	else:
		low = term.lower()
		match = lambda text: low in (text or '').lower()
	for i, msg in enumerate(msgs):
		fields = [
			msg.get('content', ''),
			msg.get('thinking', ''),
			msg.get('name', ''),
		]
		if any(match(f) for f in fields):
			matches.append((i, msg))
	return matches

def _ph_search_view(msgs, matches, term, regex):
	# Search results — same row format as !PH so numbers feed !PH <N> / !RH <N>
	if not matches:
		print("No matches for {}{}{} in {} messages.".format(
			"regex " if regex else "'", term, "'" if not regex else "", len(msgs)))
		return 2
	kind = "REGEX" if regex else "TERM"
	print("\n{}=== HISTORY SEARCH [{} '{}'] — {} match(es) ==={}\n".format(
		_PH_W, kind, term, len(matches), _PH_R))
	seen_hashes = set()
	for i, msg in matches:
		print(_ph_format_row(i, msg, seen_hashes))
	print("{}Use !PH <row> to view, !RH <row> (or <from> <to>) to remove.{}".format(_PH_D, _PH_R))
	print()
	return 2
