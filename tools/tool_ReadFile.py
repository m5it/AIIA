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
		# Try work/ only
		path = "work/{}".format(fileName)
		if not os.path.exists(path):
			return "Error: File `{}` not found in work/".format(fileName)
		
		data = fread(path)
		if data==False:
			return "Failed retrieving content of file {}".format(fileName)
		return data
		
