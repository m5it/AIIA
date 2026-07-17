import os

class ReplaceLine():
	def __init__(self):
		self.info = {
			"name":"ReplaceLine",
			"description":"Replace a specific line or range of lines in a file with new content. Lines are 1-indexed. First call previews the current content; call again with confirmed=true to apply.",
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
	#
	def run(self, fileName="", fromLine=None, toLine=None, replacement="", confirmed="false"):
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

		# Preview: show current content without modifying
		confirmed = confirmed.lower() in ('true', '1', 'yes')
		old_lines = lines[fl - 1:tl]
		old_text = ''.join(old_lines)
		old_preview = old_text.replace('\n', '\\n')
		if len(old_preview) > 200:
			old_preview = old_preview[:200] + '...'

		if not confirmed:
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

		# Confirmed — execute the replacement
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
		try:
			with open(full_path, 'w') as f:
				f.writelines(new_lines)
		except Exception as e:
			return "Error: {}".format(e)
		#
		count = tl - fl + 1
		new_count = len(repl_lines)
		return "Replaced line{} {}-{} in '{}'. ({} old line{} -> {} new line{}). Old content: {}".format(
			's' if count > 1 else '', fl, tl, fileName,
			count, 's' if count != 1 else '',
			new_count, 's' if new_count != 1 else '',
			old_preview)
