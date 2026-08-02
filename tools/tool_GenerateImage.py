#
# GenerateImage tool — thin wrapper around src/ImageGenBackends.
# All backend logic (Ollama / vLLM-Omni / local diffusers), chain resolution,
# and save-and-inject live in src/ImageGenBackends.py.
#
from src.ToolParser import ToolParser
from src import ImageGenBackends


class GenerateImage():
	def __init__(self):
		self.info = {
			"name":"GenerateImage",
			"description":"Generate an image using a diffusion model (Ollama, vLLM-Omni, or local diffusers — see AI_IMAGE_BACKEND config). Saves to workout/ and injects into the conversation so the AI can see the result.",
			"parameters":{
				"returnType":"string",
				"required":["prompt"],
				"properties":{
					"prompt":{
						"type":"string",
						"description":"Text description of the image to generate"
					},
					"model":{
						"type":"string",
						"description":"Image generation model name (default: from config or 'flux-schnell')"
					},
					"width":{
						"type":"integer",
						"description":"Image width in pixels (default: 1024, range: 64-2048, multiple of 8)"
					},
					"height":{
						"type":"integer",
						"description":"Image height in pixels (default: 1024, range: 64-2048, multiple of 8)"
					},
					"steps":{
						"type":"integer",
						"description":"Number of diffusion steps (default: 4 for flux-schnell, 25 for flux)"
					},
					"seed":{
						"type":"integer",
						"description":"Random seed for reproducible generation"
					},
					"prompt_prefix":{
						"type":"string",
						"description":"Optional prefix appended to prompt (e.g. style hints for the model)"
					},
					"output":{
						"type":"string",
						"description":"Output filename (saved to workout/). If omitted, auto-generated."
					},
				},
			},
		}

	def run(self, prompt, model="", width=1024, height=1024, steps=None, seed=None, prompt_prefix="", output="", opts={}):
		print("GenerateImage.run() prompt: '{}'".format(prompt[:80]))

		# Convert types from XML strings
		width = int(width) if width else 1024
		height = int(height) if height else 1024
		steps = int(steps) if steps else None
		seed = int(seed) if seed else None
		explicit_model = bool(model)  # user explicitly named a model

		# Resolve model: param > AI_IMAGE_GEN_MODEL config > current chat model > x/flux2-klein fallback
		handle = ToolParser._current_handle
		if not model and handle:
			model = handle.Options.get('AI_IMAGE_GEN_MODEL', '') or handle.Options.get('AI_MODEL', '')
		if not model:
			model = 'x/flux2-klein'

		# Clamp dimensions and ensure multiples of 8
		width = max(64, min(2048, width))
		height = max(64, min(2048, height))
		width = (width // 8) * 8
		height = (height // 8) * 8

		# Auto-detect steps based on model name
		if steps is None:
			steps = 4 if 'turbo' in model.lower() else 25

		# Build full prompt
		full_prompt = (prompt_prefix + "\n" + prompt) if prompt_prefix else prompt

		print("GenerateImage: model={}, {}x{}, steps={}".format(model, width, height, steps))

		# --- Generate via the configured backend chain (Ollama / vLLM-Omni / diffusers) ---
		img = ImageGenBackends.generate_image(model, full_prompt, width, height, steps, seed, handle, explicit_model)
		if isinstance(img, str):
			return img

		# --- Save & inject ---
		return ImageGenBackends._save_and_inject(img, model, prompt, output, handle)
