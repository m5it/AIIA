from src.ToolParser import ToolParser

class ReinsertTip():
	def __init__(self):
		self.info = {
			"name":"ReinsertTip",
			"description":"Reinsert a saved tip's entries into current chat history. Pulls tip content into active context.",
			"parameters":{
				"returnType":"string",
				"required":["title"],
				"properties":{
					"title":{
						"type":"string",
						"description":"Title of the tip to reinsert into chat history."
					}
				}
			}
		}
	#
	def run(self, title="", **kwargs):
		if not title:
			return "Error: 'title' parameter is required. Usage: <ReinsertTip><title>my_tip</title></ReinsertTip>"
		try:
			handle = ToolParser._current_handle
			if not handle or not hasattr(handle, 'hTM'):
				return "Error: handle with hTM not available."
			count = handle.hTM.reinsert(title)
			if count > 0:
				return "Reinserted {} message(s) from tip '{}' into chat history.".format(count, title)
			else:
				return "No entries found for tip title '{}'.".format(title)
		except Exception as e:
			return "Error: {}".format(e)
