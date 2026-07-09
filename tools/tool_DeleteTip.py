import os, shutil
from config import Options

class DeleteTip():
	def __init__(self):
		self.info = {
			"name":"DeleteTip",
			"description":"Delete a tip title and all its entries from model storage.",
			"parameters":{
				"returnType":"string",
				"required":["title"],
				"properties":{
					"title":{
						"type":"string",
						"description":"Title of the tip to delete"
					},
				},
			},
		}
	def run(self, title="", opts={}):
		if not title or not title.strip():
			return "Error: <title> is required and cannot be empty." + self._usage()
		base = Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
		removed = 0
		for s in ['user', 'model']:
			path = os.path.join(base, s, title)
			if os.path.isdir(path):
				shutil.rmtree(path)
				removed += 1
		if removed:
			return "Deleted tip '{}'".format(title)
		return "No tip titled '{}' found.".format(title)
	def _usage(self):
		return "\nUsage:\n<DeleteTip>\n<title>string</title>\n</DeleteTip>"

class deletetip(DeleteTip): pass
