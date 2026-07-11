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
				},
			},
		}
	#
	def run(self, fileName, max_chars='50000'):
		print("ReadFile.run() STARTING on name: {}".format(fileName))
		try:
			max_chars = int(max_chars)
		except (ValueError, TypeError):
			max_chars = 50000
		if max_chars <= 0:
			max_chars = 50000

		# Resolve path: try workin/ first, then literal path
		path = "workin/{}".format(fileName)
		if not os.path.exists(path):
			path = "{}".format(fileName)
			if not os.path.exists(path):
				return "Error: File `{}` not found (checked workin/ and CWD)".format(fileName)
		
		data = fread(path)
		if data is False or data is None:
			return "Error: Failed to read file {}".format(fileName)
		
		if len(data) > max_chars:
			# Truncate at last newline before max_chars to keep whole lines
			truncated = data[:max_chars]
			last_nl = truncated.rfind('\n')
			if last_nl > 0:
				truncated = truncated[:last_nl]
			remaining = len(data) - len(truncated)
			return ("{}\n\n[-- File truncated: {} chars remaining ({:.1f}%). "
				"Use <ReadFile><fileName>{}</fileName><max_chars>{}</max_chars></ReadFile> "
				"to read further. --]").format(
					truncated, remaining, 100.0 * remaining / len(data), fileName, min(remaining, max_chars))
		return data
		
