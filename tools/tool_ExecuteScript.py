import subprocess
import os
import shlex
import shutil

class ExecuteScript():
	#
	def __init__(self):
		print("ExecuteScript() STARTING")
		self.info = {
			"name":"ExecuteScript",
			"description":"Execute a script file (.sh, .py, .js, etc.) or a command (python, bash, node, etc.) with arguments. Returns stdout+stderr.",
			"parameters":{
				"returnType":"string",
				"required":["fileName"],
				"properties":{
					"fileName":{
						"type":"string",
						"description":"Script file name (e.g. script.sh, test.py) or command name (e.g. python, bash, node)."
					},
					"args":{
						"type":"string",
						"description":"(Optional) Arguments — quoted string is split automatically (e.g. '-c \"print(1)\"')."
					},
				},
			},
		}
	#
	def run(self, fileName, args="", opts={}):
		print("ExecuteScript.run() STARTING, fileName: {}, args: {}".format(fileName, args))
		#
		file_path = fileName
		is_file = os.path.exists(file_path) and os.path.isfile(file_path)
		is_command = False
		#
		if not is_file:
			# Try as a command in PATH
			if shutil.which(fileName):
				is_command = True
			else:
				return "Error: '{}' not found as file or command.".format(fileName)
		#
		# Determine interpreter (only for script files)
		interpreter = None
		if is_file:
			ext = os.path.splitext(fileName)[1].lower()
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
		#
		# Build command
		if interpreter:
			cmd = [interpreter, file_path]
		elif is_command:
			cmd = [fileName]
		else:
			cmd = [file_path]
		#
		if args:
			# Check for shell syntax — if detected, wrap in bash -c
			shell_chars = set('|;&><`$')
			if any(c in args for c in shell_chars):
				full_cmd = "{} {}".format(fileName, args)
				cmd = ["bash", "-c", full_cmd]
			else:
				try:
					cmd.extend(shlex.split(args))
				except ValueError:
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
			return "Error: {}".format(E)
