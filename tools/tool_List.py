#from os import listdir
import os
from src.functions import crc32b,rmatch,splitFileNameExtension
#
class List():
	#
	def __init__(self):
		print("List() STARTING")
		self.info = {
			"name":"List",
			"description":"List files and directories.",
			"parameters":{
				"returnType":"object",
				"required":[],
				"properties":{
					"path":{
						"type":"string", 
						"description":"(Optional) Set path on which to list files and directories. Path should be a directory!"
					},
				},
			},
		}
	#
	def run(self, path="", opts={}):
		print("List.run() STARTING, path: {}, opts: {}".format( path, opts ))
		opt_match       = None if "match" not in opts else opts["match"] # regex
		opt_hiddenpath  = "workin/" if "hiddenpath" not in opts else opts["hiddenpath"] # ai dont need to know real path
		usepath         = "{}{}".format(opt_hiddenpath,path)
		ret             = {}
		print("List.run() usepath: {}".format( usepath ))
		#
		for n in os.listdir( usepath ):
			#
			if opt_match != None:
				if rmatch(n,opt_match)==False:
					continue
			#
			rfp = "{}{}".format(usepath, n)
			ffp = "{}{}".format(path,n)
			ft  = 'file' if os.path.isfile(rfp) else 'directory'
			#
			nodename = os.path.basename(rfp)
			r        = splitFileNameExtension(nodename)
			ret[crc32b(ffp)] = {
				'type'    :ft, 
				'fullpath':ffp,
				'nodename':nodename,
				'name':r['name'],
				'extension':r['extension'],
			}
		return ret
