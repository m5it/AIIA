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
		opt_hiddenpath  = "" if "hiddenpath" not in opts else opts["hiddenpath"] # ai dont need to know real path
		# Normalize the real path (hiddenpath + visible path) and the visible path
		# so entry paths are never concatenated without a separator.
		visible_path = path if path and path != "." else ""
		real_path = opt_hiddenpath if opt_hiddenpath else visible_path
		if opt_hiddenpath and visible_path:
			real_path = os.path.join(opt_hiddenpath, visible_path)
		if not real_path:
			real_path = "."
		ret             = {}
		print("List.run() real_path: {}, visible_path: {}".format(real_path, visible_path))
		#
		for n in os.listdir( real_path ):
			#print("List.run() DEBUG n: {}".format(n))
			#
			if opt_match != None:
				if rmatch(n,opt_match)==False:
					continue
			#
			rfp = os.path.join(real_path, n)
			ffp = os.path.join(visible_path, n) if visible_path else n
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
