#
# VLLMBackend — OpenAI-compatible backend for vLLM servers.
# Uses the openai python SDK. Returns duck-typed chunk objects matching the
# shape Handle.Stream() expects from ollama, so Handle.py needs no changes.
#
import base64
from src.LLMBackends.BaseBackend import BaseBackend

try:
	from openai import OpenAI
	HAS_OPENAI = True
except ImportError:
	OpenAI = None
	HAS_OPENAI = False


def _detect_mime(b64):
	"""Guess image mime type from the first decoded bytes of a base64 string."""
	try:
		head = base64.b64decode(b64[:64])
		if head[:8] == b'\x89PNG\r\n\x1a\n':
			return 'image/png'
		if head[:3] == b'\xff\xd8\xff':
			return 'image/jpeg'
		if head[:6] in (b'GIF87a', b'GIF89a'):
			return 'image/gif'
		if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
			return 'image/webp'
		if head[:2] == b'BM':
			return 'image/bmp'
	except Exception:
		pass
	return 'image/png'


class _Msg:
	def __init__(self, content='', thinking='', tool_calls=None):
		self.content = content
		self.thinking = thinking
		self.tool_calls = tool_calls if tool_calls is not None else []


class _Chunk:
	"""Streaming chunk shaped like an ollama ChatResponse stream element."""
	def __init__(self, message, done=False, prompt_eval_count=None, eval_count=None):
		self.message = message
		self.done = done
		self.prompt_eval_count = prompt_eval_count
		self.eval_count = eval_count


class _Response:
	"""Non-stream response shaped like an ollama ChatResponse."""
	def __init__(self, content, thinking=''):
		self.message = _Msg(content, thinking)


def _vllm_stream(raw, think):
	"""Wrap openai stream chunks into ollama-shaped stream chunks."""
	reasoning_attr = 'reasoning_content'
	done_seen = False
	for chunk in raw:
		try:
			delta = chunk.choices[0].delta
		except (IndexError, AttributeError, TypeError):
			delta = None
		# Final chunk carries usage when stream_options include_usage=True
		usage = getattr(chunk, 'usage', None)
		if usage is not None and getattr(usage, 'prompt_tokens', None) is not None:
			done_seen = True
			yield _Chunk(_Msg(), done=True,
				prompt_eval_count=usage.prompt_tokens,
				eval_count=usage.completion_tokens)
			continue
		if delta is None:
			continue
		content = getattr(delta, 'content', None) or ''
		thinking = getattr(delta, reasoning_attr, None) or ''
		if not content and not thinking:
			continue
		if thinking:
			yield _Chunk(_Msg(content='', thinking=thinking))
		if content:
			yield _Chunk(_Msg(content=content))
	# Safety: if no usage chunk arrived (stream_options unsupported), emit a
	# final done chunk so Stream() always gets its terminator.
	if not done_seen:
		yield _Chunk(_Msg(), done=True)


class VLLMBackend(BaseBackend):
	#
	@property
	def name(self):
		return "vllm"
	#
	@property
	def is_vllm(self):
		return True
	#
	def _client(self, timeout=None):
		if not HAS_OPENAI:
			raise ImportError("openai python package not installed — run: pip install openai")
		return OpenAI(
			base_url=self.Options.get('VLLM_HOST') or 'http://localhost:8000/v1',
			api_key=self.Options.get('VLLM_API_KEY') or 'EMPTY',
			timeout=timeout or self.Options.get('VLLM_TIMEOUT') or 120,
		)
	#
	def _map_options(self, options, think):
		"""Map ollama-style options to OpenAI-compatible params."""
		kwargs = {}
		if options:
			for k, v in options.items():
				if k == 'num_predict':
					kwargs['max_tokens'] = v
				elif k == 'num_ctx':
					continue  # vLLM manages context window itself
				elif k in ('temperature', 'top_p', 'top_k', 'seed', 'stop',
							'frequency_penalty', 'presence_penalty', 'max_tokens'):
					kwargs[k] = v
				# other ollama-specific options are ignored
		if think:
			body = kwargs.setdefault('extra_body', {})
			body['enable_reasoning'] = True
		return kwargs
	#
	def _convert_messages(self, messages):
		"""Convert ollama-style messages (content + images:[base64])
		to OpenAI-compatible content arrays for vision."""
		out = []
		for msg in messages:
			if not isinstance(msg, dict):
				out.append(msg)
				continue
			images = msg.get('images')
			role = msg.get('role', 'user')
			if images:
				content = []
				if msg.get('content'):
					content.append({'type': 'text', 'text': msg['content']})
				for b64 in images:
					content.append({'type': 'image_url',
						'image_url': {'url': 'data:{};base64,{}'.format(_detect_mime(b64), b64)}})
				out.append({'role': role, 'content': content})
			else:
				out.append({'role': role, 'content': msg.get('content', '')})
		return out
	#
	def chat(self, model, messages, stream=True, options=None, think=False, timeout=None):
		if not HAS_OPENAI:
			raise ImportError("openai python package not installed — run: pip install openai")
		client = self._client(timeout)
		kwargs = self._map_options(options, think)
		converted = self._convert_messages(messages)
		if stream:
			kwargs.setdefault('stream_options', {'include_usage': True})
			raw = client.chat.completions.create(
				model=model, messages=converted, stream=True, **kwargs)
			return _vllm_stream(raw, think)
		resp = client.chat.completions.create(
			model=model, messages=converted, stream=False, **kwargs)
		content = resp.choices[0].message.content or '' if resp.choices else ''
		thinking = ''
		msg = resp.choices[0].message if resp.choices else None
		if msg is not None:
			thinking = getattr(msg, 'reasoning_content', None) or ''
		return _Response(content, thinking)
	#
	def list_models(self):
		if not HAS_OPENAI:
			return []
		try:
			return [m.id for m in self._client().models.list()]
		except Exception:
			return []
