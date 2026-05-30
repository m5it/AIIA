#!/usr/bin/python
import readline
import atexit
import os

def c():
	print("completer...")
	readline.insert_text("test...")

print("Testing readline...: ")
f = "somefile.txt"
try:
	#readline.insert_text("abc")
	#tmp = input()
	#tmp = sys.stdin.readline()
	readline.read_history_file(f)
	readline.set_pre_input_hook(c)
	#print("tmp1: {}".format(tmp))
	#sys.stdin.readline.insert_text( tmp )
	#tmp = sys.stdin.readline()
	#print("tmp2: {}".format(tmp))
except Exception as E:
	print("FAIL: {}".format(E))

atexit.register(readline.write_history_file,f)
while True:
	tmp = input()
	print("tmp1: {}".format(tmp))
