import getopt,json,os
from datasets.functions import *
import torch
#from transformers import BertForSequenceClassification, BertTokenizer
from transformers import BertForMaskedLM, BertTokenizer, BertConfig, BertModel, BertForQuestionAnswering
import pandas as pd
import numpy as np
#from transformers import MaskedLMLoss

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
	model = BertForQuestionAnswering.from_pretrained('myllm')
	#tmp = torch.load(Options[crc32b('-b')]['value'],weights_only=False)
	#model.load_state_dict(tmp)
	print("Loading of model done!")
	tokenizer = BertTokenizer.from_pretrained(Options[crc32b('-m')]['value'])
	device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
	# Load the dataset (in this case, a CSV file)
	df     = pd.read_csv(Options[crc32b('-f')]['value'], encoding='utf-8', on_bad_lines='skip', engine='python')
	texts  = df['text']
	labels = df['label']

#
def Run():
	global Options, model, texts, labels, device, tokenizer
	#
	optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
	for param in model.parameters():
		param.requires_grad = True
	model.train()
	#
	for i in range(len(texts)):
		text   = texts[i]
		labl   = labels[i]
		inputs = preprocess_text( text )
		#inputs = torch.tensor(tokenizer.encode("Hello, my dog is cute")).unsqueeze(0)  # Batch size 1
		#inputs = torch.tensor(tokenizer.encode( text )).unsqueeze(0)  # Batch size 1
		print("i: {} / {} t( {} ): {}".format( i, len(texts), labl, len(text) ))
		# Move the inputs to the GPU (if available)
		start_positions = torch.tensor([1])
		end_positions = torch.tensor([3])
		output = model(inputs, start_positions=start_positions, end_positions=end_positions)
		#inputs = inputs.to(device)
		# Make a prediction
		#output = model(**inputs)
		
		print("Output keys:", list(output.keys()))
		#print("Last hidden state: {}".format( output['last_hidden_state']) )
		#print("Last hidden shape: {}".format( output['last_hidden_state'].shape ) )
		print("inputs: {}".format( inputs ))
		print("output.shape: {}".format( output ))
		#
		#s1 = output['input_ids'].size(-1)
		#s2 = output['attention_mask'].sum(-1).int().tolist()
		#s1 = inputs['attention_mask'].sum(-1).int().tolist()
		#s2 = inputs['input_ids'].size(-1)
		#print("s1: {}, s2: {}".format( s1, s2 ))
		# Create a custom target tensor for masked language modeling
		#loss = None
		#if 'loss' in output:
		#	loss = output['loss']
		#else:
		#	label = inputs['input_ids'].clone()
		#	label[inputs['attention_mask'] == 0] = -100
		#	print("Prepared label for loss_fn: {}".format( label ))
		#	print("label.shape d1: {}".format( label.shape ))
		#	#loss = torch.nn.CrossEntropyLoss()(output['last_hidden_state'].view(-1, output['last_hidden_state'].size(-1)), label.view(-1))
		#	#loss = torch.nn.CrossEntropyLoss()(output['last_hidden_state'].view(-1, output['last_hidden_state'].size(-1)), label)
		#	#loss = torch.nn.CrossEntropyLoss()(output['last_hidden_state'].view(-1, output['last_hidden_state'].size(-1)), label.view(-1, 1))
		#	#loss = torch.nn.MSELoss()(output['last_hidden_state'].view(-1, output['last_hidden_state'].size(-1)), label)
		#	#label = label.view(-1,2048)
		#	# label.view( seq_len, batch_size )
		#	#label = label.view(1,25,2048)
		#	label = label.unsqueeze(-2)
		#	label = label.view(1,25,2048)
		#	print("label.shape d2: {}".format( label.shape ))
		#	loss = torch.nn.CrossEntropyLoss()( output['last_hidden_state'], label )
		#	print("Got loss: {}".format( loss ))
		#	print("Got label after: {}".format( label ))
		#
		loss = output.loss
		optimizer.zero_grad()
		loss.backward()
		optimizer.step()
		# Print progress
		if i % 100 == 0:
			print(f'Training step {i+1}, loss = {loss.item()}')
	#
	if Options[crc32b('-o')]['value']!="":
		print("saving...")
		model.save_pretrained('{}/'.format( Options[crc32b('-m')]['value'] ))
		torch.save(model.state_dict(), Options[crc32b('-o')]['value'])
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

