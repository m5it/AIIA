import subprocess
import os

class ExecuteScript():
	#
	def __init__(self):
		print("ExecuteScript() STARTING")
		self.info = {
			"name":"ExecuteScript",
			"description":"Execute a script file (.sh, .py, .js, etc.) and return the output. Scripts are executed from the project root directory.",
			"parameters":{
				"returnType":"string",
				"required":["fileName"],
				"properties":{
					"fileName":{
						"type":"string", 
						"description":"Name of the script file to execute (e.g., script.sh, test.py). File should be in  folder."
					},
					"args":{
						"type":"string", 
						"description":"(Optional) Arguments to pass to the script."
					},
				},
			},
		}
	#
	def run(self, fileName, args="", opts={}):
		print("ExecuteScript.run() STARTING, fileName: {}, args: {}".format(fileName, args))
		#
		# Check  folder
		file_path = "{}".format(fileName)
		if not os.path.exists(file_path):
			return "Error: File {} not found in ".format(fileName)
		#
		# Determine interpreter based on file extension
		ext = os.path.splitext(fileName)[1].lower()
		interpreter = None
		#
		if ext == ".py":
			interpreter = "python3"
		elif ext == ".sh":
			interpreter = "bash"
		elif ext in [".js", ".mjs"]:
			interpreter = "node"
		elif ext == ".rb":
			interpreter = "ruby"
		elif ext == ".pl":
			interpreter = "perl"
		else:
			# Try to run as executable
			interpreter = ""
		#
		# Build command
		if interpreter:
			cmd = [interpreter, file_path]
		else:
			cmd = [file_path]
		#
		if args:
			cmd.append(args)
		#
		print("ExecuteScript.run() executing: {}".format(cmd))
		#
		try:
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=30,
				cwd="."
			)
			#
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				output += "\nSTDERR:\n{}".format(result.stderr)
			#
			return output if output else "(no output)"
			#
		except subprocess.TimeoutExpired:
			return "Error: Script execution timed out (30s limit)"
		except Exception as E:
			return "Error executing script: {}".format(E)
