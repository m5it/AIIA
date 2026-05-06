import subprocess
import os

class Find():
	#
	def __init__(self):
		print("Find() STARTING")
		self.info = {
			"name":"Find",
			"description":"Find files by name pattern. Searches in work/ directory.",
			"parameters":{
				"returnType":"string",
				"required":["pattern"],
				"properties":{
					"pattern":{
						"type":"string", 
						"description":"File name pattern (supports wildcards like *.py, test*)."
					},
					"path":{
						"type":"string", 
						"description":"(Optional) Specific path to search. Default: work/."
					},
				},
			},
		}
	#
	def run(self, pattern, path="", opts={}):
		print("Find.run() STARTING, pattern: {}, path: {}".format(pattern, path))
		#
		results = []
		errors = []
		#
		# Determine search paths
		search_paths = []
		if path:
			# Remove work/ prefix if already present to avoid double prefix
			if path.startswith("work/"):
				full_path = path
			else:
				full_path = "work/{}".format(path)
			search_paths.append(full_path)
		else:
			search_paths = ["work/"]
		#
		# Use find command
		for sp in search_paths:
			try:
				result = subprocess.run(
					["find", sp, "-name", pattern],
					capture_output=True,
					text=True,
					timeout=10
				)
				if result.stdout.strip():
					results.extend(result.stdout.strip().split('\n'))
				if result.stderr:
					errors.append("find error in {}: {}".format(sp, result.stderr.strip()))
			except Exception as E:
				error_msg = "Find.run() error on {}: {}".format(sp, E)
				print(error_msg)
				errors.append(error_msg)
		#
		response = ""
		if results:
			response += "\n".join(results)
		if errors:
			if response:
				response += "\n\nErrors:\n"
			response += "\n".join(errors)
		if not response:
			response = "No files found matching pattern: {}".format(pattern)
		#
		return response
