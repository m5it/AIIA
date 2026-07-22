#!/usr/bin/python
from transformers import DataCollatorForLanguageModeling
#
import torch,sys
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from accelerate import Accelerator, DistributedType
#
from transformers import Trainer, TrainingArguments
from transformers import BertConfig, BertForMaskedLM
from tokenizers.implementations import ByteLevelBPETokenizer
from tokenizers.processors import BertProcessing
from transformers import AutoTokenizer
from datasets import Dataset
import pandas as pd
import numpy as np
#load base tokenizer to train on dataset
#tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
tokenizer = AutoTokenizer.from_pretrained("myllm1")
# convert pandas dataset to HF dataset
df      = pd.read_csv("train_datasets/sen_wac.csv", encoding='utf-8', on_bad_lines='skip', engine='python')
#dataset = Dataset.from_pandas(df.rename(columns={"comment":'text'}))
dataset = Dataset.from_pandas(df)
train_inputs = df['text'].tolist()
train_labels = df['label'].tolist()
print("column_names: {}".format( dataset.column_names ))
#sys.exit(1)
#
config = BertConfig(
	hidden_size = 384,
	vocab_size= tokenizer.vocab_size,
	num_hidden_layers = 6,
	num_attention_heads = 6,
	intermediate_size = 1024,
	max_position_embeddings = 256
)

model = BertForMaskedLM(config=config)
print(model.num_parameters()) #10457864

# define iterator
training_corpus = (
	dataset[i : i + 10000]["text"]
	for i in range(0, len(dataset), 10000)
)

#train the new tokenizer for dataset
tokenizer = tokenizer.train_new_from_iterator(training_corpus, 100000)
#test trained tokenizer for sample text
#text = dataset['text'][123]
#print(text)
cnt=0
for data in dataset['text']:
	if cnt>=10:
		break
	print("data: {}".format( data ))
	input_ids = tokenizer(data).input_ids
	print("input_ids: {}".format( torch.tensor(input_ids) ))
	subword_view = [tokenizer.convert_ids_to_tokens(id) for id in input_ids]
	print("np.array: {}".format( np.array(subword_view) ))
	cnt+=1

print("Step 2 continuing...")
#
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=True, mlm_probability=0.15)

#
class LineByLineTextDataset(Dataset):
	def __init__(self, tokenizer, raw_datasets, max_length: int):
		self.padding = "max_length"
		self.text_column_name = 'text'
		self.max_length = max_length
		self.accelerator = Accelerator(gradient_accumulation_steps=1)
		self.tokenizer = tokenizer
		#
		with self.accelerator.main_process_first():
			self.tokenized_datasets = raw_datasets.map(
				self.tokenize_function,
				batched=True,
				num_proc=4,
				remove_columns=[self.text_column_name],
				desc="Running tokenizer on dataset line_by_line",
			)
			self.tokenized_datasets.set_format('torch',columns=['input_ids'],dtype=torch.long)
	def tokenize_function(self,examples):
		examples[self.text_column_name] = [
			line for line in examples[self.text_column_name] if len(line[0]) > 0 and not line[0].isspace()
		]
		return self.tokenizer(
			examples[self.text_column_name],
			padding=self.padding,
			truncation=True,
			max_length=self.max_length,
			return_special_tokens_mask=True,
		)
	def __len__(self):
		return len(self.tokenized_datasets)

	def __getitem__(self, i):
		return self.tokenized_datasets[i]

#
#tokenized_dataset_train = LineByLineTextDataset(
#	tokenizer= tokenizer,
#	raw_datasets = dataset,
#	max_length=256,
#)
# Define an input format for user queries (e.g., as strings)
def preprocess_input(query):
	inputs = tokenizer.encode_plus(
		query,
		add_special_tokens=True,
		max_length=256,
		padding='max_length',
		truncation=True,
		return_attention_mask=True,
		return_tensors='pt'
	)
	#input_ids = inputs['input_ids'].flatten().unsqueeze(0)
	#attention_mask = inputs['attention_mask'].flatten().unsqueeze(0)

	# Convert the data to tensors
	#input_ids = torch.tensor(input_ids.unsqueeze(0))
	#input_ids = torch.tensor(input_ids)
	#attention_mask = torch.tensor(attention_mask.unsqueeze(0))
	#attention_mask = torch.tensor(attention_mask)
	#return input_ids, attention_mask
	return inputs

