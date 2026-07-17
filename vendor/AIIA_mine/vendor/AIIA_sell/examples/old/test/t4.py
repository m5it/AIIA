import sys

user_input = ""

while True:
	char = sys.stdin.read(1)
	print("debug char: {}".format( ord(char) ))
	if char == "\b":  # Backspace character
		if len(user_input) > 0:
			user_input = user_input[:-1]
	elif ord(char)==10:
		print("got data...")
		break
	elif char != "\r" and char != "\n":  # Don't print newline characters
		user_input += char

# Print the final input
print("Final input:", user_input)
