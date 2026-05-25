import subprocess, os, socket, json, time, signal, atexit
from config import Options

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
		first_line = proc.stdout.readline().strip()
		if first_line.startswith("SERVER_PORT="):
			port = int(first_line.split("=")[1])
			_server_state['proc'] = proc
			_server_state['port'] = port
			_server_state['started'] = True
			_write_port_file(port)
			atexit.register(_cleanup_server)
			return port
		else:
			proc.kill()
			return None
	except Exception:
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

def ensure_server():
	if _server_state['started'] and _server_state['proc']:
		ret = _server_state['proc'].poll()
		if ret is None:
			return _server_state['port']
		_server_state['started'] = False
		_server_state['port'] = None
		_server_state['proc'] = None
		_remove_port_file()
	return _start_server()

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
			return None
		resp = json.loads(line)
		if resp.get('status') == 'ok':
			return resp.get('data', '')
		else:
			return resp.get('data', None)
	except:
		return None
