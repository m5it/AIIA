import base64, io, os, sys, importlib.util

import pytest
from PIL import Image
from src.ToolParser import ToolParser
from src import ImageGenBackends

# Load the tool module the same way the framework does (dynamic file load).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL_PATH = os.path.join(_ROOT, 'tools', 'tool_GenerateImage.py')

def _load_tool():
	spec = importlib.util.spec_from_file_location('tool_GenerateImage', _TOOL_PATH)
	mod = importlib.util.module_from_spec(spec)
	sys.modules['tool_GenerateImage'] = mod
	spec.loader.exec_module(mod)
	return mod

tool = _load_tool()

PNG_1x1 = None
def _png_b64():
	global PNG_1x1
	if PNG_1x1 is None:
		buf = io.BytesIO()
		Image.new('RGB', (1, 1), (255, 0, 0)).save(buf, 'PNG')
		PNG_1x1 = base64.b64encode(buf.getvalue()).decode()
	return PNG_1x1


class FakeHandle:
	def __init__(self, options):
		self.Options = options
	def Response(self, role, msg):
		pass


class FakeResp:
	def __init__(self, payload):
		self._payload = payload
	def raise_for_status(self):
		pass
	def json(self):
		return self._payload


class FakeRequests:
	"""Stub `requests` module capturing the last POST."""
	def __init__(self, payload):
		self._payload = payload
		self.last_url = None
		self.last_kwargs = None
	def post(self, url, **kwargs):
		self.last_url = url
		self.last_kwargs = kwargs
		return FakeResp(self._payload)


# ---------------------------------------------------------------------------
# _resolve_image_backends
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("options,expected", [
	({"AI_BACKEND": "ollama", "AI_IMAGE_BACKEND": "auto"}, ['ollama', 'vllm', 'local']),
	({"AI_BACKEND": "vllm", "AI_IMAGE_BACKEND": "auto"}, ['vllm', 'ollama', 'local']),
	({"AI_BACKEND": "vllm", "AI_IMAGE_BACKEND": "ollama"}, ['ollama', 'vllm', 'local']),
	({"AI_BACKEND": "ollama", "AI_IMAGE_BACKEND": "vllm"}, ['vllm', 'ollama', 'local']),
	({"AI_BACKEND": "vllm", "AI_IMAGE_BACKEND": "local"}, ['local']),
	({"AI_BACKEND": "vllm", "AI_IMAGE_BACKEND": "bogus"}, ['vllm', 'ollama', 'local']),
])
def test_resolve_image_backends(options, expected):
	assert ImageGenBackends._resolve_image_backends(FakeHandle(options)) == expected


def test_resolve_image_backends_no_handle():
	assert ImageGenBackends._resolve_image_backends(None) == ['ollama', 'vllm', 'local']


# ---------------------------------------------------------------------------
# _generate_vllm
# ---------------------------------------------------------------------------

@pytest.fixture
def vllm_handle():
	return FakeHandle({
		"AI_BACKEND": "vllm",
		"AI_IMAGE_BACKEND": "auto",
		"VLLM_HOST": "http://localhost:8000/v1",
		"VLLM_API_KEY": "",
		"VLLM_TIMEOUT": 30,
	})


def test_generate_vllm_success(monkeypatch, vllm_handle):
	fake = FakeRequests({'data': [{'b64_json': _png_b64()}]})
	monkeypatch.setitem(sys.modules, 'requests', fake)

	img = ImageGenBackends._generate_vllm('Qwen/Qwen-Image', 'a cat', 512, 512, 25, 42, vllm_handle)

	assert img is not None
	assert img.size == (1, 1)
	assert fake.last_url == 'http://localhost:8000/v1/images/generations'
	body = fake.last_kwargs['json']
	assert body['prompt'] == 'a cat'
	assert body['size'] == '512x512'
	assert body['num_inference_steps'] == 25
	assert body['seed'] == 42
	assert 'model' not in body  # not explicitly requested
	assert fake.last_kwargs['timeout'] == 30


def test_generate_vllm_explicit_model(monkeypatch, vllm_handle):
	fake = FakeRequests({'data': [{'b64_json': _png_b64()}]})
	monkeypatch.setitem(sys.modules, 'requests', fake)

	ImageGenBackends._generate_vllm('My/Own-Model', 'p', 64, 64, None, None, vllm_handle, explicit_model=True)

	assert fake.last_kwargs['json']['model'] == 'My/Own-Model'
	assert 'num_inference_steps' not in fake.last_kwargs['json']
	assert 'seed' not in fake.last_kwargs['json']


def test_generate_vllm_auth_header(monkeypatch, vllm_handle):
	vllm_handle.Options['VLLM_API_KEY'] = 'secret123'
	fake = FakeRequests({'data': [{'b64_json': _png_b64()}]})
	monkeypatch.setitem(sys.modules, 'requests', fake)

	ImageGenBackends._generate_vllm('m', 'p', 64, 64, None, None, vllm_handle)

	assert fake.last_kwargs['headers']['Authorization'] == 'Bearer secret123'


