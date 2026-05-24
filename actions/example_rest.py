#--
#
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
			'rest_host':'https://example.com',
			'rest_path':'/restapi/0.1/index.php',
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
			'request_name':"1",
			'someArgs1'   :"2",
		})
		# Do something with response data !!!
		print("response data: {}".format( r.json() ))
	#
	def Test(self):
		print("Action.Test() START ({})".format(self.name))
