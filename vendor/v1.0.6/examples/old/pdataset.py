#!/usr/bin/python
# pdataset.py
# pdataset.py by w4d4f4k at gmail dot com
# prepare datasets from text files.
#
# Ex. usage: 
#  python pdataset.py -f data_sentences2.txk -w train_datasets/out -m 100
#    -m 100   # Define max lines per file. File is generated as follows: train_datasets/out_pdataset_0.csv, _1.csv, _2.csv...
#--
import getopt,json,os
from datasets.functions import *
from unidecode import unidecode
#
#from transformers import BertTokenizer
#tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

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
	crc32b('-m'):{ # filename to write to
		'name':'maxLines',
		'short':'-m',
		'long':'--max_lines',
		'accept':True, # accept value
		'value':0, # if 0 then no limit on file length. If defined value ex.: 100 then it create multiple files each one with 100 lines
	},
	crc32b('-N'):{ # filename to write to
		'name':'numerizeVocab',
		'short':'-N',
		'long':'--numerize_vocab',
		'accept':False, #
		'value':False, # True or false
	}
}
#
Stats = {
}
#
Data = []
DataBad = []
#
def NumerizeVocab( fn ):
	global Options, Stats
	print("pdataset.NumerizeVocab() starting {}".format(fn))
	#
	All=[]
	cnt=0
	#
	if fexists(fn)==False:
		return False
	with open( Options[crc32b('-f')]['value'] ) as tf:
		for line in tf:
			line = line.strip()
			print("{} {}".format( line, cnt ))
			cnt+=1

#
def Load( fn ):
	global Options, Stats, Data
	print("pdataset.Load() starting {}".format(fn))
	#
	if fexists(fn)==False:
		return False
	cnt=0
	#
	with open( fn ) as tf:
		for line in tf:
			line  = line.strip() #.replace('"','```')
			words = line.split(" ")
			label = 1
			bad   = False
			for word in words:
				word = unidecode(word)
				if crc32b(word.lower()) in DataBad:
					print("{}.) got bad word: {} -> {}".format( cnt, word, line ))
					bad=True
			if bad:
				label=0
			Data.append( {"text":line.replace('"','```'),"label":label} )
			cnt+=1
#
def LoadBad( fn ):
	global DataBad
	print("pdataset.LoadBad() starting {}".format(fn))
	#
	if fexists(fn)==False:
		return False
	with open( fn ) as tf:
		for line in tf:
			words = line.strip().split(" ")
			for word in words:
				word = unidecode(word.lower())
				if len(word)>=3:
					DataBad.append( crc32b(word) )
#
def Run():
	global Options, Stats, Data, DataBad
	print("pdataset.Run() starting Data.len: {}".format( len(Data) ))
	#
	maxLines=Options[crc32b('-m')]['value'] # None or number
	cnt=0
	cntFile=0
	fn = "" # file name we write into
	#
	for o in Data: # text,label
		label=1
		#
		if cnt==0:
		#	print("text,label")
			if Options[crc32b('-w')]['value']!=None:
				fn = "{}_pdataset_{}.csv".format( Options[crc32b('-w')]['value'], cntFile )
				fwrite(fn,"text,label\n", False)
		#
		#print("\"{}\",{}".format( o['text'], o['label'] ))
		#
		if Options[crc32b('-w')]['value']!=None:
			fwrite(fn,"\"{}\",{}\n".format( o['text'], o['label'] ), False)
		#
		if maxLines>0 and cnt>=maxLines:
			print("generating new file...")
			cntFile += 1
			cnt = 0
		else:
			cnt+=1

#
def List():
	global Options
	pfn = Options[crc32b('-F')]['value']
	for fn in os.listdir(pfn):
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
	
	#
	if Options[crc32b('-f')]['value']==None and Options[crc32b('-F')]['value']==None:
		print("You should choose file to work on. Options: -f or -F or dont exists.")
		sys.exit(1)
	#
	if Options[crc32b('-N')]['value']:
		print("d1")
		#NumerizeVocab(Options[crc32b('-f')]['value'])
	elif Options[crc32b('-F')]['value']!=None:
		print("d2!")
		#List()
	else:
		#print("d3!")
		LoadBad("bad-slo-words.txt")
		Load(Options[crc32b('-f')]['value'])
		Run()

#
#--
if __name__ == "__main__":
	main(sys.argv[1:])

