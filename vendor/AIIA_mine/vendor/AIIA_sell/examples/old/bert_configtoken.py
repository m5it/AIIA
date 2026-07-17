from transformers import BertConfig, BertForMaskedLM
from tokenizers.implementations import ByteLevelBPETokenizer
from tokenizers.processors import BertProcessing
from transformers import AutoTokenizer
from datasets import Dataset
import pandas as pd
import numpy as np
#load base tokenizer to train on dataset
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
# convert pandas dataset to HF dataset
df      = pd.read_csv("train_datasets/sen_wac.csv", encoding='utf-8', on_bad_lines='skip', engine='python')
#dataset = Dataset.from_pandas(df.rename(columns={"comment":'text'}))
dataset = Dataset.from_pandas(df)

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
    dataset[i : i + 1000]["text"]
    for i in range(0, len(dataset), 1000)
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
	subword_view = [tokenizer.convert_ids_to_tokens(id) for id in input_ids]
	print("np.array: {}".format( np.array(subword_view) ))
	cnt+=1
#
#print("Test Done! Saving tokens...")
#tokenizer.save_pretrained('myllm1')
#print("Saving tokens done.")
