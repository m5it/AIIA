import subprocess, os, socket, json, time, signal, atexit
from config import Options

# Module-level server state (persists across tool reloads)
_server_state = {
	'proc': None,
	'port': None,
	'started': False,
}

_PORT_FILE = '/tmp/wwwjs.port'

def _read_port_file():
	try:
		if os.path.exists(_PORT_FILE):
			with open(_PORT_FILE) as f:
				return int(f.read().strip())
	except: pass
	return None

def _write_port_file(port):
	try:
		with open(_PORT_FILE, 'w') as f:
			f.write(str(port))
	except: pass

def _remove_port_file():
	try:
		if os.path.exists(_PORT_FILE):
			os.remove(_PORT_FILE)
	except: pass

def _ensure_server():
	if _server_state['started'] and _server_state['proc']:
		# Check if still alive
		ret = _server_state['proc'].poll()
		if ret is None:
			return _server_state['port']  # still running
		# crashed — clean up
		_server_state['started'] = False
		_server_state['port'] = None
		_server_state['proc'] = None
		_remove_port_file()
	return _start_server()

def _start_server():
	tool_dir = os.path.dirname(os.path.abspath(__file__))
	run_script = os.path.join(tool_dir, "wwwjs", "run.sh")
	if not os.path.exists(run_script):
		return None

	cmd = [run_script, "--server"]

	cookie_path = Options.get("COOKIE_FILE")
	if cookie_path:
		abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
		cmd.extend(["--cookie-file", abs_path])

	try:
		proc = subprocess.Popen(
			cmd,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			bufsize=1,
		)
		# Read port from first stdout line
		first_line = proc.stdout.readline().strip()
		if first_line.startswith("SERVER_PORT="):
			port = int(first_line.split("=")[1])
			_server_state['proc'] = proc
			_server_state['port'] = port
			_server_state['started'] = True
			_write_port_file(port)
			# Register cleanup
			atexit.register(_cleanup_server)
			return port
		else:
			# Unexpected output — kill and fall back
			proc.kill()
			return None
	except Exception as e:
		print("WWWJS server start error: {}".format(e))
		return None

def _cleanup_server():
	if _server_state['proc']:
		try:
			_server_state['proc'].terminate()
			_server_state['proc'].wait(timeout=3)
		except: pass
	_server_state['started'] = False
	_server_state['port'] = None
	_server_state['proc'] = None
	_remove_port_file()

def _send_command(port, cmd_dict, timeout=120):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(timeout)
		s.connect(('127.0.0.1', port))
		# Send JSON command
		json_str = json.dumps(cmd_dict) + '\n'
		s.sendall(json_str.encode('utf-8'))
		# Read JSON response
		buf = b''
		while True:
			chunk = s.recv(65536)
			if not chunk:
				break
			buf += chunk
			if b'\n' in chunk:
				break
		s.close()
		line = buf.decode('utf-8').strip()
		if not line:
			return "Error: empty response from server"
		resp = json.loads(line)
		if resp.get('status') == 'ok':
			return resp.get('data', '')
		else:
			return resp.get('data', 'Error: unknown server error')
	except socket.timeout:
		return "Error: server request timed out after {}s".format(timeout)
	except ConnectionRefusedError:
		# Server died — clean up and let caller fall back
		_server_state['started'] = False
		_server_state['port'] = None
		_server_state['proc'] = None
		_remove_port_file()
		return "Error: server not running"
	except Exception as e:
		return "Error: server communication error: {}".format(e)

class WWWJS():
	def __init__(self):
		self.info = {
			"name":"WWWJS",
			"description":"Fetch a web page using JavaFX WebView (full JS rendering). Opens a persistent server on first call; subsequent calls reuse it. Can open a visible browser window for captcha solving. Supports cookies from a shared cookie file.",
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
		# Build command dict
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

		# Try to use server if available
		port = _ensure_server()
		if port:
			result = _send_command(port, cmd)
			# If server communication failed, fall through to one-shot
			if not result.startswith("Error: server"):
				return result

		# Fall back to one-shot mode
		return self._run_oneshot(url, browser, text, links, source, screenshot, wait, selector)

	def _run_oneshot(self, url, browser=None, text=None, links=None,
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
