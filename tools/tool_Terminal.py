import subprocess
import os
import re
from datetime import datetime

class Terminal():
	#
	def __init__(self):
		print("Terminal() STARTING")
		self.info = {
			"name":"Terminal",
			"description":"Execute terminal commands with security restrictions. Only allowed programs can be executed. All commands are logged for audit.",
			"parameters":{
				"returnType":"string",
				"required":["arg1"],
				"properties":{
					"arg1":{
						"type":"string", 
						"description":"Program/command to execute (must be in allowed list)."
					},
					"arg2":{
						"type":"string", 
						"description":"(Optional) Second argument."
					},
					"arg3":{
						"type":"string", 
						"description":"(Optional) Third argument."
					},
					"arg4":{
						"type":"string", 
						"description":"(Optional) Fourth argument."
					},
					"arg5":{
						"type":"string", 
						"description":"(Optional) Fifth argument."
					},
				},
			},
		}
		#
		# Default allowed programs list
		self.DEFAULT_ALLOWED = [
			'ls', 'dir', 'cat', 'echo', 'pwd', 'whoami', 'date', 'id',
			'grep', 'find', 'sort', 'head', 'tail', 'wc', 'awk', 'sed',
			'bash', 'sh', 'python3', 'python', 'node', 'perl', 'ruby',
			'git', 'make', 'cmake', 'gcc', 'g++',
			'ping', 'curl', 'wget', 'netstat', 'ss',
			'ps', 'top', 'df', 'du', 'free',
			'mkdir', 'cp', 'mv', 'touch', 'chmod', 'chown'
		]
	#
	def log_command(self, cmd, output, success):
		# Log command for audit purposes
		try:
			timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			log_entry = "[{}] CMD: {} | SUCCESS: {} | OUTPUT_LEN: {}\n".format(
				timestamp, ' '.join(cmd), success, len(output)
			)
			with open('terminal_audit.log', 'a') as f:
				f.write(log_entry)
		except Exception as E:
			print("Terminal.log_command() ERROR: {}".format(E))
	#
	def run(self, **kwargs):
		print("Terminal.run() STARTING, args: {}".format(kwargs))
		#
		# Extract arguments dynamically (arg1, arg2, arg3, ...)
		args = []
		for i in range(1, 100):  # Support up to 99 args
			key = "arg{}".format(i)
			if key in kwargs:
				args.append(kwargs[key])
			else:
				break
		#
		if len(args) == 0:
			return "Error: No arguments provided. At least arg1 (program name) is required."
		#
		program = args[0]
		#
		# Get allowed programs list from options or use default
		allowed = self.DEFAULT_ALLOWED
		if 'opts' in kwargs:
			opts = kwargs['opts']
			if isinstance(opts, dict) and 'allowed_programs' in opts:
				allowed = opts['allowed_programs']
		#
		# Check if program is allowed
		if program not in allowed:
			self.log_command(args, "", False)
			return "Error: Program '{}' is not in the allowed programs list. Allowed: {}".format(program, ', '.join(allowed))
		#
		# Build command (shell=False for security)
		cmd = args
		#
		print("Terminal.run() executing: {}".format(cmd))
		#
		try:
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=30,
				cwd=".",
				shell=False
			)
			#
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				if output:
					output += "\n"
				output += "STDERR:\n{}".format(result.stderr)
			#
			self.log_command(cmd, output, True)
			return output if output else "(no output)"
			#
		except subprocess.TimeoutExpired:
			self.log_command(cmd, "TIMEOUT", False)
			return "Error: Command timed out (30s limit)"
		except FileNotFoundError:
			self.log_command(cmd, "NOT_FOUND", False)
			return "Error: Program '{}' not found in PATH".format(program)
		except Exception as E:
			self.log_command(cmd, str(E), False)
			return "Error executing command: {}".format(E)
