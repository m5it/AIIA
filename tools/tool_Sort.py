import subprocess
import os

class Sort():
	#
	def __init__(self):
		print("Sort() STARTING")
		self.info = {
			"name":"Sort",
			"description":"Sort lines in a file alphabetically or numerically. Reads from  directory.",
			"parameters":{
				"returnType":"string",
				"required":["fileName"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file to sort."
					},
					"numeric":{
						"type":"boolean", 
						"description":"(Optional) Sort numerically. Default: false."
					},
					"reverse":{
						"type":"boolean", 
						"description":"(Optional) Reverse sort order. Default: false."
					},
					"unique":{
						"type":"boolean", 
						"description":"(Optional) Output only unique lines. Default: false."
					},
				},
			},
		}
	#
	def run(self, fileName, numeric=False, reverse=False, unique=False, opts={}):
		print("Sort.run() STARTING, fileName: {}, numeric: {}, reverse: {}, unique: {}".format(fileName, numeric, reverse, unique))
		#
		numeric = str(numeric).lower() == 'true'
		reverse = str(reverse).lower() == 'true'
		unique = str(unique).lower() == 'true'
		#
		# Find file
		file_path = self._find_file(fileName)
		if not file_path:
			return "Error: File {} not found".format(fileName)
		#
		# Build sort command
		cmd = ["sort"]
		if numeric:
			cmd.append("-n")
		if reverse:
			cmd.append("-r")
		if unique:
			cmd.append("-u")
		#
		cmd.append(file_path)
		#
		print("Sort.run() executing: {}".format(cmd))
		#
		try:
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=10
			)
			#
			output = result.stdout if result.stdout else "(no output)"
			if result.stderr:
				output += "\nSTDERR: {}".format(result.stderr)
			#
			return output
			#
		except subprocess.TimeoutExpired:
			return "Error: Sort execution timed out (10s limit)"
		except Exception as E:
			return "Error executing sort: {}".format(E)
	#
	def _find_file(self, fileName):
		full_path = "{}".format(fileName)
		if os.path.exists(full_path):
			return full_path
		return None
