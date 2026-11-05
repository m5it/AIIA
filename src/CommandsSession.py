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
		history/ folder. Default filename uses the session prefix so it appears
		in !AH / the history chooser."""
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
		# Write copy into history/ dir
		history_dir = "{}/history".format(self.handle.Options.get('path', '').rstrip('/'))
		main_path = os.path.join(history_dir, filename)
		self._write_history_lines(main_path, msgs)
		print("Saved history to {}".format(main_path))
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
	def _eh_default_filename(self, from_row, to_row, ext=".md"):
		"""Build a unique default export filename with timestamp so repeated exports don't overwrite."""
		ts = time.strftime("%Y%m%d_%H%M%S")
		if from_row == to_row:
			base = "export_{}_{}".format(from_row, ts)
		else:
			base = "export_{}-{}_{}".format(from_row, to_row, ts)
		return "workout/{}{}".format(base, ext)

	def _eh_parse_export_args(self, inp, cmd_tag):
		"""Shared parser for !EH / !EHH — returns (from_row, to_row, filename) or (None, error_msg)."""
		msgs = self.handle.hHM.msgs
		tokens = inp.strip().split()
		args = tokens[1:] if len(tokens) > 0 and tokens[0].upper() == cmd_tag else tokens
		if not args:
			return None, "Usage: !{} <row> [filename] | !{} <from> <to> [filename]".format(cmd_tag, cmd_tag)
		row_nums = []
		filename = None
		for i, a in enumerate(args):
			try:
				row_nums.append(int(a))
			except ValueError:
				filename = ' '.join(args[i:]).strip()
				if len(filename) >= 2 and filename[0] == filename[-1] and filename[0] in ('"', "'"):
					filename = filename[1:-1]
				break
			if len(row_nums) == 2:
				if i + 1 < len(args):
					filename = ' '.join(args[i + 1:]).strip()
					if len(filename) >= 2 and filename[0] == filename[-1] and filename[0] in ('"', "'"):
						filename = filename[1:-1]
				break
		if not row_nums:
			return None, "Row numbers must be integers (see !PH for row numbers)."
		if len(row_nums) == 1:
			from_row = to_row = row_nums[0]
		else:
			from_row, to_row = row_nums[0], row_nums[1]
			if from_row > to_row:
				from_row, to_row = to_row, from_row
		if from_row < 0 or to_row >= len(msgs):
			return None, "Rows {}-{} out of range. History has {} rows (0-{}).".format(from_row, to_row, len(msgs), len(msgs) - 1)
		if not filename:
			filename = self._eh_default_filename(from_row, to_row, ".md")
		else:
			# If user gave bare name with no extension, append .md
			if '/' not in filename and '\\' not in filename and os.path.splitext(filename)[1] == '':
				filename = "{}.md".format(filename)
			if '/' not in filename and '\\' not in filename:
				filename = "workout/{}".format(filename)
		return (from_row, to_row, filename), None

	def _eh_header_block(self, msg, row_idx):
		"""Render one message as markdown with header and JSON comment (importable)."""
		role = msg.get('role', 'unknown')
		tool_name = msg.get('name', '')
		ts = msg.get('timestamp', time.time())
		try:
			time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
		except Exception:
			time_str = '??:??'
		# Header
		if tool_name:
			header = "## [{}] {}: {} (row {})\n".format(time_str, role.upper(), tool_name, row_idx)
		else:
			header = "## [{}] {} (row {})\n".format(time_str, role.upper(), row_idx)
		# Thinking block if present
		body = ""
		thinking = msg.get('thinking', '')
		if thinking:
			body += "> Thinking: {}\n>\n".format(thinking.replace('\n', '\n> '))
		content = msg.get('content', '')
		if content is None:
			content = ''
		if content:
			body += content
		else:
			body += "(empty)"
		body += "\n\n---\n\n"
		# JSON comment for import (full fidelity, not truncated)
		json_comment = "<!-- {} -->\n\n".format(json.dumps(msg, ensure_ascii=False))
		return header + body + json_comment

	def CMD_EXPORT_HISTORY(self, inp=""):
		"""!EH <row> [filename] | !EH <from> <to> [filename] — export raw
		content of a chat history row (or inclusive range) to a file. Bare
		filenames are written to workout/; paths with directories are used
		as-is (parent dirs auto-created). Default filename now includes a
		timestamp so repeated exports don't collide:
		workout/export_<row>_<YYYYMMDD_HHMMSS>.md."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history to export.")
			return 2
		parsed, err = self._eh_parse_export_args(inp, "!EH")
		if err:
			print(err)
			if "Usage" not in err:
				print("Usage: !EH <row> [filename] | !EH <from> <to> [filename]")
			return 2
		from_row, to_row, filename = parsed
		parent = os.path.dirname(filename)
		if parent:
			try:
				os.makedirs(parent, exist_ok=True)
			except Exception as e:
				print("Error creating directory '{}': {}".format(parent, e))
				return 2
		selected = msgs[from_row:to_row + 1]
		parts = []
		for m in selected:
			c = m.get('content', '')
			if c is None:
				c = ''
			parts.append(c)
		content = '\n\n'.join(parts) if len(parts) > 1 else (parts[0] if parts else '')
		if not content:
			print("Warning: selected row(s) have empty content — writing empty file.")
		try:
			with open(filename, 'w', encoding='utf-8') as f:
				f.write(content)
		except Exception as e:
			print("Error writing '{}': {}".format(filename, e))
			return 2
		if from_row == to_row:
			role = selected[0].get('role', '?')
			print("Exported row {} [{}] ({} chars) to {} [raw]".format(from_row, role, len(content), filename))
		else:
			print("Exported rows {}-{} ({} rows, {} chars) to {} [raw]".format(from_row, to_row, len(selected), len(content), filename))
		return 2

	def CMD_EXPORT_HISTORY_HEADER(self, inp=""):
		"""!EHH <row> [filename] | !EHH <from> <to> [filename] — export with
		markdown header and JSON metadata (importable via !IH). Same path rules
		as !EH; default filename also includes a timestamp to avoid overwrites."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history to export.")
			return 2
		parsed, err = self._eh_parse_export_args(inp, "!EHH")
		if err:
			print(err)
			if "Usage" not in err:
				print("Usage: !EHH <row> [filename] | !EHH <from> <to> [filename]")
			return 2
		from_row, to_row, filename = parsed
		parent = os.path.dirname(filename)
		if parent:
			try:
				os.makedirs(parent, exist_ok=True)
			except Exception as e:
				print("Error creating directory '{}': {}".format(parent, e))
				return 2
		selected = msgs[from_row:to_row + 1]
		blocks = []
		for idx in range(from_row, to_row + 1):
			blocks.append(self._eh_header_block(msgs[idx], idx))
		content = "".join(blocks)
		try:
			with open(filename, 'w', encoding='utf-8') as f:
				f.write(content)
		except Exception as e:
			print("Error writing '{}': {}".format(filename, e))
			return 2
		if from_row == to_row:
			role = selected[0].get('role', '?')
			print("Exported row {} [{}] ({} chars) to {} [with header]".format(from_row, role, len(content), filename))
		else:
			print("Exported rows {}-{} ({} rows, {} chars) to {} [with header]".format(from_row, to_row, len(selected), len(content), filename))
		return 2

	def _ih_resolve_path(self, filename):
		"""Resolve import filename: bare name tries workout/ first, then as-is, then workin/."""
		if not filename:
			return None
		# Absolute or with dir component — use as-is
		if '/' in filename or '\\' in filename or os.path.isabs(filename):
			if os.path.exists(filename):
				return filename
			# Also try relative to CWD even if not exists yet (for error message)
			return filename
		# Bare name: try workout/, then as-is, then workin/
		for cand in ["workout/{}".format(filename), filename, "workin/{}".format(filename)]:
			if os.path.exists(cand):
				return cand
		return "workout/{}".format(filename)

	def _ih_parse_file(self, filepath):
		"""Parse import file into list of message dicts. Tries HTML-comment JSON, then JSON-lines, then raw."""
		import re
		try:
			with open(filepath, 'r', encoding='utf-8') as f:
				raw = f.read()
		except Exception as e:
			return None, "Cannot read '{}': {}".format(filepath, e)
		if not raw or not raw.strip():
			return None, "File '{}' is empty.".format(filepath)
		# 1) HTML comment JSON blocks: <!-- {...} -->
		comment_pat = re.compile(r'<!--\s*(\{.*?\})\s*-->', re.DOTALL)
		matches = comment_pat.findall(raw)
		if matches:
			msgs = []
			for jstr in matches:
				try:
					m = json.loads(jstr)
					if isinstance(m, dict) and m.get('role'):
						msgs.append(m)
				except Exception:
					continue
			if msgs:
				return msgs, None
		# 2) JSON-lines: each non-empty line is a JSON object with role
		lines = [l.strip() for l in raw.splitlines() if l.strip()]
		json_lines = []
		for l in lines:
			if l.startswith('{'):
				try:
					m = json.loads(l)
					if isinstance(m, dict) and m.get('role'):
						json_lines.append(m)
				except Exception:
					break
		if json_lines and len(json_lines) == len([l for l in lines if l.startswith('{')]):
			# All JSON-looking lines parsed successfully — treat as JSON-lines file
			if len(json_lines) == len(lines):
				return json_lines, None
			# Mixed content but at least some JSON lines — still use them if they cover all JSON lines
			if json_lines:
				return json_lines, None
		# 3) Raw: single user message with entire file content
		return [{'role': 'user', 'content': raw}], None

	def CMD_IMPORT_HISTORY(self, inp=""):
		"""!IH <filename> [row] [--replace] | !IMPORT <filename> [row] [--replace] — import
		messages from a file. Bare filenames are looked up in workout/ first. Without
		row, appends to end; with row N, inserts at position N. With --replace,
		replaces row(s) starting at N instead of inserting."""
		import shlex
		msgs = self.handle.hHM.msgs
		# Parse with shlex to handle quoted filenames
		try:
			tokens = shlex.split(inp.strip())
		except ValueError:
			tokens = inp.strip().split()
		# tokens[0] is !IH / !IMPORT
		if not tokens or len(tokens) == 1:
			print("Usage: !IH <filename> [row] [--replace] | !IMPORT <filename> [row] [--replace]")
			print("  filename  — file to import (bare name looks in workout/)")
			print("  row       — optional position to insert at (see !PH); omit to append")
			print("  --replace — replace row(s) at position instead of inserting")
			return 2
		args = tokens[1:]
		# Extract flags
		replace = False
		clean = []
		for a in args:
			if a.lower() in ('--replace', '-r', '--overwrite'):
				replace = True
			else:
				clean.append(a)
		args = clean
		if not args:
			print("Usage: !IH <filename> [row] [--replace]")
			return 2
		filename = args[0]
		row_pos = None
		if len(args) >= 2:
			try:
				row_pos = int(args[1])
			except ValueError:
				print("Row must be an integer (see !PH). Got: {}".format(args[1]))
				return 2
			if len(args) > 2:
				print("Usage: !IH <filename> [row] [--replace]")
				return 2
		elif len(args) > 2:
			print("Usage: !IH <filename> [row] [--replace]")
			return 2
		# Resolve path
		resolved = self._ih_resolve_path(filename)
		if not resolved or not os.path.exists(resolved):
			print("File not found: '{}' (tried workout/{} and ./{}).".format(filename, filename, filename))
			return 2
		# Parse file
		imported, err = self._ih_parse_file(resolved)
		if err:
			print(err)
			return 2
		if not imported:
			print("No messages found in '{}'.".format(resolved))
			return 2
		# Normalize imported messages: ensure required fields, assign current session id, fresh timestamps if missing
		now = time.time()
		date_str = str(datetime.now().date())
		current_sid = self.handle.Options.get('AI_SESS_ID', 0)
		for m in imported:
			if not m.get('role'):
				m['role'] = 'user'
			if m.get('content') is None:
				m['content'] = ''
			if not m.get('timestamp'):
				m['timestamp'] = now
			if not m.get('date'):
				m['date'] = date_str
			if not m.get('sessionId'):
				m['sessionId'] = current_sid
			# rowId will be reassigned below
		# Determine insertion
		if row_pos is None:
			# Append
			insert_at = len(msgs)
			msgs.extend(imported)
			action = "appended"
		else:
			if row_pos < 0 or row_pos > len(msgs):
				print("Row {} out of range. History has {} rows (0-{}). Use omit to append.".format(row_pos, len(msgs), len(msgs) - 1 if msgs else 0))
				return 2
			if replace:
				# Replace N rows starting at row_pos (or as many as imported, clamped)
				for i, m in enumerate(imported):
					idx = row_pos + i
					if idx < len(msgs):
						msgs[idx] = m
					else:
						msgs.append(m)
				insert_at = row_pos
				action = "replaced {} row(s) at {}".format(len(imported), row_pos)
			else:
				# Insert
				for i, m in enumerate(imported):
					msgs.insert(row_pos + i, m)
				insert_at = row_pos
				action = "inserted at {}".format(row_pos)
		# Renumber rowIds and update global counter
		for i, m in enumerate(msgs):
			m['rowId'] = i
		self.handle.Options['AI_ROW_ID'] = len(msgs)
		# Rewrite history files
		from src.PlanSaver import PlanSaver
		main_path = "{}/{}".format("{}/history".format(self.handle.Options.get('path', '')), self.handle.Options['AI_FILE_HISTORY'])
		try:
			os.remove(main_path)
		except Exception:
			pass
		for m in msgs:
			fwrite(main_path, "{}\n".format(json.dumps(m)), False)
		proj_dir = self.handle.Options.get('working_dir')
		framework_dir = self.handle.Options.get('path', '').rstrip('/')
		if proj_dir and proj_dir != framework_dir:
			proj_history = os.path.join(proj_dir, 'HISTORY.md')
			PlanSaver.rebuild_history(proj_history, msgs)
		# Report
		if len(imported) == 1:
			role = imported[0].get('role', '?')
			print("Imported 1 message [{}] from {} — {} (now {} rows).".format(role, resolved, action, len(msgs)))
		else:
			roles = {}
			for m in imported:
				r = m.get('role', '?')
				roles[r] = roles.get(r, 0) + 1
			parts = ', '.join("{} {}".format(n, r) for r, n in sorted(roles.items()))
			print("Imported {} messages ({}) from {} — {} (now {} rows).".format(len(imported), parts, resolved, action, len(msgs)))
		return 2

	def _im_parse_rows(self, spec, max_len):
		"""Parse flexible row spec like '10 12,15 17-20,23' into sorted unique indices.
		Supports spaces, commas, and ranges with -, .., : . Returns (rows, bad_tokens)."""
		import re
		if not spec or not spec.strip():
			return [], []
		# Normalize: replace commas with spaces, then split
		# Keep ranges like 17-20 intact
		tmp = spec.replace(',', ' ')
		parts = [p.strip() for p in tmp.split() if p.strip()]
		rows = set()
		bad = []
		for p in parts:
			# Range patterns: 10-12, 10..12, 10:12
			m = re.match(r'^(\d+)\s*(?:-|\.\.|:)\s*(\d+)$', p)
			if m:
				try:
					a = int(m.group(1)); b = int(m.group(2))
					if a > b:
						a, b = b, a
					for x in range(a, b+1):
						if 0 <= x < max_len:
							rows.add(x)
						else:
							# collect out-of-range as bad for warning
							bad.append(str(x))
					continue
				except ValueError:
					bad.append(p)
					continue
			# Single number
			try:
				v = int(p)
				if 0 <= v < max_len:
					rows.add(v)
				else:
					bad.append(p)
			except ValueError:
				bad.append(p)
		return sorted(rows), bad

	def CMD_IMPORTANT(self, inp=""):
		"""!IM [rows] | !IM --clear [rows] — pin/unpin rows so summarize keeps them.
		Rows spec is flexible: spaces, commas, and ranges (e.g. !IM 10 12,15 17-20,23).
		No args lists current pins. Pins are stored per-message as important:true."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history.")
			return 2
		raw = inp.strip()
		# Strip leading !IM
		spec = ""
		if raw.upper().startswith("!IM"):
			spec = raw[3:].strip()
		# No args -> list pins
		if not spec:
			pinned = [i for i, m in enumerate(msgs) if m.get('important')]
			if not pinned:
				print("No important (pinned) rows. Use !IM <rows> to pin (e.g. !IM 10 12,15 17-20).")
				return 2
			print("\n{}=== PINNED ROWS ({} via !IM) ==={}\n".format(_PH_Y, len(pinned), _PH_R))
			seen = set()
			for i in pinned:
				print(_ph_format_row(i, msgs[i], seen))
			print("{}Use !PH <row> to view, !IM --clear [rows] to unpin.{}\n".format(_PH_D, _PH_R))
			return 2
		# Detect clear mode
		clear = False
		low = spec.lower()
		if low.startswith('--clear') or low.startswith('--unpin') or low.startswith('--off') or low.startswith('clear'):
			clear = True
			# Remove the flag word
			for flag in ('--clear', '--unpin', '--off', 'clear'):
				if low.startswith(flag):
					spec = spec[len(flag):].strip()
					break
			# Bare !IM --clear with no rows -> clear all
			if not spec:
				cnt = 0
				for m in msgs:
					if m.get('important'):
						m.pop('important', None)
						cnt += 1
				# Rewrite history files to persist
				self.handle._rewrite_history(msgs)
				print("Cleared {} pinned row(s).".format(cnt))
				return 2
		# Parse row spec
		rows, bad = self._im_parse_rows(spec, len(msgs))
		if bad:
			print("Warning: ignored invalid/out-of-range entries: {}".format(", ".join(bad)))
		if not rows:
			print("No valid rows. Usage: !IM <rows> | !IM --clear [rows]")
			print("  rows: flexible e.g. 10 12,15 17-20,23")
			return 2
		changed = 0
		for r in rows:
			if clear:
				if msgs[r].get('important'):
					msgs[r].pop('important', None)
					changed += 1
			else:
				if not msgs[r].get('important'):
					msgs[r]['important'] = True
					changed += 1
		# Persist
		self.handle._rewrite_history(msgs)
		if clear:
			print("Unpinned {} row(s): {}".format(changed, ", ".join(str(x) for x in rows)))
		else:
			print("Pinned {} row(s) as important: {}".format(changed, ", ".join(str(x) for x in rows)))
			# Show them
			seen = set()
			for r in rows:
				print(_ph_format_row(r, msgs[r], seen))
		return 2


	def CMD_IMSTAT(self, inp=""):
		"""!IMSTAT — show pinned/important rows with stats."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history.")
			return 2
		pinned = [(i, m) for i, m in enumerate(msgs) if m.get('important')]
		if not pinned:
			print("No important (pinned) rows — use !IM <rows> to pin.")
			return 2
		print("\n{}=== IMPORTANT ROWS ({} pinned, via !IM) ==={}\n".format(_PH_Y, len(pinned), _PH_R))
		# Per-role counts
		roles = {}
		for _, m in pinned:
			r = m.get('role', '?')
			roles[r] = roles.get(r, 0) + 1
		parts = ', '.join("{} {}".format(n, r) for r, n in sorted(roles.items()))
		print("{}Pinned: {} | Total history: {} rows{}\n".format(_PH_D, parts, len(msgs), _PH_R))
		seen = set()
		for i, m in pinned:
			print(_ph_format_row(i, m, seen))
		print("\n{}Use !IR <rows> or !IM --clear [rows] to unpin; !PH <row> to view.{}\n".format(_PH_D, _PH_R))
		return 2

	def CMD_IR(self, inp=""):
		"""!IR [rows] | !IR --all — unpin rows (remove important flag). Flexible row spec."""
		msgs = self.handle.hHM.msgs
		if not msgs:
			print("No history.")
			return 2
		raw = inp.strip()
		spec = ""
		if raw.upper().startswith("!IR"):
			spec = raw[3:].strip()
		# Normalize --all flag
		low = spec.lower()
		if low in ('--all', 'all', '*'):
			spec = ""
		if not spec:
			# No rows -> if there are pinned rows, unpin all (confirm via print)
			pinned = [i for i, m in enumerate(msgs) if m.get('important')]
			if not pinned:
				print("No important rows to remove.")
				return 2
			cnt = 0
			for i in pinned:
				msgs[i].pop('important', None)
				cnt += 1
			self.handle._rewrite_history(msgs)
			print("Unpinned {} row(s) (all).".format(cnt))
			return 2
		# Handle --clear prefix if user typed !IR --clear ...
		if low.startswith('--clear'):
			spec = spec[len('--clear'):].strip()
		elif low.startswith('--unpin'):
			spec = spec[len('--unpin'):].strip()
		if not spec:
			print("Usage: !IR <rows> | !IR --all  (rows: 10 12,15 17-20 — flexible)")
			return 2
		rows, bad = self._im_parse_rows(spec, len(msgs))
		if bad:
			print("Warning: ignored invalid/out-of-range entries: {}".format(", ".join(bad)))
		if not rows:
			print("No valid rows. Usage: !IR <rows> | !IR --all")
			return 2
		changed = 0
		for r in rows:
			if msgs[r].get('important'):
				msgs[r].pop('important', None)
				changed += 1
		self.handle._rewrite_history(msgs)
		print("Unpinned {} row(s): {}".format(changed, ", ".join(str(x) for x in rows)))
		return 2

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
	pinned = msg.get('important')
	time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S') if ts else '??:??:??'
	color, label = _ph_label(role, tool_name)
	# Header
	print()
	pin_tag = " {}★ PINNED{}".format(_PH_Y, _PH_R) if pinned else ""
	print("{}{}═{} {}[{}]{} {} {}{} {}═{}{}{}".format(
		_PH_D, '═' * 3, _PH_R, _PH_D, time_str, _PH_R, color + label + _PH_R, _PH_W, row, _PH_D, '═' * (40 - len(label)), _PH_R, pin_tag))
	# Thinking block
	if thinking:
		print("\n{}💡 Thinking:{}\n{}".format(_PH_D, _PH_R, thinking))
	# Content — full, not truncated
	if content:
		print("\n{}\n".format(content))
	else:
		print("\n{}(empty){}\n".format(_PH_D, _PH_R))
	# Footer
	print("{}{}═{} ({} chars) {} crc32b:{} {}{}".format(_PH_D, '═' * 50, _PH_R, len(content), _PH_D, _ph_crc32(content), _PH_R, "★ pinned" if pinned else "", _PH_R))
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
	pin_marker = ' {}★{}'.format(_PH_Y, _PH_R) if msg.get('important') else ''
	return " {:>3} {} {}[{}]{} {:<14} {} {:>6} chars{}{} {}".format(
		i, _PH_D + hash_str + _PH_R, _PH_D, time_str, _PH_R, color + label + _PH_R,
		_PH_D, len(content), _PH_R, dup_marker + pin_marker, _PH_D + preview + _PH_R)

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
