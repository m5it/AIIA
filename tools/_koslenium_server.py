import subprocess, os, socket, json, time, signal, atexit, sys, threading, random
from config import Options

_DEBUG = Options.get("DEBUG", False)
def _dbg(*a, **kw):
	if _DEBUG:
		print("_koslenium_server:", *a, file=sys.stderr, **kw)

_server_lock = threading.Lock()
_server_state = {
	'proc': None,
	'port': None,
	'started': False,
	'mode': None,  # 'headless' or 'browser'
	'display': None,  # DISPLAY value used at server start
}

_xvfb_proc = None

_PORT_FILE = '/tmp/koslenium.port'
_SERVER_LOG = '/tmp/koslenium-server.log'

def _ensure_display():
	"""Return a usable DISPLAY string, starting Xvfb if needed."""
	d = os.environ.get('DISPLAY')
	if d:
		return d
	global _xvfb_proc
	if _xvfb_proc and _xvfb_proc.poll() is None:
		return os.environ.get('DISPLAY', ':99')
	# Try a few display numbers to avoid stale locks
	for disp in [99, 98, 97, 96, 95]:
		lock = '/tmp/.X{}-lock'.format(disp)
		sock = '/tmp/.X11-unix/X{}'.format(disp)
		if os.path.exists(lock) or os.path.exists(sock):
			continue
		try:
			proc = subprocess.Popen(
				['Xvfb', ':{}'.format(disp), '-screen', '0', '1280x1024x24', '-nolisten', 'tcp'],
				stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
			)
			time.sleep(0.5)
			if proc.poll() is None:
				_xvfb_proc = proc
				os.environ['DISPLAY'] = ':{}'.format(disp)
				return ':{}'.format(disp)
			proc.wait()
		except Exception:
			continue
	return None

def _cleanup_xvfb():
	global _xvfb_proc
	if _xvfb_proc:
		try:
			_xvfb_proc.terminate()
			_xvfb_proc.wait(timeout=3)
		except Exception:
			try:
				_xvfb_proc.kill()
			except Exception:
				pass
		_xvfb_proc = None
atexit.register(_cleanup_xvfb)

def _read_port_file():
	try:
		if os.path.exists(_PORT_FILE):
			with open(_PORT_FILE) as f:
				return int(f.read().strip())
	except Exception: pass
	return None

def _write_port_file(port):
	try:
		with open(_PORT_FILE, 'w') as f:
			f.write(str(port))
	except Exception: pass

def _remove_port_file():
	try:
		if os.path.exists(_PORT_FILE):
			os.remove(_PORT_FILE)
	except Exception: pass

def _start_server(browser=False):
	tool_dir = os.path.dirname(os.path.abspath(__file__))
	run_script = os.path.join(tool_dir, "koslenium_driver", "run.sh")
	if not os.path.exists(run_script):
		return None

	cmd = [run_script, "--server"]
	if browser:
		cmd.append("--browser")
	cookie_path = Options.get("COOKIE_FILE")
	if not cookie_path:
		cookie_path = os.path.expanduser("~/.config/ourai/cookies.json")
		os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
	if cookie_path:
		abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
		cmd.extend(["--cookie-file", abs_path])

	# Ensure we have a display (start Xvfb if needed)
	display = _ensure_display()
	proc_env = os.environ.copy()
	if display:
		proc_env['DISPLAY'] = display
	try:
		logfile = open(_SERVER_LOG, 'a')
		logfile.write("\n--- Server start at {} ---\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
		logfile.write("DISPLAY={}, browser={}\n".format(display, browser))
		logfile.flush()
		proc = subprocess.Popen(
			cmd,
			stdout=subprocess.PIPE,
			stderr=logfile,
			env=proc_env,
			text=True,
			bufsize=1,
		)
		first_line = proc.stdout.readline().strip()
		if first_line.startswith("SERVER_PORT="):
			port = int(first_line.split("=")[1])
			_server_state['proc'] = proc
			_server_state['port'] = port
			_server_state['started'] = True
			_server_state['mode'] = 'browser' if browser else 'headless'
			_server_state['display'] = display
			_write_port_file(port)
			atexit.register(_cleanup_server)
			logfile.write("Server started on port {} (mode={}, display={})\n".format(port, _server_state['mode'], display))
			logfile.flush()
			return port
		else:
			stderr_preview = open(_SERVER_LOG).read()[-500:]
			_dbg("server start failed. First line: {!r}, stderr tail: {}".format(first_line, stderr_preview))
			proc.kill()
			return None
	except Exception as e:
		_dbg("error starting server: {}".format(e))
		return None

def _cleanup_server():
	if _server_state['proc']:
		try:
			_server_state['proc'].terminate()
			_server_state['proc'].wait(timeout=3)
		except Exception: pass
	_server_state['started'] = False
	_server_state['port'] = None
	_server_state['proc'] = None
	_server_state['mode'] = None
	_server_state['display'] = None
	_remove_port_file()

def ensure_server(browser=False):
	with _server_lock:
		if _server_state['started'] and _server_state['proc']:
			ret = _server_state['proc'].poll()
			if ret is None:
				# If browser requested but current server is headless, restart
				if browser and _server_state.get('mode') != 'browser':
					_dbg("restarting server for browser mode (was {})".format(_server_state.get('mode')))
					_cleanup_server()
				else:
					return _server_state['port']
			_cleanup_server()
		return _start_server(browser=browser)

def send(port, cmd_dict, timeout=120):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(timeout)
		s.connect(('127.0.0.1', port))
		json_str = json.dumps(cmd_dict) + '\n'
		s.sendall(json_str.encode('utf-8'))
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
			_dbg("send: empty response from server")
			return None
		resp = json.loads(line)
		if resp.get('status') == 'ok':
			return resp.get('data', '')
		else:
			err_data = resp.get('data', 'unknown error')
			_dbg("send: server returned error: {}".format(err_data))
			return None
	except socket.timeout:
		_dbg("send: timeout after {}s connecting to port {}".format(timeout, port))
		return None
	except ConnectionRefusedError:
		_dbg("send: connection refused on port {}".format(port))
		return None
	except json.JSONDecodeError as e:
		preview = buf.decode('utf-8', errors='replace')[:200]
		_dbg("send: JSON decode error: {} data: {!r}".format(e, preview))
		return None
	except Exception as e:
		_dbg("send: unexpected error: {}".format(e))
		return None

def exec_script(port, script, wait=0, timeout=120):
	"""Send JavaScript to execute on the current page via the wwwjs server."""
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(timeout)
		s.connect(('127.0.0.1', port))
		cmd = {'script': script}
		if wait:
			cmd['wait'] = wait
		s.sendall((json.dumps(cmd) + '\n').encode('utf-8'))
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
			return None
		resp = json.loads(line)
		if resp.get('status') == 'ok':
			return resp.get('script_result') or resp.get('data', '')
		else:
			_dbg("exec_script: server error: {}".format(resp.get('data', 'unknown')))
			return None
	except Exception as e:
		_dbg("exec_script: error: {}".format(e))
		return None

def start_background(browser=False, wait=True):
	"""Start the wwwjs server in background. If wait=True, block until ready.
	   Intended for eager startup at Handle init."""
	port = ensure_server(browser=browser)
	if port:
		_dbg("background server ready on port {} (mode={})".format(port, _server_state.get('mode')))
		return port
	else:
		_dbg("background server failed to start")
		return None
