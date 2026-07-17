#!/usr/bin/python
# pcheck.py
# pcheck.py by w4d4f4k at gmail dot com
# to use it after ptext.py
#
# Ex. usage: time python pcheck.py -f out_vocab1_data.txk
#--
import getopt,json,os
from datasets.functions import *
#
from transformers import BertTokenizer, BertConfig, BertForMaskedLM
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
#
print("ptoken.py starting...")
# start with testing and creating of missing tokens.
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
	cnt=0
	#
	with open( Options[crc32b('-f')]['value'] ) as tf:
		for line in tf:
			line=line.strip()
			#print(line)
			inputs = tokenizer(line, return_tensors='pt')
			a = inputs['input_ids'].tolist()
			if len(a)<0:
				continue
			a=a[0]
			print("{}.) Tokens( {} ): {}".format( cnt, len(a), a ))
			#for ID in a[0]:
			#	if int(ID)==100:
			#		print("{} UNK on line: {}".format( cnt,line ))
			#		b = line.split(" ")
			#		for w in b:
			#			c = pmatch(w,"([\s+|\?|\!|\.|\,|\-|\_]+)")
			#			print("Check word: {} -> {}".format(w,c))
			cnt+=1 # count lines
	

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

