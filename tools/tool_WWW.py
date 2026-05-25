import subprocess, os, glob
from config import Options

class WWW():
	def __init__(self):
		self.info = {
			"name":"WWW",
			"description":"Fetch a web page. Uses a Java HTTP client. Supports cookies from a shared cookie file.",
			"parameters":{
				"returnType":"string",
				"required":["url"],
				"properties":{
					"url":{
						"type":"string",
						"description":"URL to fetch (e.g., https://www.google.com)"
					},
					"links":{
						"type":"string",
						"description":"Set to 'true' to extract anchor links from the page"
					},
					"text":{
						"type":"string",
						"description":"Set to 'true' to strip HTML and return readable text"
					},
				},
			},
		}

	def run(self, url, opts={}, links=None, text=None):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		jars = glob.glob(os.path.join(tool_dir, "www", "target", "www-*.jar"))
		if not jars:
			return "Error: www jar not found in {}/www/target/".format(tool_dir)
		jar = jars[0]
		cmd = ["java", "-jar", jar]
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
			if os.path.exists(abs_path):
				cmd.extend(["--cookie-file", abs_path])
		if links and str(links).lower() == "true":
			cmd.append("--links")
		if text and str(text).lower() == "true":
			cmd.append("--text")
		cmd.append(url)
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
			return "Error: www timed out (30s limit)"
		except FileNotFoundError:
			return "Error: java not found in PATH"
		except Exception as E:
			return "Error executing www: {}".format(E)

class www(WWW):
	pass
