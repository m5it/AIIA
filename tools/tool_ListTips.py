import os
from config import Options

class ListTips():
	def __init__(self):
		self.info = {
			"name":"ListTips",
			"description":"List all saved tip titles with entry counts, optionally filtered by source (user or model).",
			"parameters":{
				"returnType":"string",
				"required":[],
				"properties":{
					"source":{
						"type":"string",
						"description":"Filter by source: 'user' or 'model' (default: both)"
					},
				},
			},
		}
	def run(self, opts={}, source=None):
		if source and source.strip().lower() not in ('user','model',''):
			return "Error: invalid <source> '{}'. Use 'user', 'model', or omit for both.".format(source) + self._usage()
		base = Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
		srcs = ['user', 'model']
		if source and source.strip().lower() in ('user','model'):
			srcs = [source.strip().lower()]
		result = {}
		for s in srcs:
			path = os.path.join(base, s)
			if os.path.isdir(path):
				for title in sorted(os.listdir(path)):
					tpath = os.path.join(path, title)
					if os.path.isdir(tpath):
						count = len([f for f in os.listdir(tpath) if f.endswith('.json')])
						if count:
							result["{}/{}".format(s, title)] = (s, title, count)
		if not result:
			return "No tips saved."
		lines = ["Tips:"]
		for key, (s, title, count) in sorted(result.items()):
			lines.append("  {}/{} -> {} entries".format(s, title, count))
		return "\n".join(lines)
	def _usage(self):
		return "\nUsage:\n<ListTips>\n<source>string</source>\n</ListTips>"

class listtips(ListTips): pass
