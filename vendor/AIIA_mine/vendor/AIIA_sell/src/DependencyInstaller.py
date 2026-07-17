import os, sys, subprocess, json
from src.DependencyChecker import _venv_path, _python_bin, _state, _save_state

def install(persona_name, requirements, handle=None):
	"""Install a persona's dependencies into an isolated venv.
	Returns True if all succeeded, False otherwise.
	Supports resume: tracks installed packages in state file,
	retries only missing/failed items on next call.
	"""
	if not requirements:
		return True

	venv = _venv_path(persona_name)
	state = _state()
	persona_state = state.get(persona_name, {})
	installed_pip = set(persona_state.get('pip_installed', []))
	installed_hf = set(persona_state.get('hf_installed', []))

	# Step 1: Create venv if needed
	if not os.path.isdir(venv):
		_log(handle, "Creating venv for persona '{}' at {}".format(persona_name, venv))
		try:
			subprocess.run([sys.executable, '-m', 'venv', venv],
				check=True, capture_output=True, text=True)
		except subprocess.CalledProcessError as e:
			_log(handle, "Failed to create venv: {}".format(e.stderr), 'red')
			return False

	python = _python_bin(persona_name)
	if not os.path.isfile(python):
		_log(handle, "Python binary not found in venv: {}".format(python), 'red')
		return False

	# Step 2: Install pip packages
	pip_packages = requirements.get('pip_packages', [])
	all_pip_ok = True
	for pkg in pip_packages:
		if pkg in installed_pip:
			continue
		_log(handle, "Installing pip package: {} ...".format(pkg))
		try:
			subprocess.run([python, '-m', 'pip', 'install', pkg],
				check=True, capture_output=True, text=True,
				timeout=600)
			installed_pip.add(pkg)
			persona_state['pip_installed'] = sorted(installed_pip)
			state[persona_name] = persona_state
			_save_state(state)
			_log(handle, "  {} installed.".format(pkg), 'green')
		except subprocess.CalledProcessError as e:
			stderr = e.stderr.strip() if e.stderr else ''
			_log(handle, "  Failed to install {}: {}".format(pkg, stderr[:200]), 'red')
			all_pip_ok = False
		except subprocess.TimeoutExpired:
			_log(handle, "  Timed out installing {}. Will retry on next run.".format(pkg), 'red')
			all_pip_ok = False

	# Step 3: Download HF models
	hf_models = requirements.get('hf_models', [])
	all_hf_ok = True
	if hf_models:
		try:
			subprocess.run([python, '-c', 'from huggingface_hub import snapshot_download'],
				check=True, capture_output=True, text=True)
			_hf_available = True
		except subprocess.CalledProcessError:
			# huggingface_hub may not be in the requirements list;
			# install it on demand.
			_log(handle, "Installing huggingface-hub for model downloads...")
			try:
				subprocess.run([python, '-m', 'pip', 'install', 'huggingface-hub'],
					check=True, capture_output=True, text=True, timeout=120)
				_hf_available = True
			except Exception:
				_log(handle, "Failed to install huggingface-hub. Cannot download models.", 'red')
				_hf_available = False

		if _hf_available:
			for model_id in hf_models:
				if model_id in installed_hf:
					continue
				_log(handle, "Downloading model: {} ...".format(model_id))
				try:
					subprocess.run([
						python, '-c', """
import sys
from huggingface_hub import snapshot_download
try:
	snapshot_download('{model}', resume_download=True)
except Exception as e:
	sys.stderr.write(str(e))
	sys.exit(1)
""".format(model=model_id)
					], check=True, capture_output=True, text=True, timeout=1800)
					installed_hf.add(model_id)
					persona_state['hf_installed'] = sorted(installed_hf)
					state[persona_name] = persona_state
					_save_state(state)
					_log(handle, "  Model downloaded.".format(model_id), 'green')
				except subprocess.CalledProcessError as e:
					stderr = e.stderr.strip() if e.stderr else ''
					_log(handle, "  Failed to download {}: {}".format(model_id, stderr[:200]), 'red')
					all_hf_ok = False
				except subprocess.TimeoutExpired:
					_log(handle, "  Timed out downloading {}. Will retry on next run.".format(model_id), 'red')
					all_hf_ok = False

	# Step 4: Flag as ready if everything installed
	all_ok = all_pip_ok and all_hf_ok
	persona_state['all_installed'] = all_ok
	state[persona_name] = persona_state
	_save_state(state)
	return all_ok


def _log(handle, msg, color='cyan'):
	if handle and hasattr(handle, 'hLG'):
		handle.hLG.echo(msg, {'color': True, 'colorValue': color, 'debugOnly': False})
	else:
		print(msg)
