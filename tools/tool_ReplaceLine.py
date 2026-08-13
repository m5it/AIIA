import os
import hashlib
import difflib
import subprocess
import tempfile
import time
from config import Options
from src.ToolParser import ToolParser

# Context lines shown around the changed region in the verification diff
_DIFF_CONTEXT = 2
# Max diff output chars returned to the model (prevents context flooding)
_DIFF_MAX_CHARS = 6000

class ReplaceLine():
	def __init__(self):
		zero_indexed = Options.get('REPLACELINE_ZERO_INDEXED', False)
		idx_desc = "0-indexed (first line = 0)" if zero_indexed else "1-indexed (first line = 1, default)"
		simple_mode = self._is_simple_mode()
		if simple_mode:
			desc = "Replace a specific line or range of lines in a file with new content. Lines are {}. SIMPLE MODE is enabled: ReadFile with <lineNumbers>true</lineNumbers> first, then call ReplaceLine directly with the exact line numbers and the replacement text. The change is applied immediately without preview/confirmation.".format(idx_desc)
		else:
			desc = "Replace a specific line or range of lines in a file with new content. Lines are {}. Three-phase flow: (1) first call previews; (2) call with confirmed=true applies the change, backs up the whole file to /tmp, and shows a verification diff of old vs new; (3) call again with confirmed=finalize to accept the verified diff, or confirmed=revert to restore the original file from backup.".format(idx_desc)
		self.info = {
			"name":"ReplaceLine",
			"description": desc,
			"parameters":{
				"returnType":"string",
				"required":["fileName","fromLine","replacement"],
				"properties":{
					"fileName":{
						"type":"string",
						"description":"File to edit."
					},
					"fromLine":{
						"type":"number",
						"description":"Starting line number ({}).".format(idx_desc)
					},
					"toLine":{
						"type":"number",
						"description":"(Optional) Ending line number ({}). If omitted, replaces only fromLine.".format(idx_desc)
					},
					"replacement":{
						"type":"string",
						"description":"New content for the specified line(s). Multi-line supported."
					},
					"confirmed":{
						"type":"string",
						"default":"false",
						"description":"true = apply the replacement (after preview) and show a verification diff; finalize = accept the verified diff; revert = restore the file from backup."
					},
				},
			},
		}
		# Two-phase enforcement state
		self._preview_key = None   # key of last previewed replacement
		self._saved_hash = None    # SHA256 of file at preview time
		# Pending-apply state (backup until finalize/revert)
		self._backup_path = None   # /tmp backup of the whole file before apply
	#
	@staticmethod
	def _make_key(full_path, fromLine, toLine, replacement):
		raw = "{}:{}:{}:{}".format(full_path, fromLine, toLine, replacement)
		return hashlib.sha256(raw.encode()).hexdigest()
	#
	@staticmethod
	def _compute_hash(path):
		h = hashlib.sha256()
		with open(path, 'rb') as f:
			for chunk in iter(lambda: f.read(8192), b''):
				h.update(chunk)
		return h.hexdigest()
	#
	def _is_zero_indexed(self):
		return Options.get('REPLACELINE_ZERO_INDEXED', False)
	#
	def _is_simple_mode(self):
		return Options.get('REPLACELINE_SIMPLE_MODE', False)
	#
	def _min_line(self):
		return 0 if self._is_zero_indexed() else 1
	#
	def _to_array_index(self, line_num):
		"""Convert user line number to Python array index."""
		if self._is_zero_indexed():
			return line_num
		return line_num - 1
	#
	def _preview(self, fileName, fl, tl, replacement, old_text, diff, indent_warn):
		return ("Line{} {}-{} in '{}' currently reads:\n"
			"```\n{}\n```\n"
			"Proposed replacement:\n"
			"```\n{}\n```\n"
			"--- PREVIEW DIFF (old vs proposed, ±{} context) ---\n"
			"{}\n"
			"{}\n"
			"To apply, add <confirmed>true</confirmed> to your ReplaceLine call.").format(
				's' if tl != fl else '', fl, tl, fileName,
				old_text.rstrip('\n'),
				replacement.rstrip('\n'),
				_DIFF_CONTEXT, diff, indent_warn)
	#
	def _remove_backup(self):
		"""Delete any pending backup file and clear the state."""
		if self._backup_path and os.path.exists(self._backup_path):
			try:
				os.remove(self._backup_path)
			except Exception:
				pass
		self._backup_path = None
	#
	def _make_backup(self, full_path):
		"""Save a whole-file backup to /tmp (tmpfs — RAM) and return its path.
		Any previous pending backup is replaced."""
		self._remove_backup()
		fname = 'replaceline_{}_{}_{}.bak'.format(
			hashlib.sha256(full_path.encode()).hexdigest()[:10],
			os.getpid(),
			int(time.time() * 1000))
		backup_path = os.path.join(tempfile.gettempdir(), fname)
		with open(full_path, 'rb') as f:
			data = f.read()
		with open(backup_path, 'wb') as f:
			f.write(data)
		return backup_path
	#
	@staticmethod
	def _restore_file(backup_path, full_path):
		with open(backup_path, 'rb') as f:
			data = f.read()
		with open(full_path, 'wb') as f:
			f.write(data)
	#
	def _clear_pending(self):
		"""Finalize/revert cleanup — drop backup and preview tokens."""
		self._remove_backup()
		self._preview_key = None
		self._saved_hash = None
	#
	def _verification_diff(self, backup_path, full_path):
		"""Unified diff (old vs new) with context lines around the change.
		Uses the terminal `diff -U`; falls back to Python difflib."""
		diff = None
		try:
			label_old = 'old/{}'.format(os.path.basename(full_path))
			label_new = 'new/{}'.format(os.path.basename(full_path))
			cmd = ['diff', '-U', str(_DIFF_CONTEXT), '--label', label_old,
				'--label', label_new, backup_path, full_path]
			r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
			if r.stdout:
				diff = r.stdout
		except Exception:
			pass
		if diff is None:
			try:
				with open(backup_path) as f:
					old_l = f.readlines()
				with open(full_path) as f:
					new_l = f.readlines()
				diff = ''.join(difflib.unified_diff(
					old_l, new_l, 'old/{}'.format(os.path.basename(full_path)),
					'new/{}'.format(os.path.basename(full_path)), n=_DIFF_CONTEXT))
			except Exception as e:
				return "(could not build diff: {})".format(e)
		if not diff or not diff.strip():
			return "(no difference detected)"
		if len(diff) > _DIFF_MAX_CHARS:
			diff = diff[:_DIFF_MAX_CHARS] + "\n... (diff truncated, {} chars total)".format(len(diff))
		return diff
	#
	def _diff_lines(self, old_lines, new_lines, fname):
		"""Unified diff of two in-memory line lists (used for the preview,
		before the change is applied). Falls back cleanly on any failure."""
		try:
			diff = ''.join(difflib.unified_diff(
				old_lines, new_lines,
				'old/{}'.format(os.path.basename(fname)),
				'new/{}'.format(os.path.basename(fname)), n=_DIFF_CONTEXT))
		except Exception as e:
			return "(could not build diff: {})".format(e)
		if not diff or not diff.strip():
			return "(no difference detected)"
		if len(diff) > _DIFF_MAX_CHARS:
			diff = diff[:_DIFF_MAX_CHARS] + "\n... (diff truncated, {} chars total)".format(len(diff))
		return diff
	#
	def _indent_check(self, lines, new_lines, arr_fl, repl_lines):
		"""Heuristic indentation check on the replaced block vs its context.
		Returns a warning string (one line per issue) or '' if nothing looks off.
		Non-blocking: warns only, never prevents the edit."""
		def _lead(ln):
			stripped = ln.lstrip(' \t')
			return ln[:len(ln) - len(stripped)]
		block = new_lines[arr_fl:arr_fl + len(repl_lines)]
		ws = [_lead(l) for l in block if l.strip()]
		if not ws:
			return ''
		warns = []
		# 1) Mixed tabs and spaces inside the block
		for i, l in enumerate(block):
			if l.strip():
				lead = _lead(l)
				if '\t' in lead and ' ' in lead:
					warns.append("replaced block mixes tabs and spaces in indentation (line {}).".format(arr_fl + 1 + i))
		# 2) Indent family mismatch vs surrounding context
		ctx_before = ''
		for i in range(arr_fl - 1, -1, -1):
			if lines[i].strip():
				ctx_before = _lead(lines[i])
				break
		ctx_after = ''
		for i in range(arr_fl + len(repl_lines), len(new_lines)):
			if new_lines[i].strip():
				ctx_after = _lead(new_lines[i])
				break
		base = ws[0]
		def _fam(x):
			return 'tabs' if '\t' in x else 'spaces'
		if base and ctx_before and _fam(base) != _fam(ctx_before):
			warns.append("replaced block uses {} indentation but the code above uses {}.".format(_fam(base), _fam(ctx_before)))
		if base and ctx_after and _fam(base) != _fam(ctx_after):
			warns.append("replaced block uses {} indentation but the code below uses {}.".format(_fam(base), _fam(ctx_after)))
		# 3) Depth mismatch vs the original line being replaced
		orig_first = _lead(lines[arr_fl]) if arr_fl < len(lines) else ''
		if base != orig_first:
			warns.append("replaced block is indented at level '{}' while the original line was at '{}'.".format(
				base, orig_first))
		return '\n'.join('⚠ ' + w for w in warns) if warns else ''
	#
	def _apply_simple(self, fileName, full_path, lines, new_lines, arr_fl, arr_tl, repl_lines):
		"""Apply the replacement immediately without preview/confirmation/finalize.
		Used when REPLACELINE_SIMPLE_MODE is enabled."""
		new_content = ''.join(new_lines)
		# File-size guards
		if len(new_content.strip()) == 0 and len(''.join(lines).strip()) > 0:
			return "Error: replacement would result in empty file — blocked to prevent data loss."
		if len(new_content) > len(''.join(lines)) * 10 and len(new_content) > 100000:
			return "Error: replacement would grow file to {} bytes ({:.0f}x original) — likely incorrect replacement.".format(
				len(new_content), len(new_content) / max(len(''.join(lines)), 1))
		try:
			with open(full_path, 'w') as f:
				f.writelines(new_lines)
		except Exception as e:
			return "Error: failed to write '{}': {}".format(fileName, e)
		old_text = ''.join(lines[arr_fl:arr_tl + 1])
		count = arr_tl - arr_fl + 1
		new_count = len(repl_lines)
		indent_warn = self._indent_check(lines, new_lines, arr_fl, repl_lines)
		result = "Replaced line{} {}-{} in '{}'. ({} old line{} -> {} new line{}).".format(
			's' if count > 1 else '', self._min_line() + arr_fl, self._min_line() + arr_tl, fileName,
			count, 's' if count != 1 else '',
			new_count, 's' if new_count != 1 else '')
		if indent_warn:
			result += "\n" + indent_warn
		return result

	def _echo_user(self, message):
		"""Print a message to the user's console (if a handle is active).
		Tool results are normally truncated to 500 chars on the console, so
		diffs get their own full-length echo."""
		try:
			handle = ToolParser._current_handle
			if handle and handle.hLG:
				handle.hLG.echo(message, {'color': True, 'colorValue': 'orange'})
		except Exception:
			pass
	#
	def _handle_confirm(self, action, fileName, full_path):
		"""Handle confirmed=finalize / confirmed=revert after a pending apply."""
		if not self._backup_path or not os.path.exists(self._backup_path):
			self._clear_pending()
			return ("Error: no pending replacement for '{}' to {} — "
				"run ReplaceLine with <confirmed>true</confirmed> first.").format(fileName, action)
		if action == 'revert':
			try:
				self._restore_file(self._backup_path, full_path)
			except Exception as e:
				return "Error: failed to revert '{}': {}".format(fileName, e)
			self._clear_pending()
			return "Reverted '{}' — restored original content from backup. Pending state cleared.".format(fileName)
		# finalize
		self._clear_pending()
		return "Finalized — replacement in '{}' accepted (diff reviewed, backup cleared).".format(fileName)
	#
	def run(self, fileName="", fromLine=None, toLine=None, replacement="", confirmed="false"):
		preview_text = None
		min_line = self._min_line()
		zero_idx = self._is_zero_indexed()
		idx_label = "0-indexed" if zero_idx else "1-indexed"

		if not fileName or fromLine is None:
			return "Error: fileName and fromLine are required.\nUsage: <ReplaceLine><fileName>path</fileName><fromLine>{}</fromLine><replacement>new text</replacement></ReplaceLine>".format(min_line)
		try:
			fl = int(fromLine)
		except Exception:
			return "Error: fromLine must be a number."
		tl = fl
		if toLine is not None:
			try:
				tl = int(toLine)
			except Exception:
				return "Error: toLine must be a number."
		if fl < min_line or tl < fl:
			return "Error: invalid range — fromLine must be >= {} ({}) and toLine >= fromLine.".format(min_line, idx_label)
		#
		full_path = fileName if os.path.isabs(fileName) else os.path.join(os.getcwd(), fileName)
		if not os.path.exists(full_path):
			return "Error: file '{}' not found.".format(fileName)
		try:
			with open(full_path, 'r') as f:
				lines = f.readlines()
		except Exception as e:
			return "Error: {}".format(e)
		#
		total = len(lines)
		max_line = total - 1 if zero_idx else total
		if fl > max_line:
			return "Error: fromLine {} exceeds file length ({} lines, max {} {}).".format(fl, total, max_line, idx_label)
		if tl > max_line:
			return "Error: toLine {} exceeds file length ({} lines, max {} {}).".format(tl, total, max_line, idx_label)
		#
		confirmed_val = (confirmed or '').strip().lower()
		# Simple mode bypasses the two-phase preview/confirm/finalize flow entirely.
		arr_fl = self._to_array_index(fl)
		arr_tl = self._to_array_index(tl)
		if self._is_simple_mode():
			old_lines = lines[arr_fl:arr_tl + 1]
			old_text = ''.join(old_lines)
			# Simulate replacement
			repl = replacement
			if not repl.endswith('\n'):
				repl += '\n'
			repl_lines = repl.split('\n')
			if repl_lines and repl_lines[-1] == '':
				repl_lines = repl_lines[:-1]
			repl_lines = [l + '\n' for l in repl_lines]
			new_lines = lines[:arr_fl] + repl_lines + lines[arr_tl + 1:]
			return self._apply_simple(fileName, full_path, lines, new_lines, arr_fl, arr_tl, repl_lines)
		#
		if confirmed_val in ('finalize', 'revert'):
			return self._handle_confirm(confirmed_val, fileName, full_path)
		confirmed = confirmed_val in ('true', '1', 'yes')
		current_key = self._make_key(full_path, fl, tl, replacement)
		old_lines = lines[arr_fl:arr_tl + 1]
		old_text = ''.join(old_lines)

		# Simulate the replacement exactly as the apply step would write it,
		# so the preview diff matches what confirmed=true will actually produce.
		repl = replacement
		if not repl.endswith('\n'):
			repl += '\n'
		repl_lines = repl.split('\n')
		if repl_lines and repl_lines[-1] == '':
			repl_lines = repl_lines[:-1]
		repl_lines = [l + '\n' for l in repl_lines]
		sim_new_lines = lines[:arr_fl] + repl_lines + lines[arr_tl + 1:]

		# --- Two-phase enforcement ---
		preview_diff = self._diff_lines(lines, sim_new_lines, fileName)
		indent_warn = self._indent_check(lines, sim_new_lines, arr_fl, repl_lines)
		preview_echo = preview_diff + (("\n" + indent_warn) if indent_warn else "")
		if confirmed:
			# Check: has the file changed since a prior preview?
			if self._preview_key == current_key:
				current_hash = self._compute_hash(full_path)
				if current_hash != self._saved_hash:
					# File changed — reject, force fresh preview
					self._preview_key = current_key
					self._saved_hash = current_hash
					return ("⚠ File changed since preview (another tool or process modified it). "
						"Showing fresh preview.\n\n") + self._preview(fileName, fl, tl, replacement, old_text, preview_diff, indent_warn)
			# No matching preview OR file unchanged — preview + execute in one pass
			self._preview_key = None
			self._saved_hash = None
			preview_text = self._preview(fileName, fl, tl, replacement, old_text, preview_diff, indent_warn)
		else:
			# First call (or non-matching) — store preview token
			self._preview_key = current_key
			self._saved_hash = self._compute_hash(full_path)
			self._echo_user("ReplaceLine preview diff for '{}':\n{}".format(fileName, preview_echo))
			return self._preview(fileName, fl, tl, replacement, old_text, preview_diff, indent_warn)

		# --- Execute the replacement ---
		new_lines = sim_new_lines
		#
		# File-size guard
		new_content = ''.join(new_lines)
		if len(new_content.strip()) == 0 and len(''.join(lines).strip()) > 0:
			return "Error: replacement would result in empty file — blocked to prevent data loss."
		if len(new_content) > len(''.join(lines)) * 10 and len(new_content) > 100000:
			return "Error: replacement would grow file to {} bytes ({:.0f}x original) — likely incorrect replacement.".format(
				len(new_content), len(new_content) / max(len(''.join(lines)), 1))
		#
		# Back up the whole file before writing (enables revert + diff verification)
		backup_path = self._make_backup(full_path)
		try:
			with open(full_path, 'w') as f:
				f.writelines(new_lines)
		except Exception as e:
			try:
				self._restore_file(backup_path, full_path)
			except Exception:
				pass
			self._remove_backup()
			return "Error: {}".format(e)
		self._backup_path = backup_path
		#
		count = tl - fl + 1
		new_count = len(repl_lines)
		result = "Replaced line{} {}-{} in '{}'. ({} old line{} -> {} new line{}). Old content: {}".format(
			's' if count > 1 else '', fl, tl, fileName,
			count, 's' if count != 1 else '',
			new_count, 's' if new_count != 1 else '',
			old_text.replace('\n', '\\n')[:200])
		if preview_text:
			result = preview_text + "\n\n" + result
		#
		diff = self._verification_diff(backup_path, full_path)
		indent_warn = self._indent_check(lines, new_lines, arr_fl, repl_lines)
		if indent_warn:
			diff += "\n" + indent_warn
		self._echo_user("ReplaceLine verification diff for '{}':\n{}".format(fileName, diff))
		return ("{}\n\n--- VERIFICATION DIFF (old vs new, ±{} context) ---\n"
			"{}\n\nBackup: {}\n"
			"If the diff is correct, call ReplaceLine again with <confirmed>finalize</confirmed> to accept it. "
			"If it is wrong, call with <confirmed>revert</confirmed> to restore the original file from backup.").format(
				result, _DIFF_CONTEXT, diff, backup_path)
