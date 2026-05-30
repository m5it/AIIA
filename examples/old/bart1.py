import torch
from transformers import BartTokenizer, BartModel

tokenizer = BartTokenizer.from_pretrained('bart-base')
model = BartModel.from_pretrained('bart-base')
model.train()
inputs = tokenizer("Your name is AIIA.", return_tensors="pt")
outputs = model(**inputs)
print(outputs)
last_hidden_states = outputs.last_hidden_state
#torch.save(model.state_dict(),'model.h5')
#model.save_pretrained_gguf("dir", tokenizer, quantization_method = "f16")
