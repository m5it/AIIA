import getopt,json,os
from ds.functions import *
import torch
#from transformers import BertForSequenceClassification, BertTokenizer
from transformers import BertForMaskedLM, BertTokenizer, BertConfig, BertModel, BertForQuestionAnswering, BertForSequenceClassification
import pandas as pd
import numpy as np
#from transformers import MaskedLMLoss
from random import choices
#
texts  = []
labels = []
model  = None
device = None
tokenizer = None
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
	crc32b('-f'):{ # csv file
		'name':'fileDataset',
		'short':'-f',
		'long':'--file_dataset',
		'accept':True, # accept value
		'value':"",
	},
	crc32b('-b'):{ # binary model file
		'name':'fileBinary',
		'short':'-b',
		'long':'--file_binary',
		'accept':True, # accept value
		'value':"",
	},
	crc32b('-c'):{ # config model
		'name':'fileConfig',
		'short':'-c',
		'long':'--file_config',
		'accept':True, # accept value
		'value':"",
	},
	crc32b('-m'):{ # name of model and directory
		'name':'modelName',
		'short':'-m',
		'long':'--model_name',
		'accept':True, # accept value
		'value':"",
	},
	crc32b('-o'):{ # write out binary
		'name':'writeBinary',
		'short':'-o',
		'long':'--write_binary',
		'accept':True, # accept value
		'value':"",
	}
}

# Preprocess the data by converting text to input ids and attention masks
def preprocess_text(text):
	global tokenizer
	return tokenizer.encode_plus(
		text,
		#add_special_tokens=True,
		#max_length=512,
		#padding='max_length',
		#truncation=True,
		#return_attention_mask=True,
		#return_tensors='pt'
		add_special_tokens=True,
	    max_length=512,
		return_attention_mask=True,
		return_tensors='pt',
		truncation=True
	)

#
def Load():
	global Options, model, texts, labels, device, tokenizer
	#config = BertConfig.from_json_file(Options[crc32b('-c')]['value'])
	#model  = BertModel(config=config)
	#model = BertForQuestionAnswering.from_pretrained('myllm')
	#model = BertForMaskedLM.from_pretrained('myllm')
	tokenizer = BertTokenizer.from_pretrained(Options[crc32b('-m')]['value'])
	#
	# config = BertConfig(
		# hidden_size = 384,
		# vocab_size= tokenizer.vocab_size,
		# num_hidden_layers = 6,
		# num_attention_heads = 6,
		# intermediate_size = 1024,
		# max_position_embeddings = 256
	# )
	# state = torch.load('myllm1/model.pth',weights_only=False)
	#model = BertForMaskedLM(config=config)
	#model = BertForSequenceClassification(config=config)
	# model = BertForSequenceClassification(config=config)
	# model.load_state_dict(state['model'])
	
	model = BertForSequenceClassification.from_pretrained('myllm2')
	#tmp = torch.load(Options[crc32b('-b')]['value'],weights_only=False)
	#model.load_state_dict(tmp)
	print("Loading of model done!")
	print(model.num_parameters()) #10457864
	
	device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
	# Load the dataset (in this case, a CSV file)
	#df     = pd.read_csv(Options[crc32b('-f')]['value'], encoding='utf-8', on_bad_lines='skip', engine='python')
	df     = pd.read_csv(Options[crc32b('-f')]['value'], encoding='utf-8', on_bad_lines='skip')
	texts  = df['text']
	labels = df['label']

#
def Run():
	global Options, model, texts, labels, device, tokenizer
	#
	optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)
	for param in model.parameters():
		param.requires_grad = True
	model.train()
	torch.backends.cudnn.enabled=True
	#
	#for i in range(len(texts)):
	for i in range(0,56):
		j = choices(range(0,len(texts)))[0]
		text   = texts[j]
		labl   = labels[j]
		#text   = texts[i]
		#labl   = labels[i]
		inputs = preprocess_text( text )
		in_ids = inputs['input_ids']
		in_ams = inputs['attention_mask']
		#in_ids = torch.tensor( inputs['input_ids'] )
		#in_ams = torch.tensor( inputs['attention_mask'] )
		
		#
		optimizer.zero_grad()
		#inputs = torch.tensor(tokenizer.encode("Hello, my dog is cute")).unsqueeze(0)  # Batch size 1
		#inputs = torch.tensor(tokenizer.encode( text )).unsqueeze(0)  # Batch size 1
		print("i: {} / {} t( {} ): {}, {} inputs: {}".format( i, len(texts), labl, len(text), text, inputs ))
		output = model(in_ids, attention_mask=in_ams, labels=torch.tensor(labl))
		print("Output keys:", list(output.keys()))
		print("output.shape: {}".format( output ))
		#
		loss = output.loss
		#if loss is not None:
		loss.backward()
		optimizer.step()
		# Print progress
		if loss is not None and i % 100 == 0:
			print(f'Training step {i+1}, loss = {loss.item()}')
	#--
	#
	model.eval()
	#
	with torch.no_grad():
		for i in range(0,56):
			j = choices(range(0,len(texts)))[0]
			text   = texts[j]
			labl   = labels[j]
			inputs = preprocess_text( text )
			#in_ids = torch.tensor( inputs['input_ids'].detach().clone() )
			#in_ams = torch.tensor( inputs['attention_mask'].detach().clone() )
			in_ids = inputs['input_ids']
			in_ams = inputs['attention_mask']
			#inputs = torch.tensor(tokenizer.encode("Hello, my dog is cute")).unsqueeze(0)  # Batch size 1
			#inputs = torch.tensor(tokenizer.encode( text )).unsqueeze(0)  # Batch size 1
			print("i: {} / {} t( {} ): {}, {} inputs: {}".format( i, len(texts), labl, len(text), text, inputs ))
			#output = model(**inputs)
			output = model(in_ids, attention_mask=in_ams, labels=torch.tensor(labl))
			print("Output keys:", list(output.keys()))
			print("output.shape: {}".format( output ))
			#
			#loss = output.loss
			#optimizer.step()
			optimizer.zero_grad()
			# Print progress
			#if loss is not None and i % 100 == 0:
			#print(f'Evaluating step {i+1}, loss = {loss.item()}')
	#
	if Options[crc32b('-o')]['value']!="":
		print("saving...")
		
		model.save_pretrained('myllm2')
		torch.save(model.state_dict(), 'myllm2/model.bin')
		torch.save({
			'model':model.state_dict(),
			#'tokenizer':tokenizer.state_dict(),
		},'myllm2/model.pth')
		#
		tokenizer.save_pretrained('myllm2')
	print("done")

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
	#
	if opt_help:
		print("HElp!")
		Options[crc32b('-h')]['exec']()
		sys.exit(1)
	print(Options)
	#
	if Options[crc32b('-f')]['value']=="" or Options[crc32b('-c')]['value']=="" or Options[crc32b('-b')]['value']=="" or Options[crc32b('-m')]['value']=="":
		print("Required ( -f, -c, -b, -m ) to define file where to read from...")
		sys.exit(1)
	#
	Load()
	Run()

#
if __name__ == "__main__":
	main(sys.argv[1:])

