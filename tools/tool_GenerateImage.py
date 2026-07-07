import os, sys, base64, uuid
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
from ollama import Client
from src.ToolParser import ToolParser

# Diffusers pipeline cache (module-level, survives dynamic reloads in same process)
_diffusers_pipeline = None
_diffusers_pipeline_model = None

class GenerateImage():
	def __init__(self):
		self.info = {
			"name":"GenerateImage",
			"description":"Generate an image using a diffusion model (e.g. flux-schnell, flux). Saves to workout/ and injects into the conversation so the AI can see the result.",
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

		# --- Try Ollama backend first ---
		img = _generate_ollama(model, full_prompt, width, height, steps, seed)

		# If Ollama failed, try diffusers fallback
		if img is None:
			print("Ollama generate failed — trying diffusers fallback...")
			img = _generate_diffusers(model, full_prompt, width, height, steps, seed)

		# If both failed, return the error
		if isinstance(img, str):
			return img

		# --- Save & inject ---
		return _save_and_inject(img, model, prompt, output, handle)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _generate_ollama(model, prompt, width, height, steps, seed):
	"""Try generating via Ollama Client.generate(). Returns PIL Image or None on failure."""
	# Ollama diffusion models require MLX (Apple) — skip on Linux, go straight to diffusers
	if sys.platform.startswith('linux'):
		return None
	# Stop any loaded ollama model that differs from the gen model (free GPU memory)
	try:
		import subprocess
		r = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=10)
		if r.returncode == 0:
			for line in r.stdout.strip().split('\n')[1:]:
				parts = line.split()
				if parts and parts[0] and parts[0] != model:
					subprocess.run(['ollama', 'stop', parts[0]], capture_output=True, timeout=10)
					print("  Freed memory: stopped {}".format(parts[0]))
	except Exception:
		pass

	try:
		gen_options = {}
		if seed is not None:
			gen_options['seed'] = seed
		client = Client()
		res = client.generate(
			model=model,
			prompt=prompt,
			width=width,
			height=height,
			steps=steps,
			options=gen_options if gen_options else None,
		)
	except Exception:
		return None  # fall through to diffusers

	if not res.image:
		return None  # text response — not an image

	try:
		img_data = base64.b64decode(res.image)
		img = PILImage.open(BytesIO(img_data))
		if img.mode in ('RGBA', 'LA', 'P'):
			img = img.convert('RGBA')
		return img
	except Exception:
		return None


def _generate_diffusers(model, prompt, width, height, steps, seed):
	"""Fallback image generation via HuggingFace diffusers (Linux-compatible).
	Returns PIL Image on success, or error string on failure."""
	global _diffusers_pipeline, _diffusers_pipeline_model

	try:
		import torch
		from diffusers import DiffusionPipeline
	except ImportError:
		return ("diffusers backend not available. Install with:\n"
			"  pip install diffusers torch transformers accelerate")

	# Map Ollama model names to HuggingFace model IDs
	# Note: black-forest-labs/FLUX.1-schnell is gated (requires HF login)
	# Using open Stability AI models instead
	HF_MODEL_MAP = {
		'x/flux2-klein': 'stabilityai/sdxl-turbo',
		'x/z-image-turbo': 'stabilityai/sdxl-turbo',
		'flux-schnell': 'stabilityai/sdxl-turbo',
		'sdxl-turbo': 'stabilityai/sdxl-turbo',
	}
	hf_model = HF_MODEL_MAP.get(model, model)

	if '/' not in hf_model:
		return ("Model '{}' not recognized for diffusers backend. "
			"Use a HuggingFace model ID (e.g. 'black-forest-labs/FLUX.1-schnell')".format(model))

	# Reuse cached pipeline if same model
	if _diffusers_pipeline is None or _diffusers_pipeline_model != hf_model:
		_diffusers_pipeline = None
		_diffusers_pipeline_model = None
		print("Loading diffusers pipeline: {} ...".format(hf_model))
		try:
			dtype = torch.float16 if torch.cuda.is_available() else torch.float32
			pipe = DiffusionPipeline.from_pretrained(hf_model, torch_dtype=dtype)
			if torch.cuda.is_available():
				pipe = pipe.to("cuda")
			_diffusers_pipeline = pipe
			_diffusers_pipeline_model = hf_model
		except Exception as e:
			return "Failed to load diffusers model '{}': {}".format(hf_model, e)

	try:
		generator = torch.Generator(device="cpu").manual_seed(seed) if seed is not None else None
		result = _diffusers_pipeline(
			prompt=prompt,
			width=width,
			height=height,
			num_inference_steps=steps or 4,
			generator=generator,
		)
		img = result.images[0]
		if img.mode in ('RGBA', 'LA', 'P'):
			img = img.convert('RGBA')
		return img
	except Exception as e:
		return "Diffusers inference failed: {}".format(e)


# ---------------------------------------------------------------------------
# Save & inject helper
# ---------------------------------------------------------------------------

def _save_and_inject(img, model, original_prompt, output, handle):
	"""Save PIL Image to workout/, inject into conversation, return result string."""
	# Determine output filename
	if output:
		out_name = output
	else:
		ts = datetime.now().strftime('%Y%m%d_%H%M%S')
		uid = uuid.uuid4().hex[:8]
		out_name = "gen_{}_{}.png".format(ts, uid)

	# Ensure workout/ directory exists
	workout_dir = 'workout'
	if handle:
		base_path = handle.Options.get('path', '')
		if base_path:
			workout_dir = os.path.join(base_path, 'workout')
	os.makedirs(workout_dir, exist_ok=True)

	out_path = os.path.join(workout_dir, out_name)

	# Save image (PNG by default, or match extension if user provided one)
	fmt = _guess_save_format(out_name)
	img.save(out_path, fmt)
	file_size = os.path.getsize(out_path)

	# Encode saved image for conversation injection
	with open(out_path, 'rb') as f:
		b64_inject = base64.b64encode(f.read()).decode('utf-8')

	# Inject into conversation as a user message
	content = "Generated image: {} ({}x{}, prompt: '{}')".format(
		out_name, img.width, img.height, original_prompt[:200])
	if handle:
		handle.Response('user', {
			'content': content,
			'images': [b64_inject],
		})

	return (
		"Image generated: {}\n"
		"  Model: {}\n"
		"  Dimensions: {}x{}\n"
		"  File: {}\n"
		"  Size: {} bytes\n"
		"  Prompt: {}".format(out_name, model, img.width, img.height, out_path, file_size, original_prompt)
	)


def _guess_save_format(filename):
	ext = os.path.splitext(filename)[1].lower()
	return {
		'.jpg': 'JPEG', '.jpeg': 'JPEG',
		'.png': 'PNG',
		'.webp': 'WebP',
		'.bmp': 'BMP',
		'.gif': 'GIF',
		'.tiff': 'TIFF', '.tif': 'TIFF',
	}.get(ext, 'PNG')
