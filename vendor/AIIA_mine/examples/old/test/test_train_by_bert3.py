import torch
from transformers import BertTokenizer, BertModel, BertConfig

# Load the pre-trained BERT model and tokenizer
#tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
tokenizer = BertTokenizer.from_pretrained('myllm')
#model = BertModel.from_pretrained('bert-base-uncased')

# Load your saved model
#state_dict = torch.load('bert-base-uncased/bert-base-uncased_myvocab1.pth', map_location='cuda' if torch.cuda.is_available() else 'cpu')
#state_dict = torch.load('bert-base-uncased/bert-base-uncased_myvocab1.pth', map_location='cuda' if torch.cuda.is_available() else 'cpu', weights_only=False)
#state_dict = torch.load('myllm/model.safetensors', map_location='cpu', weights_only=False)
state_dict = torch.load('myllm/my-bert-model.bin', map_location='cpu', weights_only=False)
#state_dict = torch.load('myllm/bert-base-uncased_myvocab1.pth', map_location='cuda' if torch.cuda.is_available() else 'cpu', weights_only=False)
#
#config = BertConfig.from_json_file('bert-base-uncased/config.json')
config = BertConfig.from_json_file('myllm/config.json')
model  = BertModel(config=config)
model.load_state_dict(state_dict)

# Set the model to evaluation mode (in case it was in training mode before)
model.eval()

# Prepare some sample input
input_text = "Kako si?"
input_ids = tokenizer.encode(input_text, return_tensors="pt")

# Pass the input through the model and get its output
output = model(input_ids)

# Print the output (you can also do other things with it, like compute metrics or visualize it)
print(output.last_hidden_state.shape)
