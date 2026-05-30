import torch
from transformers import BertForSequenceClassification, BertTokenizer
import pandas as pd
import numpy as np

# Load the dataset (in this case, a CSV file)
df = pd.read_csv('done_clanki.csv',encoding='utf-8',on_bad_lines='skip')
df['text'] = df['text'].apply(lambda x: x.encode('utf-8').decode('utf-8'))

# Create a tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Preprocess the data by converting text to input ids and attention masks
def preprocess_text(text):
	print("preprocess_text() STARTING on text(): {}".format(text))
	#print("preprocess_text() STARTING on text({}): {}".format(len(text),text))
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
train_texts  = df['text'].tolist()
train_inputs = [preprocess_text(text) for text in train_texts]

# Create a dataset class to handle the data
class BERTDataset(torch.utils.data.Dataset):
	def __init__(self, inputs, labels=None):
		self.inputs = inputs
		if labels is not None:
			self.labels = labels

	def __getitem__(self, idx):
		input_ids = self.inputs[idx]['input_ids']
		attention_mask = self.inputs[idx]['attention_mask']
		if 'labels' in self:
			return {
				'input_ids': input_ids,
				'attention_mask': attention_mask,
				'labels': self.labels[idx]
			}
		else:
			return {'input_ids': input_ids, 'attention_mask': attention_mask}

	def __len__(self):
		return len(self.inputs)

# Create a dataset instance
dataset = BERTDataset(train_inputs)

# Create a data loader for the training set
batch_size = 32
train_loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

# Load the pre-trained BART model
model = BertForSequenceClassification.from_pretrained('bert-base-uncased')

# Define a custom training loop
def train(model, device, loader, optimizer):
	model.train()
	total_loss = 0
	for batch in loader:
		print("train()...")
		input_ids = batch['input_ids'].to(device)
		attention_mask = batch['attention_mask'].to(device)
		labels = batch['labels'].to(device) if 'labels' in batch else None

		# Forward pass
		output = model(input_ids, attention_mask=attention_mask, labels=labels)
		loss = output.loss

		# Backward pass and optimization
		optimizer.zero_grad()
		loss.backward()
		optimizer.step()

		total_loss += loss.item()

	return total_loss / len(loader)

# Define a custom evaluation loop
def evaluate(model, device, loader):
	model.eval()
	with torch.no_grad():
		total_loss = 0
		for batch in loader:
			print("evaluate() in for...")
			input_ids = batch['input_ids'].to(device)
			attention_mask = batch['attention_mask'].to(device)

			# Forward pass
			output = model.generate(input_ids, attention_mask=attention_mask)
			loss = output.loss

			total_loss += loss.item()

	return total_loss / len(loader)

# Train the model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)

for epoch in range(5):
	print("last loop...")
	loss = train(model, device, train_loader, optimizer)
	print(f'Epoch {epoch+1}, Loss: {loss:.4f}')

# Evaluate the model
evaluation_loss = evaluate(model, device, train_loader)
print(f'Evaluation Loss: {evaluation_loss:.4f}')
print("saving...")
torch.save(model.state_dict(), 'bert-base-uncased/tf_model.h5', map_location='cpu')
print("done...")
