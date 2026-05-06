#from os import listdir
import os
from src.functions import fwrite
#
class WriteFile():
	#
	def __init__(self):
		print("WriteFile() STARTING")
		self.info = {
			"name":"WriteFile",
			"description":"Create if missing and Write or overwrite text to a file.",
			"parameters":{
				"returnType":"string",
				"required":["fileName","contentOfFile"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file into which we are writing."
					},
					"contentOfFile":{
						"type":"string", 
						"description":"Content that we have generated and will save into file with specific filename."
					},
				},
			},
		}
	#
	def run(self, fileName, contentOfFile, opts={}):
		print("WriteFile.run() STARTING, {}, len: {}, opts: {}".format( fileName, len(contentOfFile), opts))
		ret=""
		try:
			# Create parent directories if they don't exist
			import os
			full_path = "work/{}".format(fileName)
			parent_dir = os.path.dirname(full_path)
			if parent_dir and not os.path.exists(parent_dir):
				os.makedirs(parent_dir, exist_ok=True)
				print("WriteFile.run() Created directory: {}".format(parent_dir))
			#
			x = fwrite(full_path, contentOfFile, True)
		except Exception as E:
			print("WriteFile.run() ERROR: {}".format(E))
			return "Error occured: {}".format(E)
		return "{} was created with length {}".format( fileName, len(contentOfFile) )
