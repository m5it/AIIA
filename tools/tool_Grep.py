import subprocess
import os

class Grep():
	#
	def __init__(self):
		print("Grep() STARTING")
		self.info = {
			"name":"Grep",
			"description":"Search for patterns in files using regex. Searches in workin/ and workout/ directories.",
			"parameters":{
				"returnType":"string",
				"required":["pattern"],
				"properties":{
					"pattern":{
						"type":"string", 
						"description":"Regular expression pattern to search for."
					},
					"fileName":{
						"type":"string", 
						"description":"(Optional) Specific file to search. If not provided, searches all files in workin/ and workout/."
					},
					"recursive":{
						"type":"boolean", 
						"description":"(Optional) Search recursively in subdirectories. Default: false."
					},
				},
			},
		}
	#
	def run(self, pattern, fileName="", recursive=False, opts={}):
		print("Grep.run() STARTING, pattern: {}, fileName: {}, recursive: {}".format(pattern, fileName, recursive))
		#
		# Build the grep command
		cmd = ["grep", "-n"]  # -n for line numbers
		#
		if recursive:
			cmd.append("-r")
		#
		cmd.append(pattern)
		#
		# Determine which directories/files to search
		search_paths = []
		#
		if fileName:
			# Search in specific file
			if os.path.exists("workin/{}".format(fileName)):
				search_paths.append("workin/{}".format(fileName))
			elif os.path.exists("workout/{}".format(fileName)):
				search_paths.append("workout/{}".format(fileName))
			else:
				return "Error: File {} not found in workin/ or workout/".format(fileName)
		else:
			# Search all files in workin/ and workout/
			search_paths = ["workin/", "workout/"]
		#
		cmd.extend(search_paths)
		#
		print("Grep.run() executing: {}".format(cmd))
		#
		try:
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=10,
				cwd="."
			)
			#
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr and "No such file" in result.stderr:
				output += result.stderr
			#
			if not output:
				return "No matches found for pattern: {}".format(pattern)
			#
			return output
			#
		except subprocess.TimeoutExpired:
			return "Error: Grep execution timed out (10s limit)"
		except Exception as E:
			return "Error executing grep: {}".format(E)
