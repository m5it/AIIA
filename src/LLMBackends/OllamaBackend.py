#
# OllamaBackend — thin wrapper around the official ollama python client.
# Returns native ollama ChatResponse objects / streams so Handle.py's
# existing Stream()/Parse() consumption works unchanged.
#
import time
from src.LLMBackends.BaseBackend import BaseBackend

try:
	import ollama
	from ollama import Client
	HAS_OLLAMA = True
except ImportError:
	ollama = None
	Client = None
	HAS_OLLAMA = False


class OllamaBackend(BaseBackend):
	#
	@property
	def name(self):
		return "ollama"
	#
	def _client(self, timeout=None):
		opts = {}
		if timeout:
			opts['timeout'] = timeout
		return Client(**opts)
	#
	def chat(self, model, messages, stream=True, options=None, think=False, timeout=None):
		if not HAS_OLLAMA:
			raise ImportError("ollama python package not installed — run: pip install ollama")
		params = {
			'model': model,
			'messages': messages,
			'stream': stream,
		}
		if options:
			params['options'] = options
		if think:
			params['think'] = think
		return self._client(timeout).chat(**params)
	#
	def list_models(self):
		if not HAS_OLLAMA:
			return []
		return [m.get('name') or m.model for m in ollama.list().models]
