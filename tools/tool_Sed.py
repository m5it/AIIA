import subprocess
import os
import difflib
import re as py_re

class Sed():
	#
	def __init__(self):
		print("Sed() STARTING")
		self.info = {
			"name":"Sed",
			"description":"Stream editor - find and replace text in files using regex. Works on files in  directory. Supports PCRE shortcuts (\\d, \\s, \\w) — converted automatically for GNU sed.",
			"parameters":{
				"returnType":"string",
				"required":["pattern","replacement","fileName"],
				"properties":{
					"pattern":{
						"type":"string", 
						"description":"Regex pattern to search for (supports \\d, \\s, \\w shortcuts)."
					},
					"replacement":{
						"type":"string", 
						"description":"Replacement text (can include \\1, \\2 for capture groups)."
					},
					"fileName":{
						"type":"string", 
						"description":"File to edit (in )."
					},
					"inplace":{
						"type":"boolean", 
						"description":"(Optional) Edit file in-place. Default: false."
					},
				},
			},
		}
	#
	@staticmethod
	def _pcre_to_posix(pattern):
		"""Convert PCRE shortcuts (\\\\d, \\\\s, \\\\w) to POSIX ERE equivalents for GNU sed."""
		result = []
		i = 0
		while i < len(pattern):
			if pattern[i] == '\\' and i + 1 < len(pattern):
				nxt = pattern[i + 1]
				if nxt == 'd':
					result.append('[0-9]')
					i += 2
					continue
				elif nxt == 's':
					result.append('[[:space:]]')
					i += 2
					continue
				elif nxt == 'w':
					result.append('[[:alnum:]_]')
					i += 2
					continue
			result.append(pattern[i])
			i += 1
		return ''.join(result)
	#
	def _get_diff(self, before_lines, after_lines):
		"""Return a compact unified diff of changed lines."""
		matcher = difflib.SequenceMatcher(None, before_lines, after_lines)
		result = []
		for tag, i1, i2, j1, j2 in matcher.get_opcodes():
			if tag == 'replace':
				# Show all replaced lines in the block
				for i in range(i1, i2):
					result.append("  -{}".format(before_lines[i].rstrip()))
				for j in range(j1, j2):
					result.append("  +{}".format(after_lines[j].rstrip()))
			elif tag == 'delete':
				for line in before_lines[i1:i2]:
					result.append("  -{}".format(line.rstrip()))
			elif tag == 'insert':
				for line in after_lines[j1:j2]:
					result.append("  +{}".format(line.rstrip()))
		return '\n'.join(result)
	#
	def run(self, pattern, replacement, fileName, inplace=False, opts={}):
		print("Sed.run() STARTING, pattern: {}, replacement: {}, fileName: {}, inplace: {}".format(pattern, replacement, fileName, inplace))
		#
		inplace = str(inplace).lower() == 'true'
		#
		# Find file
		file_path = self._find_file(fileName)
		if not file_path:
			return "Error: File {} not found".format(fileName)
		#
		# Check if raw pattern uses PCRE shortcuts before converting
		has_pcre = bool(py_re.search(r'\\(?:d|s|w|b|D|S|W|B)', pattern))
		# Convert PCRE shortcuts to POSIX for GNU sed
		posix_pattern = self._pcre_to_posix(pattern)
		# Read original content — use raw pattern for Python match counting
		try:
			with open(file_path) as f:
				before_lines = f.readlines()
			before_matches = [l for l in before_lines if py_re.search(pattern, l)]
		except Exception:
			before_lines = []
			before_matches = []
		#
		# If the pattern has no PCRE shortcuts, it's likely a literal search.
		# Escape unescaped parens so they match literally in ERE mode.
		if not has_pcre:
			# Escape `(` and `)` not already preceded by `\`
			posix_pattern = py_re.sub(r'(?<!\\)\(', '\\\\(', posix_pattern)
			posix_pattern = py_re.sub(r'(?<!\\)\)', '\\\\)', posix_pattern)
		#
		# Build sed command (-E for ERE mode)
		sed_pattern = "s|{}|{}|g".format(posix_pattern.replace('|', '\\|'), replacement.replace('|', '\\|'))
		cmd = ["sed", "-E", sed_pattern, file_path]
		#
		print("Sed.run() executing: {}".format(cmd))
		#
		try:
			if inplace:
				cmd.insert(1, "-i")
				result = subprocess.run(
					cmd,
					capture_output=True,
					text=True,
					timeout=10
				)
				# Check for sed errors
				if result.returncode != 0:
					stderr = result.stderr.strip() if result.stderr else 'unknown error'
					return "Error: sed failed (code {}): {}".format(result.returncode, stderr)
				# Read after content for diff
				with open(file_path) as f:
					after_lines = f.readlines()
				diff = self._get_diff(before_lines, after_lines)
				changed = len(before_lines) != len(after_lines) or before_lines != after_lines
				if not changed:
					return "No changes — pattern did not match any line in {}".format(fileName)
				msg = "{} edited ({} match{})\n{}".format(
					fileName,
					len(before_matches),
					'es' if len(before_matches) != 1 else '',
					diff,
				)
				return msg
			else:
				output_file = "{}_sed".format(fileName)
				with open(output_file, 'w') as f:
					result = subprocess.run(
						cmd,
						stdout=f,
						stderr=subprocess.PIPE,
						text=True,
						timeout=10
					)
				if result.returncode != 0:
					stderr = result.stderr.strip() if result.stderr else 'unknown error'
					return "Error: sed failed (code {}): {}".format(result.returncode, stderr)
				return "Output written to {}".format(output_file)
			#
		except subprocess.TimeoutExpired:
			return "Error: Sed execution timed out (10s limit)"
		except Exception as E:
			return "Error executing sed: {}".format(E)
	#
	def _find_file(self, fileName):
		full_path = "{}".format(fileName)
		if os.path.exists(full_path):
			return full_path
		return None
