import subprocess
import os

class Diff():
	#
	def __init__(self):
		print("Diff() STARTING")
		self.info = {
			"name":"Diff",
			"description":"Compare two files and show differences. Files are read from work/ directory.",
			"parameters":{
				"returnType":"string",
				"required":["file1","file2"],
				"properties":{
					"file1":{
						"type":"string", 
						"description":"First file to compare (in work/)."
					},
					"file2":{
						"type":"string", 
						"description":"Second file to compare (in work/)."
					},
					"unified":{
						"type":"boolean", 
						"description":"(Optional) Use unified diff format (-u). Default: false."
					},
				},
			},
		}
	#
	def run(self, file1, file2, unified=False, opts={}):
		print("Diff.run() STARTING, file1: {}, file2: {}, unified: {}".format(file1, file2, unified))
		#
		# Find files in work/
		path1 = self._find_file(file1)
		path2 = self._find_file(file2)
		#
		if not path1:
			return "Error: File {} not found in work/".format(file1)
		if not path2:
			return "Error: File {} not found in work/".format(file2)
		#
		# Build diff command
		cmd = ["diff"]
		if unified:
			cmd.append("-u")
		#
		cmd.extend([path1, path2])
		#
		print("Diff.run() executing: {}".format(cmd))
		#
		try:
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				timeout=10
			)
			#
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				output += result.stderr
			#
			if not output:
				return "Files are identical"
			#
			return output
			#
		except Exception as E:
			return "Error executing diff: {}".format(E)
	#
	def _find_file(self, fileName):
		# Check work/ only
		full_path = "work/{}".format(fileName)
		if os.path.exists(full_path):
			return full_path
		return None
