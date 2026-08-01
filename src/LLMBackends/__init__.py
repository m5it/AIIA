#
# LLM backend factory — returns a backend instance based on Options['AI_BACKEND'].
# Ollama is imported lazily so vLLM-only installs don't need the ollama package.
#
def get_backend(Options):
	name = (Options.get('AI_BACKEND') or 'ollama').lower()
	if name == 'vllm':
		from src.LLMBackends.VLLMBackend import VLLMBackend
		return VLLMBackend(Options)
	from src.LLMBackends.OllamaBackend import OllamaBackend
	return OllamaBackend(Options)
