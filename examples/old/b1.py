import readline # Enables input line editing
#from pathlib import Path

import lmstudio as lms
import json, sys, time, os
#
Options = {
	'modules_path':'mods',
}
#
def read_file(name:str):
	print("read_file() STARTING on {}".format(name))
	#
	if not os.path.exists( "{}".format( name ) ):
		print("read_file() name dont exists {}".format(name))
		return False
	#
	res  = open( "{}".format( name ), "r").read()
	return res


#
def print_fragment(fragment, round_index=0):
    # .act() supplies the round index as the second parameter
    # Setting a default value means the callback is also
    # compatible with .complete() and .respond().
    print(fragment.content, end="", flush=True)

#-- importmodule(...)
#
def importmodule(text, rel=True):
	global Options
	#
	name   = "{}.{}".format(Options["modules_path"], text)
	exists = False
	mod    = None
	print("importmodule on name: {}".format(name))
	#
	try:
		# check if module already loaded, then reload
		if name in sys.modules:
			plog("importmodule() name exists in sys.modules {}".format(name))
			exists = True
		#
		mod = importlib.import_module( name )
		#
		if exists and rel:
			mod = importlib.reload( mod )
	except Exception as E:
		print("importmodule() name: {}, Failed {}".format(name, E))
		return False
	return mod

#model = lms.llm()
model = lms.llm("llama-3.2-3b-instruct")
#model = lms.llm("llama-3.2-1b-instruct")
#model = lms.llm("hermes-3-llama-3.2-3b")
#model = lms.llm("deepseek-r1-distill-qwen-7b")
#model = lms.llm("yi-coder-9b-chat")
aiwork = read_file("aiwork/add_ads.php")
#
#chat = lms.Chat("You are a task focused AI assistant")
chat = lms.Chat("Fix php code. First remove function `GetSQLValueString` and convert mysql to mysqli")

#while True:
try:
	#user_input = input("You (leave blank to exit): ")
	#user_input = "Please create a file named output.txt with your understanding of the meaning of life."
	user_input = aiwork
except EOFError:
	print("user_input failed.")
	#break
#if not user_input:
#	break
print("aiwork len: {}".format( len(aiwork) ))
chat.add_user_message(user_input)
prediction_stream = model.respond_stream(
	chat,
	on_message=chat.append,
)
print("Bot: ", end="", flush=True)
for fragment in prediction_stream:
	print(fragment.content, end="", flush=True)

#print("Bot: ", end="", flush=True)
#model.act(
#    chat,
#    [create_file],
#    on_message=chat.append,
#    on_prediction_fragment=print_fragment,
#)
print()
