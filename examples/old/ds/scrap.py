#!/usr/bin/python
#
# Ex.: 
#  python scrap.py -I config_slo_wikipedia
#
import getopt,json,time
import copy,subprocess
from pyquery import PyQuery as pq
from functions import *

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import selenium.webdriver.support.ui as ui

#--
# global vars that are created in separated file. Ex.: config_slo_ringaraja.py
C=None # or {}
TMPC={} # clone of C
G=None # or {}
D=[]   # Done urls in crc32b
A=[]
cnt=0
opt_stopOnCnt   = None
opt_linePerStat = 100
#
drv=None # selenium driver handle. if js required
#
S={
	'chk_exists':0,
	'max_exists':300,
}
#--
#
def save():
	global G, opt_linePerStat
	print("saveS() STARtinG")
	s={}
	a={}
	c=0
	n=0
	#
	if 'stats' in G:
		s = G['stats']
	print("saveS() DEBug stats {}".format(G['stats']))
	#
	for stat in s:
		#
		a[stat] = s[stat]
		c+=1
		#
		if c>opt_linePerStat:
			print("Saving stats...: {}".format(n))
			n+=1
			fwrite("{}stats_{}_{}.txk".format(G['dir'],n,c),json.dumps(a),True)
			a={}
			c=0
	c+=1
	if bool(a):
		fwrite("{}stats_{}_{}.txk".format(G['dir'],n,c),json.dumps(a),True)
#
def gethtml(url):
	args=['node','scrap.js','-u',url]
	print("gethtml start using args: {}".format(args))
	# node scrap.js -u https://www.google.com
	# Open a process
	process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	# Retrieve the output
	stdout, stderr = process.communicate()
	print("gethtml() len: {}, stderr: {}".format(len(stdout),stderr))
	return stdout
def gethtml1(url):
	global drv
	foptions = Options()
	#foptions.add_argument("--headless")
	first=False
	if drv==None:
		#drv = webdriver.Firefox()
		drv = webdriver.Chrome(options=foptions)
		first=True
	html = drv.get(url)
	print("Test => Title: {}".format(drv.title))
	if first:
		time.sleep(20)
	time.sleep(10)
	html = drv.find_element(By.CSS_SELECTOR,"html")
	return html.get_attribute('outerHTML')

#
def loadExistingFileNames():
	global G,D
	#urlfile = "{}.txk".format(crc32b(url))
	#urlfp   = "{}{}".format(G['dir'],urlfile)
	for fl in os.listdir( G['dir'] ):
		print("fl: {}".format(fl))
		if rmatch(fl,".*stats.*"):
			continue
		a=fl.split(".")
		#crc=crc32b(a[0])
		D.append( a[0] )

