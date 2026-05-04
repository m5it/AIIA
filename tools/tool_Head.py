import os

class Head():
	#
	def __init__(self):
		print("Head() STARTING")
		self.info = {
			"name":"Head",
			"description":"Show the first N lines of a file. Reads from workin/ and workout/.",
			"parameters":{
				"returnType":"string",
				"required":["fileName"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file to read."
					},
					"lines":{
						"type":"integer", 
						"description":"(Optional) Number of lines to show. Default: 10."
					},
				},
			},
		}
	#
	def run(self, fileName, lines=10, opts={}):
		print("Head.run() STARTING, fileName: {}, lines: {}".format(fileName, lines))
		#
		# Find file
		file_path = self._find_file(fileName)
		if not file_path:
			return "Error: File {} not found in workin/ or workout/".format(fileName)
		#
		try:
			with open(file_path, 'r') as f:
				content = f.readlines()
			#
			result = "".join(content[:lines])
			return result if result else "(file is empty)"
			#
		except Exception as E:
			return "Error reading file: {}".format(E)
	#
	def _find_file(self, fileName):
		for prefix in ["workin/", "workout/"]:
			full_path = "{}{}".format(prefix, fileName)
			if os.path.exists(full_path):
				return full_path
		return None