def test_generate_vllm_empty_data(monkeypatch, vllm_handle):
	fake = FakeRequests({'data': []})
	monkeypatch.setitem(sys.modules, 'requests', fake)

	assert ImageGenBackends._generate_vllm('m', 'p', 64, 64, None, None, vllm_handle) is None


def test_generate_vllm_missing_b64(monkeypatch, vllm_handle):
	fake = FakeRequests({'data': [{'url': 'http://x/y.png'}]})
	monkeypatch.setitem(sys.modules, 'requests', fake)

	assert ImageGenBackends._generate_vllm('m', 'p', 64, 64, None, None, vllm_handle) is None


def test_generate_vllm_request_error(monkeypatch, vllm_handle):
	class Boom:
		def post(self, *a, **k):
			raise ConnectionError("server not running")
	monkeypatch.setitem(sys.modules, 'requests', Boom())

	assert ImageGenBackends._generate_vllm('m', 'p', 64, 64, None, None, vllm_handle) is None


# ---------------------------------------------------------------------------
# run() dispatch
# ---------------------------------------------------------------------------

@pytest.fixture
def dispatch_handle():
	return FakeHandle({
		"AI_BACKEND": "vllm",
		"AI_IMAGE_BACKEND": "auto",
		"AI_IMAGE_GEN_MODEL": "",
		"AI_MODEL": "kimi-k2.5:cloud",
		"VLLM_HOST": "http://localhost:8000/v1",
	})


@pytest.fixture
def patch_run(monkeypatch):
	"""Replace all image backends with recorders returning None; replace save/inject."""
	calls = []
	def rec(fn_name):
		def _r(*a, **k):
			calls.append(fn_name)
			return None
		return _r
	monkeypatch.setattr(ImageGenBackends, '_generate_vllm', rec('vllm'))
	monkeypatch.setattr(ImageGenBackends, '_generate_ollama', rec('ollama'))
	monkeypatch.setattr(ImageGenBackends, '_generate_diffusers', rec('diffusers'))
	monkeypatch.setattr(ImageGenBackends, '_save_and_inject', lambda *a, **k: 'saved')
	return calls


def _ok(calls, fn_name):
	"""Recorder that appends the call and returns a valid image (success)."""
	def fn(*a, **k):
		calls.append(fn_name)
		return Image.new('RGB', (1, 1))
	return fn


def _call_run(handle, **kwargs):
	kwargs.setdefault('prompt', 'test image')
	kwargs.setdefault('width', 64)
	kwargs.setdefault('height', 64)
	old = ToolParser._current_handle
	ToolParser._current_handle = handle
	try:
		return tool.GenerateImage().run(**kwargs)
	finally:
		ToolParser._current_handle = old


def test_run_dispatches_vllm(monkeypatch, dispatch_handle, patch_run):
	monkeypatch.setattr(ImageGenBackends, '_generate_vllm', _ok(patch_run, 'vllm'))
	result = _call_run(dispatch_handle)
	assert result == 'saved'
	assert patch_run == ['vllm']  # diffusers not needed — vllm succeeded


def test_run_force_ollama_on_vllm_master(monkeypatch, dispatch_handle, patch_run):
	dispatch_handle.Options['AI_IMAGE_BACKEND'] = 'ollama'
	monkeypatch.setattr(ImageGenBackends, '_generate_ollama', _ok(patch_run, 'ollama'))
	result = _call_run(dispatch_handle)
	assert result == 'saved'
	assert patch_run == ['ollama']


def test_run_cross_backend_fallback(monkeypatch, dispatch_handle, patch_run):
	# vllm fails, ollama succeeds → chain [vllm, ollama]
	monkeypatch.setattr(ImageGenBackends, '_generate_ollama', _ok(patch_run, 'ollama'))
	result = _call_run(dispatch_handle)
	assert result == 'saved'
	assert patch_run == ['vllm', 'ollama']


def test_run_all_fail(monkeypatch, dispatch_handle, patch_run):
	def diffusers_fail(*a, **k):
		patch_run.append('diffusers')
		return "diffusers backend not available"
	monkeypatch.setattr(ImageGenBackends, '_generate_diffusers', diffusers_fail)
	result = _call_run(dispatch_handle)
	assert result == "diffusers backend not available"
	assert patch_run == ['vllm', 'ollama', 'diffusers']


def test_run_explicit_model_passed_to_vllm(monkeypatch, dispatch_handle):
	captured = {}
	def vllm_rec(model, prompt, width, height, steps, seed, handle, explicit_model=False):
		captured['explicit'] = explicit_model
		return Image.new('RGB', (1, 1))
	monkeypatch.setattr(ImageGenBackends, '_generate_vllm', vllm_rec)
	monkeypatch.setattr(ImageGenBackends, '_save_and_inject', lambda *a, **k: 'saved')
	result = _call_run(dispatch_handle, model='My/Own-Model')
	assert result == 'saved'
	assert captured['explicit'] is True
