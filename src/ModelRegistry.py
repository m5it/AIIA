import fnmatch

MODEL_DB = [
	# (pattern, context_size, vision, think, num_predict, description)
	("qwen3-vl:*",             32768,  True,  False, 8192,  "Qwen 3 Vision"),
	("llama3.2-vision:*",      131072, True,  False, 16384, "Meta Llama 3.2 Vision"),
	("llama3.2:*",             131072, False, False, 16384, "Meta Llama 3.2"),
	("llama3.1:*",             131072, False, False, 16384, "Meta Llama 3.1"),
	("gemma3:*",               8192,   True,  False, 4096,  "Google Gemma 3"),
	("gemma4:*",               32768,  False, False, 8192,  "Google Gemma 4"),
	("qwen3:*",                131072, False, False, 16384, "Qwen 3"),
	("qwen3-coder:*",          131072, False, False, 16384, "Qwen 3 Coder"),
	("qwen3.5:*",              131072, False, False, 16384, "Qwen 3.5"),
	("minicpm-v:*",            8192,   True,  False, 4096,  "MiniCPM-V Vision"),
	("ministral-3:*",          32768,  False, False, 8192,  "Mistral Ministral 3B"),
	("mistral-small3.2:*",     131072, False, False, 16384, "Mistral Small 3.2"),
	("kimi-k2.5:cloud",        131072, False, True,  16384, "Kimi K2.5 Cloud"),
	("deepseek-r1:*",          65536,  False, True,  16384, "DeepSeek R1"),
	# Image generation models (context_size=0 = not a chat model)
	("x/flux2-klein:*",        0,      False, False, 0,     "FLUX.2 Klein image generation"),
	("x/z-image-turbo:*",      0,      False, False, 0,     "Z-Image Turbo generation"),
]

def lookup(name):
	"""Look up model capabilities by name. Returns dict or None."""
	name_lower = name.lower().strip()
	for pattern, ctx, vision, think, num_predict, desc in MODEL_DB:
		if fnmatch.fnmatch(name_lower, pattern.lower()):
			return {
				'context_size': ctx,
				'vision': vision,
				'think': think,
				'num_predict': num_predict,
				'description': desc,
			}
	return None

def apply(Options, model_name):
	"""Apply model capabilities to the Options dict.
	Returns list of human-readable change strings (empty if no changes)."""
	caps = lookup(model_name)
	if caps is None:
		return _apply_unknown(Options)

	changes = []
	if caps['context_size'] > 0:
		# Chat-related options only apply to chat models
		_apply_context(Options, caps, changes)
		_apply_cap_flags(Options, caps, changes)
		_apply_num_predict(Options, caps, changes)
	return changes

def _apply_unknown(Options):
	"""Model not in the registry — reset capability flags that may have been
	inherited from a previously active model (e.g. AI_THINK left on after
	switching away from a thinking model), which would cause a hard error
	(e.g. Ollama HTTP 400) when the new model does not support them.
	Returns list of human-readable change strings (empty if no changes)."""
	changes = []
	old_think = Options.get('AI_THINK', False)
	if old_think:
		Options['AI_THINK'] = False
		changes.append("Thinking: on -> off (unknown model, no registry entry)")
	old_vision = Options.get('AI_VISION_ENABLED', False)
	if old_vision:
		Options['AI_VISION_ENABLED'] = False
		changes.append("Vision: on -> off (unknown model, no registry entry)")
	return changes

def _apply_context(Options, caps, changes):
	# Context window + num_ctx
	new_limit = caps['context_size']
	old_limit = Options.get('AI_CONTEXT_LIMIT')
	if old_limit != new_limit:
		Options['AI_CONTEXT_LIMIT'] = new_limit
		changes.append("Context: {} -> {}".format(
			old_limit if old_limit is not None else '(default)', new_limit))

	ai_opts = Options.get('AI_OPTIONS', {})
	if not isinstance(ai_opts, dict):
		ai_opts = {}
	old_num_ctx = ai_opts.get('num_ctx')
	ai_opts['num_ctx'] = new_limit
	Options['AI_OPTIONS'] = ai_opts
	if old_num_ctx != new_limit:
		changes.append("num_ctx: {} -> {}".format(
			old_num_ctx if old_num_ctx is not None else '(default)', new_limit))

def _apply_cap_flags(Options, caps, changes):
	# think / vision flags + vision note
	old_think = Options.get('AI_THINK', False)
	if old_think != caps['think']:
		Options['AI_THINK'] = caps['think']
		changes.append("Thinking: {} -> {}".format(
			'on' if old_think else 'off', 'on' if caps['think'] else 'off'))

	old_vision = Options.get('AI_VISION_ENABLED', False)
	if old_vision != caps['vision']:
		Options['AI_VISION_ENABLED'] = caps['vision']
		changes.append("Vision: {} -> {}".format(
			'on' if old_vision else 'off', 'on' if caps['vision'] else 'off'))

	if caps['vision']:
		Options['AI_VISION_NOTE'] = ""
	else:
		Options['AI_VISION_NOTE'] = (
			"This model may not support vision. "
			"Use !MODEL <vision-model> (e.g. llama3.2-vision:latest) to analyze images.")

def _apply_num_predict(Options, caps, changes):
	# num_predict
	new_np = caps['num_predict']
	old_np = Options.get('NUM_PREDICT')
	if new_np and old_np != new_np:
		Options['NUM_PREDICT'] = new_np
		changes.append("num_predict: {} -> {}".format(
			old_np if old_np is not None else '(default)', new_np))
