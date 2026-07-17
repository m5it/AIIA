#How to use
# You can use this model directly with a pipeline for masked language modeling:
# Limitations and bias
# Even if the training data used for this model could be characterized as fairly neutral, this model can have biased predictions:
# more info on: https://huggingface.co/google-bert/bert-base-uncased

from transformers import pipeline

#--
#
# Create pipeline
#pipe = pipeline("token-classification",model="myllm1")
# Test the model on a sentence
#output = pipe("Zdravo, kako si?")
#print(output)

#anal = pipeline("sentiment-analysis")
#print( anal("Kako si?") )
#unmasker = pipeline('fill-mask', model='bert-base-uncased')
#--
unmasker = pipeline('fill-mask', model='myllm2')
print(unmasker("Zdravo [MASK] si?"))
#--
#pipe = pipeline('question-answering', model='myllm', tokenizer='myllm')
#print("pipe: {}".format( pipe(question="Kako si?",context='Ime mi je Blaz. Sem dobro. Rodil sem se v Mariboru. Star sem 42 let. Kako leta letijo ne mores vrjet...') ))


#pipe = AutoModelForTokenClassification.from_pretrained("myllm")
#tokenizer = AutoTokenizer.from_pretrained("google-bert/bert-base-cased")
#print( pipe("I can't believe you did such a ", do_sample=False) )

#for out in 
#from transformers import pipeline
#unmasker = pipeline('fill-mask', model='bert-base-uncased')
#t2="Hello I'm a [MASK] model."
#print("Ex.2.) using text: {}".format(t2))
#d=unmasker(t2)
#print(d)