# Scrap method by t3ch - grandekos
def loopC(C=None, URL=None):
	global A,G,D,cnt,opt_stopOnCnt,S,TMPC
	#
	a = URL.split("#")
	URL = a[0]
	crcurl = crc32b( URL.strip().lower() )
	if crcurl in D:
		print("loopC() SKIP START {} - {} on url: {}".format(len(D), crcurl, URL))
		S['chk_exists']+=1
		if S['chk_exists']>S['max_exists']:
			print("Too much exists... Exiting...")
			return False
		return False
	S['chk_exists']=0
	#
	if opt_stopOnCnt!=None and cnt>=opt_stopOnCnt:
		print("loopC() DONE by opt_stopOnCnt: {}".format(opt_stopOnCnt))
		return False
	print("loopC() {} / STARTING, url: {}".format(len(D),URL))
	print("loopC() DEBUG C: {}".format(C))
	#
	tmpc = C if C is not None else {}
	# load html only
	#text = get_source(URL)
	
	# load with nodejs
	#text = gethtml( urlencode(URL) )
	
	# load with selenium driver
	text = gethtml1( URL )
	#print(text)
	if text[0]=='3' and text[1]=='0' and text[2]=='1' and text[3]==':':
		print("Redirect...: {}".format(text))
		text = gethtml(text.split(":",1)[1].strip())
	elif text[0]=='4' and text[1]=='0' and text[2]=='0':
		print("Error...")
		return False
	text = text.encode('utf-8').decode('utf-8')
	#
	c    = []
	D.append(crcurl)
	#
	for o in tmpc:
		# css, get_attr, get_text, get_if_match, continue_if_match, action, continue
		d = pq(text)
		print("{}./{}) in o..., using css: {}, html len: {}".format( cnt, len(A), o['css'], len(text) ))
		#
		for item in d(o['css']).items():
			#print("debug item: {}".format(item))
			data = ""
			if "get_attr" in o:
				data = item.attr[o['get_attr']]
			elif "get_text" in o:
				data = item.text()
			elif "get_html" in o:
				data = item.html()
			#
			if data=="" or data==None:
				continue
			#
			if "get_check_http" in o and o["get_check_http"]:
				#print("get_check_http old data: {}".format(data))
				if rmatch(data,"^http.*")==False:
					data = "{}{}".format(G['url'],data)
					#print("get_check_http new data: {}".format(data))
			#
			if rmatch(data,"^http.*") and crc32b(data) in D:
				continue
			#
			if "continue_if_match" in o and rmatch(data,o['continue_if_match']):
				continue
			#
			if "get_if_match" in o and rmatch(data,o['get_if_match'])==False:
				print("get_if_match.. skipping data: {}".format(data))
				continue
			#
			if "action" in o:
				o['action'](G,URL,data)
			elif "continue" in o:
				if data not in A:
					#print("Appending {}.) {} -> {}".format(len(A),len(data),data))
					A.append(data)
			#
			if "loop" in o:
				#print("LOOP STARTing!, TMPC: {} vs C: {}".format(TMPC,C))
				loopC(TMPC,URL)
		#
		if "continue" in o:
			c = o['continue']
			#print("while(A) STARTING, c: {}".format(c))
			#
			while len(A):
				data = A.pop()
				#print("while(A) data({}): {}".format(len(A),data))
				if crc32b(data) in D:
					#print("while(A) skipping same url...: {}".format(data))
					continue
				print("c: {}, tmpurl: {}".format(c,data))
				loopC(c,data)
		#
		cnt+=1
	return True

#--
def main(argv):
	global C,G,opt_stopOnCnt,opt_linePerStat,TMPC,drv
	opt_help = False
	#
	try:
		opts, args = getopt.getopt(argv,"vhI:s:l:",["--version","--help","--import_config","--stop_cnt","--max_line_stat"])
	except getopt.GetoptError:
		opt_help = True
	#
	for opt, arg in opts:
		if opt=="-h":
			opt_help = True
		elif opt=="-v":
			print("Version: xxx")
			sys.exit(1)
		#
		if opt=="-I":
			m = importmodule(arg)
			C = getattr(m,"C")
			G = getattr(m,"G")
			TMPC = copy.deepcopy(C)
		#
		if opt=="-s":
			opt_stopOnCnt = int(arg)
		#
		if opt=="-l":
			opt_linePerStat = int(arg)
	#
	if C==None or G==None:
		print("ERROR: config file should be defined with global variables: G and C")
		sys.exit(1)
	#
	if opt_help:
		print("HELP display!")
		sys.exit(1)
	#tmp = gethtml("https://sl.wikipedia.org/wiki/Glagol")
	#tmp = gethtml( urlencode("https%3A%2F%2Fsl.wikipedia.org%2Fw%2Findex.php%3Ftitle%3D%0APogovor%3ABesedna_vrsta%26action%3Dedit%26redlink%3D1") )
	#tmp = gethtml( "https%3A%2F%2Fsl.wikipedia.org%2Fw%2Findex.php%3Ftitle%3D%0APogovor%3ABesedna_vrsta%26action%3Dedit%26redlink%3D1" )
	#tmp = gethtml( "https%3A%2F%2Fstackoverflow.com%2Fquestions%2F16597358%2Fhow-to-split-a-php-class-to-separate-files" )
	#tmp = gethtml1("https://www.google.com")
	#print("debug {} {}".format(len(tmp),tmp))
	#sys.exit(1)
	#
	starturl = "{}{}".format(G['url'],G['start_query'])
	loadExistingFileNames()
	loopC(C, starturl)
	print("DONE...: ")
	save()
	drv.close()

#--
if __name__ == "__main__":
	main(sys.argv[1:])
