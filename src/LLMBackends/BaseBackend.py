#
# BaseBackend — abstract interface for LLM backends.
# Each backend wraps a specific library (ollama, vLLM/OpenAI-compatible, ...)
# and exposes a common chat() interface so src/Handle.py stays backend-agnostic.
#
class BaseBackend():
	#
	def __init__(self, Options):
		self.Options = Options
	#
	@property
	def name(self):
		return "base"
	#
	@property
	def is_vllm(self):
		return False
	#
	def chat(self, model, messages, stream=True, options=None, think=False, timeout=None):
		"""Send a chat request. Returns a stream iterator (stream=True) or a
		response object (stream=False).
		Streaming chunks must expose:
			.message.content        (str)
			.message.thinking       (str)
			.message.tool_calls     (list)
			.done                   (bool)
			.prompt_eval_count      (int)
			.eval_count             (int)
		Non-stream responses must expose .message.content and .message.thinking."""
		raise NotImplementedError
	#
	def list_models(self):
		"""Return a list of available model name strings."""
		raise NotImplementedError
