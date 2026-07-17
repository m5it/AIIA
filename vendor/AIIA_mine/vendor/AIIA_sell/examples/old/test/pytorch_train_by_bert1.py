import torch
from transformers import BertForSequenceClassification, BertTokenizer
import pandas as pd
import numpy as np

# Load the dataset (in this case, a CSV file)
#df = pd.read_csv('data_sentences1.csv', encoding='utf-8', on_bad_lines='skip', engine='python')
df = pd.read_csv('data_sentences2.csv', encoding='utf-8', on_bad_lines='skip', engine='python')
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
train_texts  = df['text'].fillna("").tolist()
train_labels = df['label'].fillna("").tolist()
print("train_texts.len: {}, labels.len: {}".format( len(train_texts), len(train_labels) ))
#
train_inputs = [preprocess_text(text) for text in train_texts]

# Create a dataset class to handle the data
class BERTDataset(torch.utils.data.Dataset):
	#
	def __init__(self, tokens, labels=None):
		self.tokens = tokens # inputs
		if labels is not None:
			self.labels = labels
	#
	def __getitem__(self, idx):
		ott = self.tokens[idx]  # Note: using idx instead of self.cnt
		print("__getitem__() START on idx: {}".format( idx ))
		input_ids      = ott['input_ids'].detach().clone() #torch.tensor(ott['input_ids'])
		attention_mask = ott['attention_mask'].detach().clone() #torch.tensor(ott['attention_mask'])
		
		if 'labels' in self:
			return {
				'input_ids': input_ids,
				'attention_mask': attention_mask,
				'labels': self.labels[idx]
			}
		else:
			return {'input_ids': input_ids, 'attention_mask': attention_mask}
	#
	def __iter__(self):
		return iter(self.tokens)
	#
	def __len__(self):
		return len(self.tokens)

# Create a dataset instance
dataset = BERTDataset(train_inputs, train_labels)

# Create a data loader for the training set
batch_size = 3
train_loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

# Load the pre-trained model
model = BertForSequenceClassification.from_pretrained('bert-base-uncased')
#model.load_state_dict(torch.load('bert-base-uncased/tf_model.h5'))
#model.load_state_dict(torch.load('bert-base-uncased/pytorch_model.bin', map_location='cpu'))

def train(model, device, loader, optimizer):
	print("train() START, loader.len: {}".format( len(loader) ))
	model.train()
	total_loss = 0
	correct    = 0

	for batch in loader:
		input_ids = batch['input_ids'].to(device)
		attention_mask = batch['attention_mask'].to(device)
		labels = batch['labels'].to(device) if 'labels' in batch else None
		output = model(input_ids, attention_mask=attention_mask, labels=labels)
		
		if isinstance(output, tuple):
			loss, logits = output
			labels = batch.get('labels', None)
		else:
			loss = output.loss
			logits = None

		# Backward pass and optimization
		optimizer.zero_grad()
		loss.backward()
		optimizer.step()

		total_loss += loss.item()

		if isinstance(output, tuple):
			_, predicted = torch.max(logits, dim=1)
			correct += (predicted == labels).sum().item()
	#
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
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
#
cnt=0
for epoch in range(5):
	print("last loop...{}".format(cnt))
	loss = train(model, device, train_loader, optimizer)
	print(f'Epoch {epoch+1}, Loss: {loss:.4f}')
	cnt+=1

# Evaluate the model
evaluation_loss = evaluate(model, device, train_loader)
print(f'Evaluation Loss: {evaluation_loss:.4f}')

#print("saving...")
#torch.save(model.state_dict(), 'bert-base-uncased/tf_model1.h5', map_location='cpu')
print("done...")
