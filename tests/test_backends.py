import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.LLMBackends import get_backend
from src.LLMBackends.VLLMBackend import _detect_mime, VLLMBackend


def test_factory_default_ollama():
	backend = get_backend({})
	assert backend.name == "ollama"
	assert backend.is_vllm is False


def test_factory_vllm():
	backend = get_backend({"AI_BACKEND": "vllm"})
	assert backend.name == "vllm"
	assert backend.is_vllm is True


def test_factory_case_insensitive():
	backend = get_backend({"AI_BACKEND": "VLLM"})
	assert backend.name == "vllm"


def test_config_backend_keys():
	from config import Options
	assert "AI_BACKEND" in Options
	assert "VLLM_HOST" in Options
	assert "VLLM_TIMEOUT" in Options


def test_vllm_map_options():
	b = VLLMBackend({})
	kwargs = b._map_options(
		{'num_predict': 2048, 'num_ctx': 65536, 'temperature': 0.7, 'top_p': 0.9},
		think=False)
	assert kwargs['max_tokens'] == 2048
	assert 'num_ctx' not in kwargs
	assert kwargs['temperature'] == 0.7
	assert kwargs['top_p'] == 0.9


def test_vllm_map_options_think():
	b = VLLMBackend({})
	kwargs = b._map_options({'num_predict': 512}, think=True)
	assert kwargs['extra_body']['enable_reasoning'] is True


def test_vllm_convert_messages_plain():
	b = VLLMBackend({})
	out = b._convert_messages([{'role': 'user', 'content': 'hello'}])
	assert out == [{'role': 'user', 'content': 'hello'}]


def test_vllm_convert_messages_vision():
	import base64
	b = VLLMBackend({})
	# 1x1 transparent PNG
	png = base64.b64decode(
		"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
	b64 = base64.b64encode(png).decode('utf-8')
	out = b._convert_messages([{'role': 'user', 'content': 'what is this?', 'images': [b64]}])
	assert isinstance(out[0]['content'], list)
	assert out[0]['content'][0] == {'type': 'text', 'text': 'what is this?'}
	assert out[0]['content'][1]['type'] == 'image_url'
	assert out[0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')


def test_vllm_convert_messages_keeps_refs_out():
	b = VLLMBackend({})
	# image_refs should NOT be passed to the API (already resolved upstream)
	out = b._convert_messages([{'role': 'user', 'content': 'x', 'image_refs': ['abc']}])
	assert 'image_refs' not in out[0]


def test_detect_mime():
	import base64
	png = base64.b64decode(
		"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
	assert _detect_mime(base64.b64encode(png).decode()) == 'image/png'
	# JPEG magic
	jpg = base64.b64decode("/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAA==")
	assert _detect_mime(base64.b64encode(jpg).decode()) == 'image/jpeg'
	# Unknown -> default png
	assert _detect_mime("AAAA") == 'image/png'


class _FakeDelta:
	def __init__(self, content=None, reasoning_content=None):
		self.content = content
		self.reasoning_content = reasoning_content


class _FakeChoice:
	def __init__(self, delta):
		self.delta = delta


class _FakeUsage:
	def __init__(self, prompt_tokens, completion_tokens):
		self.prompt_tokens = prompt_tokens
		self.completion_tokens = completion_tokens


class _FakeChunk:
	def __init__(self, choice=None, usage=None):
		self.choices = [choice] if choice else []
		self.usage = usage


def test_vllm_stream_shape_with_usage():
	from src.LLMBackends.VLLMBackend import _vllm_stream
	raw = [
		_FakeChunk(_FakeChoice(_FakeDelta(reasoning_content="think part"))),
		_FakeChunk(_FakeChoice(_FakeDelta(content="hello"))),
		_FakeChunk(_FakeChoice(_FakeDelta(content=" world"))),
		_FakeChunk(usage=_FakeUsage(10, 5)),
	]
	chunks = list(_vllm_stream(raw, think=True))
	assert chunks[0].message.thinking == "think part"
	assert chunks[1].message.content == "hello"
	assert chunks[2].message.content == " world"
	assert sum(1 for c in chunks if c.done) == 1
	assert chunks[-1].done is True
	assert chunks[-1].prompt_eval_count == 10
	assert chunks[-1].eval_count == 5


def test_vllm_stream_shape_without_usage():
	from src.LLMBackends.VLLMBackend import _vllm_stream
	raw = [_FakeChunk(_FakeChoice(_FakeDelta(content="x")))]
	chunks = list(_vllm_stream(raw, think=False))
	assert sum(1 for c in chunks if c.done) == 1
	assert chunks[-1].done is True
	assert chunks[-1].prompt_eval_count is None
