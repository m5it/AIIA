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
		print("AppendFile.run() STARTING, {}, len: {}, opts: {}".format( fileName, len(contentOfFile), opts))
		ret=""
		try:
			x = fwrite("workout/{}".format(fileName), contentOfFile, False)
		except Exception as E:
			print("AppendFile.run() ERROR: {}".format(E))
			return "Error occured: {}".format(E)
		return "{} was appended with length {}".format( fileName, len(contentOfFile) )
