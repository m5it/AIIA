import torch
from transformers import BertTokenizer, BertModel
import numpy as np

# Load the saved model and tokenizer
#tokenizer = BertTokenizer.from_pretrained('bert-base-uncased-orig')
tokenizer = BertTokenizer.from_pretrained('myllm2')
#model = BertModel.from_pretrained('bert-base-uncased-orig')
model = BertModel.from_pretrained('myllm2')

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
	input_ids = inputs['input_ids'].flatten()
	attention_mask = inputs['attention_mask'].flatten()

	# Convert the data to tensors
	input_ids = torch.tensor(input_ids.unsqueeze(0))
	attention_mask = torch.tensor(attention_mask.unsqueeze(0))

	return input_ids, attention_mask

# Process user queries through the loaded model
def get_response(model, tokenizer, query):
	inputs, attention_mask = preprocess_input(query)
	outputs = model(inputs, attention_mask=attention_mask)
	last_hidden_state = outputs.last_hidden_state.detach().numpy()

	# Since we're using BERT, extract the first sequence token as the response
	response = np.argmax(last_hidden_state[0], axis=-1)

	return response

# Test your chatbot with a simple query
query = "Torej dobro.?"
response = get_response(model, tokenizer, query)
print("Response:", response)
