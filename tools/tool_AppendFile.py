import os
from src.functions import fwrite
#
class AppendFile():
	#
	def __init__(self):
		print("AppendFile() STARTING")
		self.info = {
			"name":"AppendFile",
			"description":"Create if missing and Append text to a file.",
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
		print("AppendFile.run() STARTING, {}, len: {}".format( fileName, len(contentOfFile)))
		ret=""
		try:
			# Use work/ directory
			file_path = "work/{}".format(fileName)
			
			# Create parent directories if they don't exist
			parent_dir = os.path.dirname(file_path)
			if parent_dir and not os.path.exists(parent_dir):
				os.makedirs(parent_dir, exist_ok=True)
			
			x = fwrite(file_path, contentOfFile, False)  # False = append mode
		except Exception as E:
			print("AppendFile.run() ERROR: {}".format(E))
			return "Error occured: {}".format(E)
		return "{} was appended with length {}".format( fileName, len(contentOfFile) )
