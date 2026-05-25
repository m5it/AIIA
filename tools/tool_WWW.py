import subprocess, os, glob

class WWW():
	def __init__(self):
		self.info = {
			"name":"WWW",
			"description":"Fetch a web page via the Java web client. Runs java -jar on the wwwcli jar with the given URL.",
			"parameters":{
				"returnType":"string",
				"required":["url"],
				"properties":{
					"url":{
						"type":"string",
						"description":"URL to fetch (e.g., https://www.google.com)"
					},
				},
			},
		}

	def run(self, url, opts={}):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		jars = glob.glob(os.path.join(tool_dir, "wwwcli", "target", "wwwcli*.jar"))
		if not jars:
			return "Error: wwwcli jar not found in {}/wwwcli/target/".format(tool_dir)
		jar = jars[0]
		cmd = ["java", "-jar", jar, url]
		try:
			result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=".")
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				if output:
					output += "\n"
				output += "STDERR:\n{}".format(result.stderr)
			return output if output else "(no output)"
		except subprocess.TimeoutExpired:
			return "Error: wwwcli timed out (30s limit)"
		except FileNotFoundError:
			return "Error: java not found in PATH"
		except Exception as E:
			return "Error executing wwwcli: {}".format(E)

class www(WWW):
	pass
