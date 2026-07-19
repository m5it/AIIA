import os
import hashlib

class ReplaceLine():
	def __init__(self):
		self.info = {
			"name":"ReplaceLine",
			"description":"Replace a specific line or range of lines in a file with new content. Lines are 1-indexed. First call previews; second call with confirmed=true executes. If confirmed=true without a prior preview, preview + execute happen in one pass.",
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
						"description":"Starting line number (1-indexed)."
					},
					"toLine":{
						"type":"number",
						"description":"(Optional) Ending line number. If omitted, replaces only fromLine."
					},
					"replacement":{
						"type":"string",
						"description":"New content for the specified line(s). Multi-line supported."
					},
					"confirmed":{
						"type":"string",
						"default":"false",
						"description":"Set to true to confirm and execute the replacement after previewing the current content."
					},
				},
			},
		}
		# Two-phase enforcement state
		self._preview_key = None   # key of last previewed replacement
		self._saved_hash = None    # SHA256 of file at preview time
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
	def _preview(self, fileName, fl, tl, replacement, old_text):
		new_preview = replacement.replace('\n', '\\n')
		if len(new_preview) > 200:
			new_preview = new_preview[:200] + '...'
		return ("Line{} {}-{} in '{}' currently reads:\n"
			"```\n{}\n```\n"
			"Proposed replacement:\n"
			"```\n{}\n```\n"
			"To confirm, add <confirmed>true</confirmed> to your ReplaceLine call.").format(
				's' if tl != fl else '', fl, tl, fileName,
				old_text.rstrip('\n'),
				replacement.rstrip('\n'))
	#
	def run(self, fileName="", fromLine=None, toLine=None, replacement="", confirmed="false"):
		preview_text = None
		if not fileName or fromLine is None:
			return "Error: fileName and fromLine are required.\nUsage: <ReplaceLine><fileName>path</fileName><fromLine>10</fromLine><replacement>new text</replacement></ReplaceLine>"
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
		if fl < 1 or tl < fl:
			return "Error: invalid range — fromLine must be >= 1 and toLine >= fromLine."
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
		if fl > total:
			return "Error: fromLine {} exceeds file length ({} lines).".format(fl, total)
		if tl > total:
			return "Error: toLine {} exceeds file length ({} lines).".format(tl, total)
		#
		confirmed = confirmed.lower() in ('true', '1', 'yes')
		current_key = self._make_key(full_path, fl, tl, replacement)
		old_lines = lines[fl - 1:tl]
		old_text = ''.join(old_lines)

		# --- Two-phase enforcement ---
		if confirmed:
			# Check: has the file changed since a prior preview?
			if self._preview_key == current_key:
				current_hash = self._compute_hash(full_path)
				if current_hash != self._saved_hash:
					# File changed — reject, force fresh preview
					self._preview_key = current_key
					self._saved_hash = current_hash
					return ("⚠ File changed since preview (another tool or process modified it). "
						"Showing fresh preview.\n\n") + self._preview(fileName, fl, tl, replacement, old_text)
			# No matching preview OR file unchanged — preview + execute in one pass
			self._preview_key = None
			self._saved_hash = None
			preview_text = self._preview(fileName, fl, tl, replacement, old_text)
		else:
			# First call (or non-matching) — store preview token
			self._preview_key = current_key
			self._saved_hash = self._compute_hash(full_path)
			return self._preview(fileName, fl, tl, replacement, old_text)

		# --- Execute the replacement ---
		repl = replacement
		if not repl.endswith('\n'):
			repl += '\n'
		#
		repl_lines = repl.split('\n')
		if repl_lines and repl_lines[-1] == '':
			repl_lines = repl_lines[:-1]
		repl_lines = [l + '\n' for l in repl_lines]
		#
		new_lines = lines[:fl - 1] + repl_lines + lines[tl:]
		#
		# File-size guard
		new_content = ''.join(new_lines)
		if len(new_content.strip()) == 0 and len(''.join(lines).strip()) > 0:
			return "Error: replacement would result in empty file — blocked to prevent data loss."
		if len(new_content) > len(''.join(lines)) * 10 and len(new_content) > 100000:
			return "Error: replacement would grow file to {} bytes ({:.0f}x original) — likely incorrect replacement.".format(
				len(new_content), len(new_content) / max(len(''.join(lines)), 1))
		#
		try:
			with open(full_path, 'w') as f:
				f.writelines(new_lines)
		except Exception as e:
			return "Error: {}".format(e)
		#
		count = tl - fl + 1
		new_count = len(repl_lines)
		result = "Replaced line{} {}-{} in '{}'. ({} old line{} -> {} new line{}). Old content: {}".format(
			's' if count > 1 else '', fl, tl, fileName,
			count, 's' if count != 1 else '',
			new_count, 's' if new_count != 1 else '',
			old_text.replace('\n', '\\n')[:200])
		if preview_text:
			return preview_text + "\n\n" + result
		return result
