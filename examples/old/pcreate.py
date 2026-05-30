#!/usr/bin/python
#--
#
# Script to create empty model.
# 1.) save model                            ( binary only )
# 2.) save profile                          ( binary + config + vocab... )
#

#--
#
import getopt,json,os
from datasets.functions import *
#
import torch
#from transformers import BertForSequenceClassification, BertTokenizer
from transformers import BertForMaskedLM, BertTokenizer, BertConfig, BertModel
import pandas as pd
import numpy as np

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

#--
#
def Run():
	print("Run() START!")
	#--
	# Create a tokenizer instance
	config = BertConfig.from_json_file('bert-base-uncased/config.json')
	model  = BertModel(config=config)
	
	# Load existing model and continue editing/modifiing it...
	tmp    = torch.load('bert-base-uncased/bert-base-uncased_myvocab1.pth',weights_only=False)
	model.load_state_dict(tmp)
	model.save_pretrained('myllm/')
	torch.save(model.state_dict(), 'myllm/my-bert-model.bin')

#
def main(argv):
	print("main() START!")
	global Options,Stats
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
	#
	if opt_help:
		print("HElp!")
		Options[crc32b('-h')]['exec']()
		sys.exit(1)
	print(Options)
	
	#...
	#if Options[crc32b('-f')]['value']=="":
	#	print("Required -f to define file where to read from...")
	#	sys.exit(1)
	
	#
	Run()

#
#--
if __name__ == "__main__":
	main(sys.argv[1:])

