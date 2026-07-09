import os, json, time
from config import Options

class SaveTip():
	def __init__(self):
		self.info = {
			"name":"SaveTip",
			"description":"Save a tip with a title and content to model's tip storage. Later retrievable via GetTip.",
			"parameters":{
				"returnType":"string",
				"required":["title","content"],
				"properties":{
					"title":{
						"type":"string",
						"description":"Title for the tip (e.g., 'search_pattern', 'debug_command')"
					},
					"content":{
						"type":"string",
						"description":"The tip content to save"
					},
				},
			},
		}
	def run(self, title="", opts={}, content=""):
		err = self._validate(title, content)
		if err:
			return err + self._usage()
		base = Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
		path = os.path.join(base, 'model', title)
		os.makedirs(path, exist_ok=True)
		ts = int(time.time())
		data = {
			'title': title,
			'source': 'model',
			'saved_at': ts,
			'entries': [{'role':'model', 'content':content}],
		}
		try:
			with open(os.path.join(path, "{}.json".format(ts)), 'w') as f:
				f.write(json.dumps(data))
			return "Saved tip '{}'".format(title)
		except Exception as e:
			return "Error: {}".format(e)
	def _validate(self, title, content):
		if not title or not title.strip():
			return "Error: <title> is required and cannot be empty."
		if not content or not content.strip():
			return "Error: <content> is required and cannot be empty."
		return None
	def _usage(self):
		return "\nUsage:\n<SaveTip>\n<title>string</title>\n<content>string</content>\n</SaveTip>"

class savetip(SaveTip): pass
