import readline # Enables input line editing
from pathlib import Path

import lmstudio as lms

#
chat=None
model=None
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
def create_file(name: str, content: str):
    """Create a file with the given name and content."""
    dest_path = Path(name)
    if dest_path.exists():
        return "Error: File already exists."
    try:
        dest_path.write_text(content, encoding="utf-8")
    except Exception as exc:
        return "Error: {exc!r}"
    return "File created."

#
def print_fragment(fragment, round_index=0):
    # .act() supplies the round index as the second parameter
    # Setting a default value means the callback is also
    # compatible with .complete() and .respond().
    print(fragment.content, end="", flush=True)

#
def run():
	global chat,model
	#
	main_model_key = "qwen2.5-coder-14b-instruct"
	draft_model_key = "qwen2.5-coder-0.5b-instruct"
	#
	model = lms.llm(main_model_key)
	chat = lms.Chat("You are a task focused AI assistant")
	#
	while True:
	    try:
	        user_input = input("You (leave blank to exit): ")
	        #user_input = "Please create a file named output.txt with your understanding of the meaning of life."
	    except EOFError:
	        print()
	        break
	    #
	    if not user_input:
	        break
	    #
	    chat.add_user_message(user_input)
	    print("Bot: ", end="", flush=True)
	    model.act(
	        chat,
	        [create_file],
	        on_message=chat.append,
	        on_prediction_fragment=print_fragment,
	        config={
		        "draftModel": draft_model_key,
		    }
	    )
	    print()


#
def main(argv):
	run()

#
if __name__ == "__main__":
	main(sys.argv[1:])