class MyDataset(torch.utils.data.Dataset):
	#def __init__(self, csv_path):
	def __init__(self, dataset):
		print("init START dataset.len: {}".format( len(dataset) ))
		#self.data = pd.read_csv(csv_path)
		self.data = dataset
		#self.features = torch.tensor(self.data.drop('text', axis=1).values.astype(np.float32))
		#self.labels = torch.tensor(self.data['label'].values.astype(np.float32))

	def __len__(self):
		return len(self.data)

	def __getitem__(self, idx):
		print("getitem() start on {}".format( idx ))
		#d = self.features[idx]
		d = self.data[idx][0]
		print("getitem( {} ) d: {}".format( len(d), d ))
		#return self.features[idx], self.labels[idx]
		return d

# Create a dataset class to handle the data
class BERTDataset(torch.utils.data.Dataset):
	#
	def __init__(self, tokens, labels=None):
		self.tokens = tokens # inputs
		self.labels = None
		if labels is not None:
			self.labels = labels
	#
	def __getitem__(self, idx):
		text = self.tokens[idx]
		print("getitem() start on {} ott: {}".format( idx, text ))
		input_ids, attention_mask = preprocess_input( text )
		print("getitem() debug input_ids: {}".format( input_ids ))
		#input_ids      = torch.tensor( self.tokens[idx] )
		#attention_mask = torch.tensor( sel )
		if 'labels' in self:
			return {
				'input_ids'     : input_ids,
				'attention_mask': attention_mask,
				'labels'        : torch.tensor(self.labels[idx])
			}
		else:
			return {'input_ids': input_ids, 'attention_mask': attention_mask}
	#
	def __iter__(self):
		print("__iter__() START!")
		return iter(self.tokens)
	#
	def __len__(self):
		return len(self.tokens)

#train_dataset = BERTDataset(train_inputs[:int(0.8*len(train_inputs))], labels[:int(0.8*len(labels))])
#train_loader  = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
#myDs = MyDataset("train_datasets/sen_wac.csv")
#myDs = MyDataset( df )
batchsize = 12
batches   = []
cntpos    = 0
#
for i in range(1):
	print("i: {}".format( i ))
	batch = []
	for j in range(batchsize):
		print("j: {}".format( j ))
		batch.append( [preprocess_input(train_inputs[cntpos])] )
		cntpos+=1
	batches.append( batch )
#
myDs = MyDataset( batches )
#myDsl = torch.utils.data.DataLoader(myDs, batch_size=12, shuffle=False)

#train_loader = torch.utils.data.DataLoader(training_corpus, batch_size=10, shuffle=False)
# print("myDs.len: {}".format( len(myDs) ))
# print("train_loader.len: {}".format( len(train_loader) ))
# cnt=0
# for tl in train_loader:
	# print("tl: {}".format( tl ))
	# if cnt>=10:
		# break
	# cnt+=1
#sys.exit()
#
training_args = TrainingArguments(
	output_dir="myllm2",
	overwrite_output_dir=True,
	push_to_hub=False,
	#hub_model_id="myllm1",
	num_train_epochs=2,
	per_device_train_batch_size=12,
	save_steps=5_000,
	logging_steps = 1000,
	save_total_limit=2,
	#use_mps_device = True, # disable this if you're running non-mac env
	#hub_private_repo = False, # please set true if you want to save model privetly
	save_safetensors= True,
	learning_rate = 1e-4,
	#report_to='wandb', # t3ch is not supported, only azure_ml, comet_ml, mlflow, neptune, tensorboard, wandb, codecarbon, clearml, dagshub, flyte, dvclive, swanlab are supported.
	use_cpu=True
)

#
trainer = Trainer(
	model=model,
	args=training_args,
	data_collator=data_collator,
	#train_dataset=tokenized_dataset_train
	#train_dataset=train_loader
	train_dataset=myDs
	#train_dataset=training_corpus
)

#
trainer.train()

