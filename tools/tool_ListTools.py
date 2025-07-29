#from os import listdir
import os,sys
from src.functions import crc32b,rmatch,importmodule,initmodule
from tools.tool_List import List
#
class ListTools():
	#
	def __init__(self):
		#print("ListTools() STARTING")
		self.info = {
			"name":"listTools",
			"description":"Display available tools.",
			"parameters":{
				"returnType":"object",
				"required":[],
			},
		}
	#
	def run(self):
		print("ListTools.run() STARTING")
		ret = []
		tmpret = List().run("tools/",{'hiddenpath':'', 'match':'^tool\_.*.py'})
		for tool in tmpret:
			#print("ListTools debug key: {}, tool: {}".format( tool, tmpret[tool] ) )
			# debug key: ed02c45b, tool: {'type': 'file', 'fullpath': 'tools/tool_WriteFile.py', 'nodename': 'tool_WriteFile.py', 'name': 'tool_WriteFile', 'extension': 'py'}
			# attach tool name to object
			h=None
			a = tmpret[tool]['name'].split('_')
			if a[1] in sys.modules:
				print("DEbug ListTools.run() {} is loaded!".format(a[1]))
				h = initmodule(importmodule(tmpret[tool]['name'],True,{'path':'tools'}),a[1])
			else:
				print("DEbug ListTools.run() loading {}...".format(a[1]))
				h = initmodule(importmodule(tmpret[tool]['name'],True,{'path':'tools'}),a[1])
			ret.append( {'toolName':h.info['name'], 'toolInfo':h.info, } )
			del(h)
		return ret
