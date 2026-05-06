import os
from src.functions import importmodule, splitFileNameExtension

class listTools():
	def __init__(self):
		self.info = {
			"name": "listTools",
			"description": "List all available tools and their descriptions.",
			"parameters": {
				"returnType": "string",
				"required": [],
				"properties": {}
			}
		}
	
	def run(self, opts={}):
		print("listTools.run() STARTING")
		tools_dir = "tools/"
		tool_list = []
		
		# Get all tool files
		for filename in os.listdir(tools_dir):
			if filename.startswith("tool_") and filename.endswith(".py"):
				# filename is like "tool_X.py"
				# Extract module name (tool_X) and class name (X)
				tmp = splitFileNameExtension(filename)
				module_name = tmp['name']  # tool_X
				class_name = filename[5:-3]  # X
				try:
					mod = importmodule(module_name, True, {'path': 'tools'})
					tool_class = getattr(mod, class_name)
					tool_instance = tool_class()
					tool_list.append({
						"name": tool_instance.info["name"],
						"description": tool_instance.info["description"]
					})
				except Exception as e:
					print("listTools: failed to load {}: {}".format(class_name, e))
		
		# Format output
		output = "Available tools ({} total):\n".format(len(tool_list))
		for tool in sorted(tool_list, key=lambda x: x["name"]):
			output += "\n- {}: {}".format(tool["name"], tool["description"])
		
		# Add usage examples from Commands.cmds if available
		try:
			from src.Handle import Handle
			# This is a bit tricky since we need an instance, but we can show examples
			output += "\n\nUsage examples:"
			output += "\n- <List></List>  # List files in work/"
			output += "\n- <ReadFile><fileName>test.txt</fileName></ReadFile>  # Read file from work/"
			output += "\n- <WriteFile><fileName>output.txt</fileName><contentOfFile>Hello</contentOfFile></WriteFile>  # Write file to work/"
			output += "\n- <Find><pattern>*.py</pattern></Find>  # Find Python files in work/"
			output += "\n- <Grep><pattern>def </pattern><fileName>test.py</fileName></Grep>  # Search in file"
		except:
			pass
		
		return output
