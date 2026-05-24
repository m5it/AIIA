from pathlib import Path

class CreateFile():
	#
	def __init__(self):
		print("CreateFile() STARTING")
		self.info = {
			"name":"CreateFile",
			"description":"Create a new file with the given name and content. Fails if file already exists.",
			"parameters":{
				"returnType":"string",
				"required":["fileName","contentOfFile"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of the file to create (in  folder)."
					},
					"contentOfFile":{
						"type":"string", 
						"description":"Content to write to the new file."
					},
				},
			},
		}
	#
	def run(self, fileName, contentOfFile, opts={}):
		print("CreateFile.run() STARTING, fileName: {}, content length: {}".format(fileName, len(contentOfFile)))
		dest_path = Path("{}".format(fileName))
		if dest_path.exists():
			return "Error: File {} already exists.".format(fileName)
		try:
			dest_path.parent.mkdir(parents=True, exist_ok=True)
			dest_path.write_text(contentOfFile, encoding="utf-8")
		except Exception as exc:
			return "Error: {}".format(exc)
		return "File {} created successfully.".format(fileName)
