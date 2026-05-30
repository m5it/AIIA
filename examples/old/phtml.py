#!/usr/bin/python
# phtml.py
# phtml.py by w4d4f4k at gmail dot com
# to use it after scrap.py if html is scrapped not text...
#
# Ex. usage: 
# python phtml.py -F datasets/data/slo/wikipedia/html/ -E ".*stats.*" -w datasets/data/slo/wikipedia/text/
# or to current directory:
# python phtml.py -f datasets/data/slo/wikipedia/html/onefile.txt -E ".*stats.*" -w ""
#--
import getopt,json,os
#from operator import itemgetter
from pyquery import PyQuery as pq
from datasets.functions import *

#
Version = "0.7331.1"
#
def HELP():
	global Options
	print("HELP....\n")
	for k in Options:
		o=Options[k]
		print("{} => {}".format( o['short'], o['name'] ))
#
def VERSION():
	global Version
	print("v{}".format(Version))

#
Options = {
	crc32b('-h'):{
		'name':'help',
		'short':'-h',
		'long':'--help',
		'accept':False, # accept value
		'value':False,
		'exec':HELP,
	},
	crc32b('-v'):{
		'name':'version',
		'short':'-v',
		'long':'--version',
		'accept':False, # accept value
		'value':False,
		'exec':VERSION,
	},
	crc32b('-f'):{
		'name':'fileName',
		'short':'-f',
		'long':'--file_name',
		'accept':True, # accept value
		'value':"",
	},
	crc32b('-F'):{
		'name':'filePath',
		'short':'-F',
		'long':'--file_path',
		'accept':True, # accept value
		'value':None,
	},
	crc32b('-E'):{ # match file to exclude it
		'name':'fileMatchExclude',
		'short':'-E',
		'long':'--exclude_match_file',
		'accept':True, # accept value
		'value':None, # regex
	},
	crc32b('-w'):{ # filename to write to
		'name':'writeToFile',
		'short':'-w',
		'long':'--write_to_file',
		'accept':True, # accept value
		'value':None, # regex
	},
}
#
Stats = {
	'skipped1':[], # special vocabs
	'skipped2':[], # trash
}
#
def Run(fn):
	global Options, Stats
	print("phtml.Run() starting {}".format(fn))
	#
	if fexists(fn)==False:
		return False
	#
	html = fread( fn )
	if html==False:
		return False
	print("html.len: {}".format( len(html) ))
	#
	d = pq( html )
	#text = d.text()
	#
	s1=0
	s2=0
	text=""
	for item in d("*").items():
		s1+=len(item.text())
		for iner in item("p").items():
			#print("iner: {}".format( iner ))
			s2+=len(iner.text())
			text += iner.text()
	#
	if Options[crc32b('-w')]['value']!=None:
		tmpfn="/{}".format(fn)
		nfn = "{}{}".format(Options[crc32b('-w')]['value'],os.path.basename(tmpfn))
		print("len: {} - {} => Writing to {}\n".format( len(text), fn, nfn ))
		if fexists(nfn):
			os.remove(nfn)
		fwrite(nfn,text,False)
	else:
		print("len: {} - {} => Displaying...\n".format( len(text), fn ))
		print( text )
	print("s1: {} vs s2: {}".format(s1,s2))

#
def List():
	global Options
	#print("List() START")
	pfn = Options[crc32b('-F')]['value']
	for fn in os.listdir(pfn):
		#if Options[crc32b('-M')]['value']!=None and rmatch(fn,Options[crc32b('-M')]['value']):
		#	tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
		#	Run(tmpfn)
		if Options[crc32b('-E')]['value']!=None and rmatch(fn,Options[crc32b('-E')]['value'])==False:
			tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
			Run(tmpfn)
		elif Options[crc32b('-E')]['value']==None:
			tmpfn = "{}{}".format(Options[crc32b('-F')]['value'],fn)
			Run(tmpfn)

#
def main(argv):
	global Options
	#
	opt_help=False
	#
	try:
		opts, args = getopt.getopt(argv,genShortArgs(Options),genLongArgs(Options))
		#
		for opt, arg in opts:
			if crc32b(opt) in Options:
				o = Options[crc32b(opt)]
				if 'accept' in o and o['accept']:
					if type(Options[crc32b(opt)]['value']).__name__ == "int":
						Options[crc32b(opt)]['value'] = int(arg)
					else:
						Options[crc32b(opt)]['value'] = arg
				elif "exec" in o:
					o['exec']()
					sys.exit(1)
				else:
					Options[crc32b(opt)]['value'] = True
	except getopt.GetoptError:
		opt_help = True
	if opt_help:
		print("HElp!")
		Options[crc32b('-h')]['exec']()
		sys.exit(1)
	print(Options)
	#...
	#if Options[crc32b('-f')]['value']=="" or fexists(Options[crc32b('-f')]['value'])==False:
	#	print("Required -f to define file where to read from or file dont exists.")
	#	sys.exit(1)
	#
	if Options[crc32b('-f')]['value']==None and Options[crc32b('-F')]['value']==None:
		print("You should choose file to work on. Options: -f or -F or dont exists.")
		sys.exit(1)
	#
	if Options[crc32b('-F')]['value']!=None:
		List()
	else:
		Run(Options[crc32b('-f')]['value'])

#
#--
if __name__ == "__main__":
	main(sys.argv[1:])

