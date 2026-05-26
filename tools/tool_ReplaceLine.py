import os

class ReplaceLine():
	def __init__(self):
		self.info = {
			"name":"ReplaceLine",
			"description":"Replace a specific line or range of lines in a file with new content. Lines are 1-indexed.",
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
				},
			},
		}
	#
	def run(self, fileName="", fromLine=None, toLine=None, replacement="", opts={}):
		if not fileName or fromLine is None:
			return "Error: fileName and fromLine are required.\nUsage: <ReplaceLine><fileName>path</fileName><fromLine>10</fromLine><replacement>new text</replacement></ReplaceLine>"
		try:
			fl = int(fromLine)
		except:
			return "Error: fromLine must be a number."
		tl = fl
		if toLine is not None:
			try:
				tl = int(toLine)
			except:
				return "Error: toLine must be a number."
		if fl < 1 or tl < fl:
			return "Error: invalid range — fromLine must be >= 1 and toLine >= fromLine."
		#
		full_path = "{}".format(fileName)
		if not os.path.exists(full_path):
			return "Error: file '{}' not found.".format(fileName)
		try:
			with open(full_path, 'r') as f:
				lines = f.readlines()
		except Exception as e:
			return "Error reading file: {}".format(e)
		#
		total = len(lines)
		if fl > total:
			return "Error: fromLine {} exceeds file length ({} lines).".format(fl, total)
		if tl > total:
			return "Error: toLine {} exceeds file length ({} lines).".format(tl, total)
		#
		repl = replacement
		if not repl.endswith('\n'):
			repl += '\n'
		#
		new_lines = lines[:fl - 1] + [repl] + lines[tl:]
		#
		try:
			with open(full_path, 'w') as f:
				f.writelines(new_lines)
		except Exception as e:
			return "Error writing file: {}".format(e)
		#
		count = tl - fl + 1
		return "Replaced line{} {}-{} in '{}'.".format('s' if count > 1 else '', fl, tl, fileName)
