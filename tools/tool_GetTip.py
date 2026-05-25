import os, json
from config import Options

class GetTip():
	def __init__(self):
		self.info = {
			"name":"GetTip",
			"description":"Retrieve saved tip entries by title. Returns all entries saved under that title.",
			"parameters":{
				"returnType":"string",
				"required":["title"],
				"properties":{
					"title":{
						"type":"string",
						"description":"Title of the tip to retrieve"
					},
				},
			},
		}
	def run(self, title="", opts={}):
		if not title or not title.strip():
			return "Error: <title> is required and cannot be empty." + self._usage()
		base = Options.get('TIPS_PATH', os.path.expanduser('~/.config/ourai/tips'))
		combined = []
		for s in ['user', 'model']:
			path = os.path.join(base, s, title)
			if os.path.isdir(path):
				for f in sorted(os.listdir(path)):
					if f.endswith('.json'):
						try:
							with open(os.path.join(path, f)) as fp:
								combined.append(json.load(fp))
						except: pass
		if not combined:
			return "No tips found for title '{}'".format(title)
		lines = []
		for i, data in enumerate(combined):
			lines.append("--- Entry {} ---".format(i))
			for msg in data.get('entries', []):
				role = msg.get('role','?')
				content = msg.get('content','')
				lines.append("[{}] {}".format(role, content))
		return "\n".join(lines)
	def _usage(self):
		return "\nUsage:\n<GetTip>\n<title>string</title>\n</GetTip>"

class gettip(GetTip): pass
