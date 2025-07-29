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
			x = fwrite("workout/{}".format(fileName), contentOfFile, True)
		except Exception as E:
			print("WriteFile.run() ERROR: {}".format(E))
			return "Error occured: {}".format(E)
		return "{} was created with length {}".format( fileName, len(contentOfFile) )
