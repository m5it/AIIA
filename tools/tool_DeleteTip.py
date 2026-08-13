import os, shutil
from config import Options

def _find_tip_dirs(base, title):
	"""Recursively find all directories named title under the tip base."""
	found = []
	if not os.path.isdir(base):
		return found
	for root, dirs, files in os.walk(base):
		if os.path.basename(root) == title:
			found.append(root)
	return found

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
		for path in _find_tip_dirs(base, title):
			shutil.rmtree(path)
			removed += 1
		if removed:
			return "Deleted tip '{}'".format(title)
		return "No tip titled '{}' found.".format(title)
	def _usage(self):
		return "\nUsage:\n<DeleteTip>\n<title>string</title>\n</DeleteTip>"

class deletetip(DeleteTip): pass
