#--
# View paths on grandekos.com for creating page on specific path.
import os,json
import requests
# requests ex.:
# r = requests.post("{}{}".format(arg_host, arg_path),data=event)
#--
#
class Action():
	# options is object. Required is to set handle of Handle! Ex.: {'handle':self} when in Handle(). self=Handle()
	def __init__(self,opts):
		self.name = "viewpaths"
		print("Action().__init__() START ({})".format(self.name))
		#
		self.options = {
			#
			'rest_host':'https://grandekos.com',
			'rest_path':'/rest/index.php',
			#
			'page_path':'',
		}
		#
		self.handle = opts['handle'] if 'handle' in opts else None
		print("Action().__init__() DONE ({})".format(self.name))
	#
	def Exec(self, args={}):
		print("Action.Exec() START ({}), args: {}, options: {}".format( self.name, args, self.options ))
		#
		r = requests.post("{}{}".format(self.options['rest_host'], self.options['rest_path']),data={
			'webpages_preview_paths':"1",
			'path'                  :self.options['page_path'],
		})
		#print("Action.Exec() D1 ({}), r: {}".format( self.name, r ))
		jsn = r.json()
		#print("Action.Exec() D2 ({}), jsn: {}".format( self.name, jsn ))
		#print("Action.Exec() D3 ({}), jsn['data']: {}".format( self.name, jsn['data'] ))
		n=0
		for obj in jsn['data']:
		#	print("Action.Exec() DEBUG obj: ",obj)
			if 'name' not in obj: # Not active page
				continue
			print("{}.) {} path: {}".format( n, obj['name'], obj['path'] ))
			n+=1
	#
	def Test(self):
		print("Action.Test() START ({})".format(self.name))
