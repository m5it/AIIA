import os,sys
from src.functions import fread
from tools.tool_List import List
#
class ReadFile():
	#
	def __init__(self):
		self.info = {
			"name":"ReadFile",
			"description":"Get content of file",
			"parameters":{
				"returnType":"string", # return type
				"required":['fileName'],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file of which we retrive content"
					},
				},
			},
		}
	#
	def run(self, fileName, opts={}):
		print("ReadFile.run() STARTING on name: {}".format(fileName))
		# Try  only
		path = "{}".format(fileName)
		if not os.path.exists(path):
			return "Error: File `{}` not found".format(fileName)
		
		data = fread(path)
		if data==False:
			return "Error: Failed to read file {}".format(fileName)
		return data
		
