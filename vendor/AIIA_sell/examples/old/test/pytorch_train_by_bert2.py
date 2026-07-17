import torch
from transformers import BertForSequenceClassification, BertTokenizer
import pandas as pd
import numpy as np

# Load the dataset (in this case, a CSV file)
#df = pd.read_csv('data_sentences1.csv', encoding='utf-8', on_bad_lines='skip', engine='python')
df = pd.read_csv('data_sentences3.csv', encoding='utf-8', on_bad_lines='skip', engine='python')
#df = pd.read_csv('data_sentences.csv', encoding='latin1', on_bad_lines='skip')
#df['text'] = df['text'].apply(lambda x: x.encode('utf-8').decode('utf-8'))
#df['text'] = df['text'].fillna("")
# Create a tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Preprocess the data by converting text to input ids and attention masks
def preprocess_text(text):
	return tokenizer.encode_plus(
		text,
		add_special_tokens=True,
		max_length=512,
		padding='max_length',
		truncation=True,
		return_attention_mask=True,
		return_tensors='pt'
	)

# Preprocess the data for the training set
#train_texts  = df['text'].fillna("").tolist()
#train_labels = df['label'].fillna("").tolist()
inputs = df['text']
labels = df['label']
train_inputs = inputs.apply(lambda x: tokenizer.encode_plus(x, 
														   padding='max_length',
														   truncation=True,
														   add_special_tokens=True, 
														   max_length=512, 
														   return_attention_mask=True, 
														   return_tensors='pt'
														   )) #  return_token_type_ids=False
# train_labels = labels.apply(lambda x: tokenizer.encode_plus(x, 
														   # padding='max_length',
														   # truncation=True,
														   # add_special_tokens=True, 
														   # max_length=512, 
														   # return_attention_mask=True, 
														   # return_tensors='pt'))
#print("train_texts.len: {}, labels.len: {}".format( len(train_texts), len(train_labels) ))
#print("train_inputs.len: {}, labels.len: {}, iloc: {}".format( len(train_inputs), len(labels), train_inputs.iloc[0] ))
#
#train_inputs = [preprocess_text(text) for text in train_texts]

class BERTDataset(torch.utils.data.Dataset):
	def __init__(self, inputs_tok, labels):
		self.inputs_tok = inputs_tok
		self.labels = labels

	def __getitem__(self, idx):
		print("__getitem__() START at {}".format(idx))
		input_ids      = self.inputs_tok.iloc[idx]['input_ids'].squeeze(0)  # squeeze to remove batch dimension
		attention_mask = self.inputs_tok.iloc[idx]['attention_mask'].squeeze(0)
		label          = torch.tensor(self.labels.iloc[idx])

		return {
			'input_ids': input_ids,
			'attention_mask': attention_mask,
			'labels': label,
		}

	def __len__(self):
		return len(self.inputs_tok)

batch_size = 1

# Create a dataset instance
#dataset = BERTDataset(train_inputs, labels)
# Create a data loader for the training set
#train_loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)

#
#train_dataset = BERTDataset(train_inputs[:int(0.8*len(train_inputs))], labels[:int(0.8*len(labels))])
#val_dataset   = BERTDataset(train_inputs[int(0.8*len(train_inputs)):], labels[int(0.8*len(labels)):])

#train_loader  = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
#val_loader    = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

# Load the pre-trained model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = BertForSequenceClassification.from_pretrained('bert-base-uncased',num_labels=2)
#model = BertForSequenceClassification.from_pretrained('bert-base-uncased')
cnt1=0
def train(model, device, loader, optimizer):
	global cnt1#,tokenizer
	print("train() START, loader.len: {}".format( len(loader) ))
	model.train()
	total_loss = 0
	correct    = 0

	for batch in loader:
		input_ids = batch['input_ids'].to(device)
		#input_ids = batch['input_ids']
		attention_mask = batch['attention_mask'].to(device)
		labels = batch['labels'].to(device)
		#labels = batch['labels'].to(device) if 'labels' in batch else None
		#input_ids, attention_mask, labels = batch
		#input_ids, attention_mask = batch
		#for i in range(len(input_ids)):
		#cinput_ids = input_ids[i]
		#tmpinputs = torch.unsqueeze(cinput_ids,dim=0)
		#tmpinputs = torch.unsqueeze(cinput_ids,0)
		#tmpinputs1 = torch.tensor(tmpinputs.detach())
		#cattention_mask = attention_mask[i]
		#clabels = labels[i]
		#print("input_ids: {}, type: {}, tmpinputs: {}, 1: {}".format( cinput_ids.shape, type(cinput_ids), tmpinputs.shape, tmpinputs1.shape ))
		#print("train() at {} mask: {}".format( cnt1, cattention_mask ))
		#print("train() at {} labels: {}".format( cnt1, labels ))
		print("train() input_ids.shape: {}".format( input_ids.shape))
		# Forward pass
		output = model(input_ids, attention_mask=attention_mask)
		#output = model(cinput_ids, attention_mask=cattention_mask)
		#output = model(padded_input_ids['input_ids'], attention_mask=padded_input_ids['attention_mask'],labels=labels)
		#output = model(padded_input_ids['input_ids'], attention_mask=padded_input_ids['attention_mask'])
		
		#loss = output.loss
		if output.loss is None:
			print("is none! continuing at {} - {}".format(cnt1,output))
			continue
		loss = output.loss
		print("train() at {} loss: {}".format( cnt1, loss ))
		# Backward pass and optimization
		optimizer.zero_grad()
		loss.backward()
		optimizer.step()

		total_loss += loss.item()
		cnt1+=1
	accuracy = correct / len(loader.dataset) * 100 if loader.dataset else 0
	return {
			'loss': total_loss / len(loader),
			'accuracy': accuracy,
	}

# Define a custom evaluation loop
def evaluate(model, device, loader):
	print("evaluate() START!")
	model.eval()
	with torch.no_grad():
		total_loss = 0
		for batch in loader:
			input_ids = batch['input_ids'].to(device)
			attention_mask = batch['attention_mask'].to(device)

			# Forward pass
			output = model(input_ids, attention_mask=attention_mask)
			loss = output.loss

			total_loss += loss.item()

	return total_loss / len(loader)

# Train the model
optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
cnt=0
for epoch in range(4):
	print("last loop...{}".format(cnt))
	for param in model.parameters():
		param.requires_grad = True
	train_dataset = BERTDataset(train_inputs[:int(0.8*len(train_inputs))], labels[:int(0.8*len(labels))])
	train_loader  = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
	
	loss = train(model, device, train_loader, optimizer)
	#loss = train(model, device, train_inputs, optimizer)
	#print(f'Epoch {epoch+1}, Loss: {loss:.4f}')
	print("loop train: {}".format(loss))
	cnt+=1

# Evaluate the model
#evaluation_loss = evaluate(model, device, train_loader)
#print(f'Evaluation Loss: {evaluation_loss:.4f}')

# saving...
#torch.save(model.state_dict(), 'bert-base-uncased/model1.h5', map_location='cpu')
print("done...")
