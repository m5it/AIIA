import re,os,sys
import zlib
import urllib.parse
import importlib
import requests

#--
#
def genShortArgs(Options):
	#global Options
	ret=""
	for k in Options:
		o = Options[k]
		if "accept" in o and o["accept"]:
			ret = "{}{}:".format(ret,o["short"][1:len(o["short"])])
		else:
			ret = "{}{}".format(ret,o["short"][1:len(o["short"])])
	return ret
#
def genLongArgs(Options):
	#global Options
	ret=[]
	for k in Options:
		o = Options[k]
		ret.append(o['long'])
	return ret

#--
#
def remove_emoji(text):
	emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F"  # emoticons
								u"\U0001F300-\U0001F5FF"  # symbols & pictographs
								u"\U0001F680-\U0001F6FF"  # transport & map symbols
								u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
								u"\U00002702-\U000027B0"
								u"\U000024C2-\U0001F251"
								u"\U0001f926-\U0001f937"
								u"\U00010000-\U0010ffff"
								u"\u2640-\u2642"
								u"\u2600-\u2B55"
								u"\u200d"
								u"\u23cf"
								u"\u23e9"
								u"\u231a"
								u"\ufe0f"
								u"\u3030" "]+", flags=re.UNICODE)
	return emoji_pattern.sub(r'', text)

#--
#
def splitFileNameExtension(text):
	a = text.split(".")
	r = {
		'name'     :'',      # somename
		'extension':'', # php,js...
	}
	if len(a)>=2:
		r['extension'] = a[len(a)-1]
		del(a[len(a)-1])
		r['name'] = "".join(a)
	return r
#
def importmodule(text, rel=True, opts={}):
	path = opts["path"] if "path" in opts else ""
	#
	name   = "{}{}".format("{}.".format(path) if path!="" else "", text)
	exists = False
	mod    = None
	#
	try:
		# check if module already loaded, then reload
		if name in sys.modules:
			exists = True
		#
		mod = importlib.import_module( name )
		#
		if exists and rel:
			mod = importlib.reload( mod )
	except Exception as E:
		print("importmodule() ERROR: name => {}, message => {}".format(name, E))
		return False
	return mod
#
def initmodule(i,n,opts=None):
	a=[]
	try:
		c = getattr(i,n)
		h = None
		if opts!=None:
			h = c( opts )
		else:
			h = c()
		return h
	except Exception as E:
		print("initmodule() ERROR: {}".format(E))
		return False
#
def crc32b(text):
	return "%x"%(zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF)
#
def rmatch(input,regex):
	x = re.match( regex, input )
	if x != None:
		return x
	else:
		return False
#
def pmatch(input,regex):
	ret=[]
	a = re.findall( regex, input, flags=re.IGNORECASE )
	if a is not None:
		if type(a) is list and len(a)>0 and type(a[0]) is tuple:
			a = a[0]
		for v in a:
			ret.append( v )
	return ret
#
def fexists( filename ):
	if os.path.exists( filename ):
		return True
	return False
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
#
def fread( filename ):
	print("fread() STARTING on {}".format(filename))
	#
	if not os.path.exists( "{}".format( filename ) ):
		print("fread() filename dont exists {}".format(filename))
		return False
	#
	res  = open( "{}".format( filename ), "r").read()
	return res

#
def urlencode(text):
	return urllib.parse.quote(text, safe="",encoding='utf-8')
#
def get_source(url):
	r = requests.get(url)
	#text = os.popen("node scrap.js").read()
	return r.text
