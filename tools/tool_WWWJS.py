import subprocess, os
from config import Options

class WWWJS():
	def __init__(self):
		self.info = {
			"name":"WWWJS",
			"description":"Fetch a web page using JavaFX WebView (full JS rendering). Can open a visible browser window for captcha solving. Supports cookies from a shared cookie file.",
			"parameters":{
				"returnType":"string",
				"required":["url"],
				"properties":{
					"url":{
						"type":"string",
						"description":"URL to fetch (e.g., https://www.google.com)"
					},
					"browser":{
						"type":"string",
						"description":"Set to 'true' to open a visible browser window for manual interaction (captcha solving)"
					},
					"text":{
						"type":"string",
						"description":"Set to 'true' to strip HTML and return readable text"
					},
					"links":{
						"type":"string",
						"description":"Set to 'true' to extract anchor links from the page"
					},
					"source":{
						"type":"string",
						"description":"Set to 'true' to show raw HTML (bypasses captcha detection)"
					},
					"screenshot":{
						"type":"string",
						"description":"File path to save a PNG screenshot (e.g., /tmp/page.png)"
					},
					"wait":{
						"type":"string",
						"description":"Extra wait time in milliseconds for JS rendering (default: 3000)"
					},
					"selector":{
						"type":"string",
						"description":"CSS selector to wait for before extracting content"
					},
				},
			},
		}

	def run(self, url, opts={}, browser=None, text=None, links=None,
			source=None, screenshot=None, wait=None, selector=None):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		run_script = os.path.join(tool_dir, "wwwjs", "run.sh")
		if not os.path.exists(run_script):
			return "Error: wwwjs/run.sh not found"
		cmd = [run_script]
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
			cmd.extend(["--cookie-file", abs_path])
		if browser and str(browser).lower() == "true":
			cmd.append("--browser")
		if text and str(text).lower() == "true":
			cmd.append("--text")
		if links and str(links).lower() == "true":
			cmd.append("--links")
		if source and str(source).lower() == "true":
			cmd.append("--source")
		if screenshot:
			cmd.extend(["--screenshot", screenshot])
		if wait:
			cmd.extend(["--wait", wait])
		if selector:
			cmd.extend(["--selector", selector])
		cmd.append(url)
		try:
			result = subprocess.run(cmd, capture_output=True, text=True,
									timeout=300, cwd=".")
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				if output:
					output += "\n"
				output += "STDERR:\n{}".format(result.stderr)
			return output if output else "(no output)"
		except subprocess.TimeoutExpired:
			return "Error: wwwjs timed out (300s limit)"
		except FileNotFoundError:
			return "Error: java or run.sh not found in PATH"
		except Exception as E:
			return "Error executing wwwjs: {}".format(E)

class wwwjs(WWWJS):
	pass
