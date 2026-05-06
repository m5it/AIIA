import subprocess
import os
import tempfile

class Sed():
	#
	def __init__(self):
		print("Sed() STARTING")
		self.info = {
			"name":"Sed",
			"description":"Stream editor - find and replace text in files using regex. Works on files in work/ directory.",
			"parameters":{
				"returnType":"string",
				"required":["pattern","replacement","fileName"],
				"properties":{
					"pattern":{
						"type":"string", 
						"description":"Regex pattern to search for."
					},
					"replacement":{
						"type":"string", 
						"description":"Replacement text (can include \1, \2 for capture groups)."
					},
					"fileName":{
						"type":"string", 
						"description":"File to edit (in work/)."
					},
					"inplace":{
						"type":"boolean", 
						"description":"(Optional) Edit file in-place. Default: false."
					},
				},
			},
		}
	#
	def run(self, pattern, replacement, fileName, inplace=False, opts={}):
		print("Sed.run() STARTING, pattern: {}, replacement: {}, fileName: {}, inplace: {}".format(pattern, replacement, fileName, inplace))
		#
		# Find file
		file_path = self._find_file(fileName)
		if not file_path:
			return "Error: File {} not found in work/".format(fileName)
		#
		# Build sed command
		# Escape special characters for sed
		sed_pattern = "s/{}/{}/g".format(pattern, replacement)
		cmd = ["sed", sed_pattern, file_path]
		#
		print("Sed.run() executing: {}".format(cmd))
		#
		try:
			if inplace:
				# Edit file in place
				cmd.insert(1, "-i")
				result = subprocess.run(
					cmd,
					capture_output=True,
					text=True,
					timeout=10
				)
				return "File {} edited in-place".format(fileName)
			else:
				# Write to new file in work/
				output_file = "work/{}_sed".format(fileName)
				with open(output_file, 'w') as f:
					result = subprocess.run(
						cmd,
						stdout=f,
						stderr=subprocess.PIPE,
						text=True,
						timeout=10
					)
				return "Output written to {}".format(output_file)
			#
		except subprocess.TimeoutExpired:
			return "Error: Sed execution timed out (10s limit)"
		except Exception as E:
			return "Error executing sed: {}".format(E)
	#
	def _find_file(self, fileName):
		# Check work/ only
		full_path = "work/{}".format(fileName)
		if os.path.exists(full_path):
			return full_path
		return None
