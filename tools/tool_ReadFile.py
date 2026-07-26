import os, sys
from src.functions import fread

class ReadFile():
	#
	def __init__(self):
		self.info = {
			"name":"ReadFile",
			"description":"Read file contents. Prefers files in workin/ directory. Truncates output beyond ~50K chars to keep context manageable.",
			"parameters":{
				"returnType":"string",
				"required":['fileName'],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file to read (checked in workin/ first, then as-is)"
					},
					"max_chars":{
						"type":"string",
						"default":"50000",
						"description":"Max characters to return. Remaining lines truncated with a note."
					},
					"offset":{
						"type":"string",
						"default":"0",
						"description":"Character offset to start reading from. Use to continue reading after truncation."
					},
					"lines":{
						"type":"string",
						"description":"(Optional) Max lines to return. Overrides max_chars if both set."
					},
				},
			},
		}
	#
	def run(self, fileName, max_chars='50000', offset='0', lines=None):
		print("ReadFile.run() STARTING on name: {}".format(fileName))
		try:
			max_chars = int(max_chars)
		except (ValueError, TypeError):
			max_chars = 50000
		if max_chars <= 0:
			max_chars = 50000
		#
		try:
			offset = int(offset)
		except (ValueError, TypeError):
			offset = 0
		if offset < 0:
			offset = 0
		#
		line_limit = None
		if lines is not None:
			try:
				line_limit = int(lines)
			except (ValueError, TypeError):
				line_limit = None

		# Resolve path: try workin/ first, then literal path
		path = "workin/{}".format(fileName)
		if not os.path.exists(path):
			path = "{}".format(fileName)
			if not os.path.exists(path):
				return "Error: File `{}` not found (checked workin/ and CWD)".format(fileName)
		
		data = fread(path)
		if data is False or data is None:
			return "Error: Failed to read file {}".format(fileName)

		total_len = len(data)

		# Apply offset
		if offset > 0:
			if offset >= total_len:
				return "Error: offset {} exceeds file size {} chars".format(offset, total_len)
			data = data[offset:]

		# Line-based reading takes priority over max_chars
		if line_limit is not None:
			split = data.split('\n')
			chunk = '\n'.join(split[:line_limit])
			remaining_lines = len(split) - line_limit
			remaining_chars = len(data) - len(chunk)
			if remaining_lines > 0:
				next_offset = offset + len(chunk)
				return ("{}\n\n[-- Lines truncated: {} lines remaining ({:.1f}%). "
					"Use <ReadFile><fileName>{}</fileName><offset>{}</offset><max_chars>{}</max_chars></ReadFile> "
					"to read further. --]").format(
						chunk, remaining_lines, 100.0 * remaining_lines / len(split),
						fileName, next_offset, min(remaining_chars, max_chars))
			return chunk

		# Char-based reading
		if len(data) > max_chars:
			truncated = data[:max_chars]
			last_nl = truncated.rfind('\n')
			if last_nl > 0:
				truncated = truncated[:last_nl]
			remaining = len(data) - len(truncated)
			next_offset = offset + len(truncated)
			return ("{}\n\n[-- File truncated: {} chars remaining ({:.1f}%). "
				"Use <ReadFile><fileName>{}</fileName><offset>{}</offset><max_chars>{}</max_chars></ReadFile> "
				"to read further. --]").format(
					truncated, remaining, 100.0 * remaining / len(data),
					fileName, next_offset, min(remaining, max_chars))
		return data
		
