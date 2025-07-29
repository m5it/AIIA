import re,os,sys
import zlib
import urllib.parse
import importlib
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
def user_input( opts={} ):
	#
	opt_debug         = opts["debug"] if "debug" in opts else False
	opt_quitWithCTRLX = opts["quit_with_ctrlx"] if "quit_with_ctrlx" in opts else False
	ret=""
	#
	while True:
		#
		char = sys.stdin.read(1)
		#
		if char=="":
			continue
		#
		if opt_debug:
			print("DEBUG user_input() char: {}, ord: {}".format( char, ord(char) ))
		#
		if opt_quitWithCTRLX==False and ord(char)==10:
			#print("DEBUG quit by ENTER!!!")
			break
		elif opt_quitWithCTRLX and ord(char)==24:
			#print("DEBUG quit by quitWitHCTRLD!!!")
			sys.stdin.read(1) # read last empty space
			break
		#
		if char == "\b":  # Backspace character
			if len(ret) > 0:
				ret = ret[:-1]
		#elif char != "\r" and char != "\n":  # Don't print newline characters
		else:
			ret += char
	return ret
#
def crc32b(text):
	return "%x"%(zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF)
#
def urlencode(text):
	return urllib.parse.quote(text, safe="")
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
def fread( filename ):
	#print("fread() STARTING on {}".format(filename))
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
