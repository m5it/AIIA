import os, json, subprocess, sys

DEPS_STATE_DIR = os.path.expanduser('~/.config/aiia')
DEPS_STATE_FILE = os.path.join(DEPS_STATE_DIR, 'persona_deps.json')

def _venv_path(persona_name):
	return os.path.join(DEPS_STATE_DIR, 'envs', persona_name)

def _python_bin(persona_name):
	venv = _venv_path(persona_name)
	if sys.platform == 'win32':
		return os.path.join(venv, 'Scripts', 'python.exe')
	return os.path.join(venv, 'bin', 'python3')

def _state():
	if os.path.isfile(DEPS_STATE_FILE):
		try:
			return json.load(open(DEPS_STATE_FILE))
		except Exception:
			pass
	return {}

def _save_state(state):
	os.makedirs(DEPS_STATE_DIR, exist_ok=True)
	with open(DEPS_STATE_FILE, 'w') as f:
		json.dump(state, f, indent=2)

def check(persona_name, requirements):
	"""Check if a persona's requirements are installed.
	Returns dict with keys: all_installed, venv_exists, pip_missing, hf_missing, installed_pip, installed_hf.
	"""
	if not requirements:
		return {'all_installed': True, 'venv_exists': False,
				'pip_missing': [], 'hf_missing': []}
	state = _state()
	persona_state = state.get(persona_name, {})
	installed_pip = set(persona_state.get('pip_installed', []))
	installed_hf = set(persona_state.get('hf_installed', []))

	venv = _venv_path(persona_name)
	venv_exists = os.path.isdir(venv)

	pip_required = set(requirements.get('pip_packages', []))
	hf_required = set(requirements.get('hf_models', []))

	pip_missing = [p for p in pip_required if p not in installed_pip]
	hf_missing = [m for m in hf_required if m not in installed_hf]

	return {
		'all_installed': venv_exists and not pip_missing and not hf_missing,
		'venv_exists': venv_exists,
		'pip_missing': pip_missing,
		'hf_missing': hf_missing,
		'installed_pip': list(installed_pip),
		'installed_hf': list(installed_hf),
		'state': persona_state,
	}
