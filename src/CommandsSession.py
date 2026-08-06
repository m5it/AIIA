#--
# class CommandsSession — session & history commands
import os, json, zlib
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
		if len(a) < 2:
			print("Usage: !RH <row_num>")
			return 2
		try:
			num = int(a[1])
		except ValueError:
			print("Row number must be an integer.")
			return 2
		if num < 0 or num >= len(self.handle.hHM.msgs):
			print("Row {} does not exist. History has {} rows.".format(num, len(self.handle.hHM.msgs)))
			return 2
		removed = self.handle.hHM.msgs.pop(num)
		print("Removed row {}: [{}] {}".format(num, removed.get('role','?'), removed.get('content','')[:80]))
		# Rebuild main history file on disk
		main_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in self.handle.hHM.msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		# Rebuild project HISTORY.md
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, self.handle.hHM.msgs)
		return 2
	#
	#
	def CMD_SUMMARIZE(self, inp=""):
		self.handle.hLG.echo("Summarizing — clearing history, keeping system messages...",
			{'color':True, 'colorValue':'orange','debugOnly':False})
		self.handle._auto_clear()
		return 2

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
		"""!AH — list all available history files with sizes and display names."""
		self.handle.hHM.Available()
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

def _ph_format_row(i, msg):
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
	return " {:>3} {} {}[{}]{} {:<14} {} {:>6} chars{} {}".format(
		i, _PH_D + _ph_crc32(content) + _PH_R, _PH_D, time_str, _PH_R, color + label + _PH_R,
		_PH_D, len(content), _PH_R, _PH_D + preview + _PH_R)

def _ph_list_view(msgs):
	# Full history list
	print("\n{}=== CHAT HISTORY ({} messages) ==={}\n".format(_PH_W, len(msgs), _PH_R))
	for i, msg in enumerate(msgs):
		print(_ph_format_row(i, msg))
	print()
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
	for i, msg in matches:
		print(_ph_format_row(i, msg))
	print("{}Use !PH <row> to view, !RH <row> to remove.{}".format(_PH_D, _PH_R))
	print()
	return 2
