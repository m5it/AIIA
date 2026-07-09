import subprocess, os, glob, sys
from config import Options
from tools._koslenium_server import ensure_server, send

_DEBUG = Options.get("DEBUG", False)
def _dbg(*a, **kw):
	if _DEBUG:
		print("WWW:", *a, file=sys.stderr, **kw)

class WWW():
	def __init__(self):
		self.info = {
			"name":"WWW",
			"description":"Fetch a web page. Uses a persistent JS-capable browser engine when available; falls back to a lightweight HTTP client for simple requests.",
			"parameters":{
				"returnType":"string",
				"required":["url"],
				"properties":{
					"url":{
						"type":"string",
						"description":"URL to fetch (e.g., https://www.google.com)"
					},
					"js":{
						"type":"string",
						"description":"Set to 'true' to enable JavaScript rendering (default: false for speed, auto-enables when browser/screenshot needed)"
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

	def run(self, url, opts={}, js=None, browser=None, text=None, links=None,
			source=None, screenshot=None, wait=None, selector=None):
		needs_js = (
			browser and str(browser).lower() == 'true'
			or screenshot
			or (js and str(js).lower() == 'true')
		)

		# Auto-enable cookies for JS/browser requests
		if needs_js and not Options.get("COOKIE_FILE"):
			default_cookie = os.path.expanduser("~/.config/aiia/cookies.json")
			Options["COOKIE_FILE"] = default_cookie
			os.makedirs(os.path.dirname(default_cookie), exist_ok=True)

		# Build command dict for server mode
		cmd = {'url': url}
		if browser and str(browser).lower() == 'true':
			cmd['browser'] = True
		if text and str(text).lower() == 'true':
			cmd['text'] = True
		if links and str(links).lower() == 'true':
			cmd['links'] = True
		if source and str(source).lower() == 'true':
			cmd['source'] = True
		if screenshot:
			cmd['screenshot'] = screenshot
		if wait:
			cmd['wait'] = int(wait)
		if selector:
			cmd['selector'] = selector
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			if not os.path.isabs(cookie_path):
				abs_cookie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cookie_path)
			else:
				abs_cookie = cookie_path
			cmd['cookie_file'] = abs_cookie

		# Try server if JS needed or if server already running
		if needs_js:
			port = ensure_server(browser=bool(cmd.get('browser')))
			if port:
				_dbg("using server path (port {})".format(port))
				result = send(port, cmd)
				if result is not None:
					return result
				_dbg("server returned None, falling back to one-shot")
			else:
				_dbg("no server port, falling back to one-shot")
			# Fall back to one-shot wwwjs
			return self._run_wwwjs(cmd)
		else:
			_dbg("no JS needed, using simple path")

		# Try server if already running (fast path even without JS)
		port = ensure_server()
		if port:
			result = send(port, cmd)
			if result is not None:
				return result

		# Fall back to lightweight www.jar
		return self._run_www_jar(url, text, links)

	def _run_www_jar(self, url, text, links):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		jars = glob.glob(os.path.join(tool_dir, "koslenium_driver", "www", "target", "www-*.jar"))
		if not jars:
			return "Error: www jar not found"
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
			return "Error: {}".format(E)

	def _run_wwwjs(self, cmd_dict):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		run_script = os.path.join(tool_dir, "koslenium_driver", "run.sh")
		if not os.path.exists(run_script):
			return "Error: koslenium_driver/run.sh not found"

		cli = [run_script]
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
			cli.extend(["--cookie-file", abs_path])

		if cmd_dict.get('browser'):
			cli.append("--browser")
		if cmd_dict.get('text'):
			cli.append("--text")
		if cmd_dict.get('links'):
			cli.append("--links")
		if cmd_dict.get('source'):
			cli.append("--source")
		if cmd_dict.get('screenshot'):
			cli.extend(["--screenshot", cmd_dict['screenshot']])
		if cmd_dict.get('wait'):
			cli.extend(["--wait", str(cmd_dict['wait'])])
		if cmd_dict.get('selector'):
			cli.extend(["--selector", cmd_dict['selector']])
		cli.append(cmd_dict['url'])

		# Ensure display for headless JavaFX
		proc_env = os.environ.copy()
		from tools._koslenium_server import _ensure_display
		disp = _ensure_display()
		if disp:
			proc_env['DISPLAY'] = disp

		try:
			result = subprocess.run(cli, capture_output=True, text=True, timeout=300, cwd=".", env=proc_env)
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
		except Exception as E:
			return "Error: {}".format(E)

class www(WWW):
	pass
