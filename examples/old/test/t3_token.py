import torchtext
from torchtext.data import get_tokenizer

# Create a tokenizer
tokenizer = get_tokenizer("spacy")

# Tokenize the text
text = "This is a pytorch tutorial for tokenization!"
tokens = tokenizer(text)

# Create a vocabulary that maps each token to its index
vocab = {}
for i, token in enumerate(tokens):
    vocab[token] = i

# Use the vocabulary to get the input IDs
input_ids = [vocab[token] for token in tokens]

print("Tokens:", tokens)
print("Input IDs:", input_ids)
