# Here is how to use this model to get the features of a given text in PyTorch:
import re
import torch
from transformers import BertTokenizer#, BertModel

#
def pmatch(input,regex):
	ret=[]
	a = re.findall( regex, input, flags=re.IGNORECASE )
	if a is not None:
		if type(a) is list and len(a)>0 and type(a[0]) is tuple:
			a = a[0]
		for v in a:
			ret.append( v )
	return ret

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
#
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

#model = BertModel.from_pretrained("bert-base-uncased")
text = [{"text":"This is a pytorch tutorial for tokenization!","label":1}]
#text="why is this happening?"
#text="Is this a test?"
#text="Kaj si se zbudo?"
#text="Kaj si se zbudil?"
#text="Predmenstrualni sindrom označujejo razdražljivost, anksioznost, emocionalna labilnost, depresija, edem, boleče prsi, sprememba apetita in glavoboli, ki se tipično pojavljajo 7 do 10 dni pred menstrualno krvavitvijo in izginejo nekaj ur preden se menstruacija pojavi. Simptomi so lahko pogosto hudi in vplivajo na kakovost življenja."

#print("using text: {}".format(text))
#inputs = tokenizer(text, return_tensors='pt')
#print("inputs_ids.tolist(): ")
#print(inputs['input_ids'].tolist())

# Define downstream task-specific data and label scheme
#train_data = ...  # load training data for your specific task
#val_data = ...   # load validation data for your specific task
#train_data = [] #[tokenizer(t, return_tensors='pt') for t in text]
#for t in text:
#	train_data.append({})
# Create a custom dataset class for our downstream task
class MyDataset(torch.utils.data.Dataset):
	def __init__(self, data, tokenizer):
		self.data = data
		self.tokenizer = tokenizer

	def __getitem__(self, idx):
		# Tokenize input IDs and attention mask
		inputs = self.tokenizer(self.data[idx]['text'], return_tensors='pt', max_length=512, truncation=True)
		labels = self.data[idx]['label']

		# Get the token names from the vocabulary
		#token_names = {k: v for k, v in self.tokenizer.get_vocab().items()}
		token_names = {}
		for k, v in self.tokenizer.get_vocab().items():
			token_names[v] = k
		# Replace tokens with their corresponding IDs in the input IDs and attention mask tensors
		input_ids = inputs['input_ids'].tolist()[0]
		attention_mask = inputs['attention_mask'].tolist()[0]

		# Convert token names to indices
		#token_names_list = [token_names[token] for token in input_ids]
		token_names_list = []
		for tid in input_ids:
			if tid in token_names:
				token_names_list.append( token_names[tid] )
		#
		return {
			'text': self.data[idx]['text'],
			'labels': labels,
			'input_ids': input_ids,
			'attention_mask': attention_mask,
			'token_names': token_names_list,
		}

	def __len__(self):
		return len(self.data)

# Create an instance of the custom dataset class
dataset = MyDataset(text, tokenizer)

# Print a sample item from the dataset
print(next(iter(dataset)))
