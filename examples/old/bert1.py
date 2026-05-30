import torch
from transformers import BertTokenizer, BertModel

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')
#model.train()
inputs = tokenizer("Your name is AIIA.", return_tensors="pt")
outputs = model(**inputs)
print(outputs)
last_hidden_states = outputs.last_hidden_state
torch.save(model.state_dict(),'bert-base-uncased.pth')
#model.save_pretrained_gguf("dir", tokenizer, quantization_method = "f16")
