import torch
#from transformers import BertTokenizer, BertForSequenceClassification
from transformers import BertTokenizer, BertForMaskedLM, BertConfig, BertModel

# Load the saved model
#model = BertForSequenceClassification.from_pretrained('bert-base-uncased', state_dict=torch.load('bert-base-uncased/tf_model.h5',weights_only=False)) # .h5 or .pth
#model = BertForSequenceClassification.from_pretrained('bert-base-uncased') # .h5 or .pth
#model = BertForMaskedLM.from_pretrained('bert-base-uncased', state_dict=torch.load('bert-base-uncased.pth',weights_only=False)) # .h5 or .pth

config = BertConfig.from_json_file('bert-base-uncased/config.json')
model  = BertModel(config=config)
#model = BertForMaskedLM.from_pretrained('bert-base-uncased') # .h5 or .pth
tmp = torch.load('bert-base-uncased/bert-base-uncased_myvocab.pth',weights_only=False)
model.load_state_dict(tmp)
#tmp = torch.load('bert-base-uncased/tf_model.h5')
#model = BertForMaskedLM.from_pretrained('bert-base-uncased.pth') # .h5 or .pth

# Create a tokenizer instance
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Prepare some input text
#input_text = "hello"
#input_text = "stari"
input_text="Loci vsak dogodek posebej."
# Preprocess the input text
inputs = tokenizer.encode_plus(
    input_text,
    add_special_tokens=True,
    max_length=512,
    return_attention_mask=True,
    return_tensors='pt',
    truncation=True
)

# Move the inputs to the GPU (if available)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
inputs = inputs.to(device)

# Make a prediction
outputs = model(inputs['input_ids'], attention_mask=inputs['attention_mask'])

# Get the predicted class probabilities
#probs = outputs.logits

# Print the predicted class probabilities
print(outputs)
#print(probs)
#torch.save(model.state_dict(), 'bert-base-uncased/bert-base-uncased_myvocab.pth')
#torch.save(model.state_dict(), 'bert-base-uncased/bert-base-uncased_myvocab.bin')
