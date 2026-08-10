import os
from src.functions import fread, fwrite
#
class AppendFile():
	#
	def __init__(self):
		print("AppendFile() STARTING")
		self.info = {
			"name":"AppendFile",
			"description":"Create if missing and Append text to a file, or insert at specific line.",
			"parameters":{
				"returnType":"string",
				"required":["fileName","contentOfFile"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of file into which we are writing."
					},
					"contentOfFile":{
						"type":"string", 
						"description":"Content that we have generated and will save into file with specific filename."
					},
				"fromLineNumber":{
					"type":"integer", 
					"description":"Insert after this 1-indexed line number. 0 = before the first line, N = after line N (use the line numbers shown by ReadFile with <lineNumbers>true</lineNumbers>), -1 or omitted = append at the end."
				},
				},
			},
		}
	#
	def run(self, fileName, contentOfFile, fromLineNumber=None):
		print("AppendFile.run() STARTING, {}, len: {}, fromLineNumber: {}".format(fileName, len(contentOfFile), fromLineNumber))
		if fromLineNumber is not None:
			try:
				fromLineNumber = int(fromLineNumber)
			except (ValueError, TypeError):
				fromLineNumber = -1
		try:
			file_path = fileName
			
			parent_dir = os.path.dirname(file_path)
			if parent_dir and not os.path.exists(parent_dir):
				os.makedirs(parent_dir, exist_ok=True)
			
			lines = []
			if os.path.exists(file_path):
				lines = fread(file_path).split('\n')
				# split('\n') on a file ending with a newline produces an extra
				# empty string at the end. That is not a real line; drop it so
				# we don't insert content before that trailing newline.
				if lines and lines[-1] == '':
					lines.pop()
			
			if fromLineNumber is None or fromLineNumber == -1:
				lines.append(contentOfFile)
			elif fromLineNumber == 0:
				lines.insert(0, contentOfFile)
			else:
				# fromLineNumber is 1-indexed: insert after that line.
				# Python list.insert(pos) inserts before the element at index pos,
				# so fromLineNumber=N inserts after line N (1-indexed).
				pos = max(0, min(fromLineNumber, len(lines)))
				lines.insert(pos, contentOfFile)
			
			content = '\n'.join(lines)
			if not content.endswith('\n'):
				content += '\n'
			
			fwrite(file_path, content, True)
		except Exception as E:
			print("AppendFile.run() ERROR: {}".format(E))
			return "Error: {}".format(E)
		return "{} was updated with length {} at position {}".format(fileName, len(contentOfFile), fromLineNumber)