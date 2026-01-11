import torch
from transformers import BertForQuestionAnswering, BertTokenizer
import pandas as pd
import numpy as np

tokenizer = BertTokenizer.from_pretrained('myllm')
model = BertForQuestionAnswering.from_pretrained('myllm')
input_ids = torch.tensor(tokenizer.encode("Kako si?")).unsqueeze(0)  # Batch size 1
start_positions = torch.tensor([1])
end_positions = torch.tensor([3])
outputs = model(input_ids, start_positions=start_positions, end_positions=end_positions)
print("outputs: {}".format( outputs ))
#loss, start_scores, end_scores = outputs[:2]
#print("loss: {}, start_Scores: {}, end_scores: {}".format( loss, start_scores, end_scores ))
loss = outputs.loss
print("loss: {}".format( loss ))
