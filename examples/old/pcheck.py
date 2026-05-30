#!/usr/bin/python
# pcheck.py
# pcheck.py by w4d4f4k at gmail dot com
# to use it after ptext.py
#
# Ex. usage: time python pcheck.py -f out_vocab1_data.txk
#--
import getopt,json,os
from datasets.functions import *
print("pcheck.py starting...")
# start with testing of tokens
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
}
#
Stats = {
	'skipped1':[], # special vocabs
	'skipped2':[], # trash
}
#
def run():
	global Options, Stats
	#
	All=[]
	Skp1=['.*\-.*|.*\-|\-.*','^([0-9]+).*','([0-9]+)']
	Skp2=['.*\=.*|.*\=|\=.*','.*\&.*|.*\&|\&.*','.*http.*']
	#
	with open( Options[crc32b('-f')]['value'] ) as text_file:
		for line in text_file:
			line=line.strip()
			print(line)
			# skip=False
			# if line in Stats['skipped1'] or line in Stats['skipped2']:
				# continue
			# for r in Skp2:
				# if rmatch(line,r) and len(line)>10:
					# Stats['skipped2'].append(line)
					# skip=True
					# break
			# if skip:
				# continue
			# for r in Skp1:
				# if rmatch(line,r):
					# Stats['skipped1'].append(line)
					# skip=True
					# break
			# if skip:
				# continue
			# line=line.replace(".","#")
			# line=line.replace(")","#")
			# line=line.replace("(","#")
			# #line=line.replace("[","#")
			# #line=line.replace("]","#")
			# line=line.replace("{","#")
			# line=line.replace("}","#")
			# line=line.replace("?","#")
			# line=line.replace("=","#")
			# line=line.replace("-","#")
			# line=line.replace("_","#")
			# line=line.replace(":","#")
			# line=line.replace(";","#")
			# line=line.replace("<","#")
			# line=line.replace(">","#")
			# line=line.replace("|","#")
			# a=line.split("/")
			# for l in a:
				# if len(l)>20:
					# continue
				# if rmatch(l,".*\#.*"):
					# continue
				# All.append(l)
				# print(l)
	#
	# print("All.len: {}".format( len(All) ))
	# print("Stats.skipped1: {}".format( len(Stats['skipped1']) ))
	# print("Stats.skipped2: {}".format( len(Stats['skipped2']) ))
	# print("skipped2: ")
	# print(Stats['skipped2'])
	# print("skipped1: ")
	# print(Stats['skipped1'])

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
	if Options[crc32b('-f')]['value']=="":
		print("Required -f to define file where to read from...")
		sys.exit(1)
	#
	run()

#
#--
if __name__ == "__main__":
	main(sys.argv[1:])

