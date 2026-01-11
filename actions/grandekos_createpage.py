#--
# Create page on grandekos.com from ASSISTANT specific response trough REST interface.
import os,json
import requests
import urllib.parse

#--
# requests ex.:
# r = requests.post("{}{}".format(arg_host, arg_path),data=event)

#
def urlencode(text):
	return urllib.parse.quote(text, safe="")
#
def fread( filename ):
	#
	if not os.path.exists( "{}".format( filename ) ):
		print("fread() filename dont exists {}".format(filename))
		return False
	#
	res  = open( "{}".format( filename ), "r").read()
	return res
#
def fwrite( filename, data, overwrite=False ):
	f=None
	if os.path.exists( filename )==True and overwrite==True:
		f = open(filename,"w")
		f.seek(0)
		f.truncate()
	elif os.path.exists( filename )==False:
		f = open(filename,"w")
	else:
		f = open(filename,"a")
	f.write("{}".format( data ))
	f.close()

#--
#
class Action():
	# options is object. Required is to set handle of Handle! Ex.: {'handle':self} when in Handle(). self=Handle()
	def __init__(self,opts):
		self.name = (__name__).split(".")[1]
		print("Action().__init__() START ({}), debug dir: {}".format(self.name))
		#
		self.options = {
			#
			'rest_host':'https://grandekos.com',
			'rest_path':'/rest/index.php',
			#
			'history_num':None, # data
			'page_path'  :None,
			'page_name'  :None,
		}
		#
		self.handle = opts['handle'] if 'handle' in opts else None
		#
		self.data   = "" # Data to update or create page with
		print("Action().__init__() DONE ({})".format(self.name))
	
	# save options
	def Save(self, args={}):
		print("Action.Save() START args: {}, name: ({})".format( args, self.name ))
		fwrite("{}.opts".format(self.name),json.dumps(self.options),True)
	
	# load saved options
	def Load(self, args={}):
		print("Action.Load() START args: {}, name ({})".format( args, self.name ))
	
	# list saved options
	def List(self, args={}):
		print("Action.List() START args: {}, name: ({})".format( args, self.name ))
	
	#
	def Exec(self, args={}):
		print("Action.Exec() START ({}), args: {}, self.options: {}".format( self.name, args, self.options ))
		data = self.handle.hHM.msgs[ int(self.options['history_num']) ]
		#data = json.dumps( data )
		data = data['content']
		print("Action.Exec() DEBUG history_num: {} data({}): {}".format( self.options['history_num'], len(data), data ))
		#
		r = requests.post("{}{}".format(self.options['rest_host'], self.options['rest_path']),data={
			'webpages_create_page':"1",
			'path'                  :urlencode(self.options['page_path']),
			'name'                  :urlencode(self.options['page_name']),
			'data'                  :urlencode(data),
		})
		print("Action.Exec() DONE D1({}) r   : {}".format(self.name,r))
		print("Action.Exec() DONE D2({}) json: {}".format(self.name,r.json()))
	#
	def Test(self):
		print("Action.Test() START")
