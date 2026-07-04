import subprocess
import os
import re
import shlex
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
			'mkdir', 'cp', 'mv', 'touch', 'rm', 'rmdir', 'ln', 'install',
			'chmod', 'chown', 'cd'
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
		# Build final arg list: arg1 is the program name, remaining args
		# are passed verbatim.  No space-splitting — each <argN> is one
		# argument.  If an arg has matching outer quotes (' or "), strip
		# them but keep as one token (the model sometimes adds them).
		cleaned = []
		for i, arg in enumerate(args):
			if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in '\'"':
				cleaned.append(arg[1:-1])
			else:
				cleaned.append(arg)
		args = cleaned
		#
		program = args[0]
		#
		# Allow user-created scripts (./ or / paths that exist and are executable)
		if program.startswith('./') or program.startswith('/'):
			if os.path.isfile(program) and os.access(program, os.X_OK):
				print("Terminal.run() allowing local script: {}".format(program))
				cmd = args
				program_args = args[1:]
				try:
					result = subprocess.run(
						[program] + program_args,
						capture_output=True,
						text=True,
						timeout=30,
						cwd=".",
						shell=False
					)
					output = ""
					if result.stdout:
						output += result.stdout
					if result.stderr:
						if output:
							output += "\n"
						output += "STDERR:\n{}".format(result.stderr)
					self.log_command(cmd, output, True)
					return output if output else "(no output)"
				except subprocess.TimeoutExpired:
					self.log_command(cmd, "TIMEOUT", False)
					return "Error: Command timed out (30s limit)"
				except Exception as E:
					self.log_command(cmd, str(E), False)
					return "Error: {}".format(E)
			else:
				return "Error: Script '{}' not found or not executable. Use ExecuteScript tool for scripts that need chmod first.".format(program)
		#
		# Get allowed programs list from options or use default
		allowed = self.DEFAULT_ALLOWED
		if 'opts' in kwargs:
			opts = kwargs['opts']
			if isinstance(opts, dict) and 'allowed_programs' in opts:
				allowed = opts['allowed_programs']
		#
		# Detect arguments smashed into arg1 instead of split across argN
		if ' ' in program.strip():
			parts = program.split()
			first_word = parts[0]
			rest_args = parts[1:]
			if first_word in allowed:
				example = "  <arg1>{}</arg1>\n".format(first_word)
				for i, arg in enumerate(rest_args):
					example += "  <arg{}>{}</arg{}>\n".format(i+2, arg, i+2)
				return ("Error: Arguments embedded in <arg1> — each argument needs its own <argN> tag.\n"
					"Use separate tags:\n"
					"{}\n"
					"Instead of:\n"
					"  <arg1>{} {}</arg1>\n"
					"'{}' is allowed but arguments must be in their own tags.").format(
						example.rstrip(), first_word, ' '.join(rest_args), first_word)
			else:
				example = "  <arg1>{}</arg1>\n".format(first_word)
				for i, arg in enumerate(rest_args):
					example += "  <arg{}>{}</arg{}>\n".format(i+2, arg, i+2)
				return ("Error: Program '{}' not found in allowed list and contains spaces. "
					"If you intended '{}', use separate tags:\n"
					"{}\n"
					"Allowed: {}").format(program, first_word, example.rstrip(),
						', '.join(allowed))
		#
		# Handle cd explicitly — change Python's working directory
		if program == 'cd':
			if len(args) < 2:
				target = os.path.expanduser('~')
			else:
				target = args[1]
			try:
				os.chdir(target)
				cwd = os.getcwd()
				print("Terminal.run() cd to: {}".format(cwd))
				self.log_command(args, "Changed to {}".format(cwd), True)
				return "Directory changed to: {}".format(cwd)
			except Exception as E:
				return "Error: cd failed: {}".format(E)

		# Check if program is allowed
		if program not in allowed:
			self.log_command(args, "", False)
			return "Error: Program '{}' is not in the allowed programs list.\nAllowed: {}".format(program, ', '.join(allowed))
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
			return "Error: {}".format(E)
