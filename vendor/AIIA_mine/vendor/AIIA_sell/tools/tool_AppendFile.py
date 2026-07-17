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
						"description":"Line number to insert at. 0=prepend at start, -1 or omitted=append at end, positive=insert at that line."
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
			
			if fromLineNumber is None or fromLineNumber == -1:
				if lines:
					if lines[-1] == '':
						lines.append(contentOfFile)
					else:
						lines.append(contentOfFile)
				else:
					lines.append(contentOfFile)
			elif fromLineNumber == 0:
				if lines and lines[-1] == '':
					pass
				else:
					lines.append('')
				lines.insert(0, contentOfFile)
			else:
				pos = max(0, min(fromLineNumber, len(lines)))
				lines.insert(pos, contentOfFile)
			
			content = '\n'.join(lines)
			if not content.endswith('\n') and (lines and lines[-1] != ''):
				content += '\n'
			
			fwrite(file_path, content, False)
		except Exception as E:
			print("AppendFile.run() ERROR: {}".format(E))
			return "Error: {}".format(E)
		return "{} was updated with length {} at position {}".format(fileName, len(contentOfFile), fromLineNumber)