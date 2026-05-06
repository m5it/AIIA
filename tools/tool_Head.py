import os

class Head():
	#
	def __init__(self):
		print("Head() STARTING")
		self.info = {
			"name":"Head",
			"description":"Show the first N lines of a file. Reads from work/ directory.",
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
		# Find file in work/
		file_path = self._find_file(fileName)
		if not file_path:
			return "Error: File {} not found in work/".format(fileName)
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
		full_path = "work/{}".format(fileName)
		if os.path.exists(full_path):
			return full_path
		return None
