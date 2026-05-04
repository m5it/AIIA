import subprocess
import os

class Find():
	#
	def __init__(self):
		print("Find() STARTING")
		self.info = {
			"name":"Find",
			"description":"Find files by name pattern. Searches in workin/ and workout/ directories.",
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
						"description":"(Optional) Specific path to search. Default: both workin/ and workout/."
					},
				},
			},
		}
	#
	def run(self, pattern, path="", opts={}):
		print("Find.run() STARTING, pattern: {}, path: {}".format(pattern, path))
		#
		results = []
		#
		# Determine search paths
		search_paths = []
		if path:
			if os.path.exists("workin/{}".format(path)):
				search_paths.append("workin/{}".format(path))
			elif os.path.exists("workout/{}".format(path)):
				search_paths.append("workout/{}".format(path))
			else:
				search_paths.append(path)
		else:
			search_paths = ["workin/", "workout/"]
		#
		# Use find command
		for sp in search_paths:
			try:
				result = subprocess.run(
					["find", sp, "-name", pattern, "-type", "f"],
					capture_output=True,
					text=True,
					timeout=10
				)
				if result.stdout:
					results.extend(result.stdout.strip().split('\n'))
			except Exception as E:
				print("Find.run() error on {}: {}".format(sp, E))
		#
		if not results:
			return "No files found matching pattern: {}".format(pattern)
		#
		return "\n".join(results)
