import os
from config import Options

def _walk_tips(path, source_prefix):
	"""Recursively find tip titles under path. Returns list of
	(source_path, title, count) tuples."""
	result = []
	if not os.path.isdir(path):
		return result
	for entry in sorted(os.listdir(path)):
		entry_path = os.path.join(path, entry)
		if not os.path.isdir(entry_path):
			continue
		files = [f for f in os.listdir(entry_path) if f.endswith('.json')]
		subdirs = [f for f in os.listdir(entry_path)
				   if os.path.isdir(os.path.join(entry_path, f))]
		if files and not subdirs:
			# Leaf title directory.
			count = len(files)
			if count:
				result.append((source_prefix, entry, count))
		elif subdirs:
			# Project subdirectory (e.g. model/p_HASH).
			for sub_source, sub_title, sub_count in _walk_tips(
					entry_path, "{}/{}".format(source_prefix, entry)):
				result.append((sub_source, sub_title, sub_count))
	return result

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
			for source_path, title, count in _walk_tips(path, s):
				result["{}/{}".format(source_path, title)] = (source_path, title, count)
		if not result:
			return "No tips saved."
		lines = ["Tips:"]
		for key, (source_path, title, count) in sorted(result.items()):
			lines.append("  {}/{} -> {} entries".format(source_path, title, count))
		return "\n".join(lines)
	def _usage(self):
		return "\nUsage:\n<ListTips>\n<source>string</source>\n</ListTips>"

class listtips(ListTips): pass
