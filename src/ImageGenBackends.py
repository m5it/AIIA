#
# ImageGenBackends — image generation backends for the GenerateImage tool.
# Each backend is a plain function returning a PIL Image on success, None when
# the backend is unavailable/fails (caller falls through), or an error string
# for fatal per-backend problems (e.g. diffusers inference errors).
#
# Backend selection is driven by Options:
#   AI_BACKEND        — chat LLM backend ("ollama" | "vllm")
#   AI_IMAGE_BACKEND  — image backend override: "auto" (follow AI_BACKEND),
#                       "ollama", "vllm", or "local" (diffusers)
#
import os, sys, base64, uuid
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage

# Suppress library noise before any diffusers/transformers/torch imports
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['DIFFUSERS_VERBOSITY'] = 'error'
os.environ['TQDM_DISABLE'] = '1'

# Diffusers pipeline cache (module-level, survives dynamic reloads in same process)
_diffusers_pipeline = None
_diffusers_pipeline_model = None


def generate_image(model, prompt, width, height, steps, seed, handle, explicit_model=False):
	"""Try each configured image backend in order until one produces an image.

	Chain: primary (from AI_IMAGE_BACKEND / AI_BACKEND) → the other remote
	backend → local diffusers. Returns a PIL Image, an error string, or None."""
	img = None
	attempted = []
	for backend in _resolve_image_backends(handle):
		attempted.append(backend)
		if backend == 'vllm':
			print("GenerateImage: trying vLLM-Omni backend...")
			img = _generate_vllm(model, prompt, width, height, steps, seed, handle, explicit_model)
		elif backend == 'ollama':
			print("GenerateImage: trying Ollama backend...")
			img = _generate_ollama(model, prompt, width, height, steps, seed)
		else:
			print("GenerateImage: trying local diffusers backend...")
			img = _generate_diffusers(model, prompt, width, height, steps, seed)
		if img is not None and not isinstance(img, str):
			break

	if img is None:
		return "Image generation failed — tried backends: {}".format(", ".join(attempted))
	if isinstance(img, str):
		return img
	return img


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------

def _resolve_image_backends(handle):
	"""Return the ordered list of image-generation backends to try.

	Primary comes from AI_IMAGE_BACKEND ("auto" follows AI_BACKEND), then the
	other remote backend as a cross-backend fallback, then local diffusers."""
	chat_backend = (handle.Options.get('AI_BACKEND') if handle else 'ollama') or 'ollama'
	chat_backend = chat_backend.lower()
	image_backend = (handle.Options.get('AI_IMAGE_BACKEND') if handle else 'auto') or 'auto'
	image_backend = image_backend.lower()
	if image_backend not in ('auto', 'ollama', 'vllm', 'local'):
		image_backend = 'auto'

	if image_backend == 'auto':
		primary = chat_backend if chat_backend in ('ollama', 'vllm') else 'ollama'
	else:
		primary = image_backend

	if primary == 'local':
		return ['local']

	chain = [primary]
	chain.append('vllm' if primary == 'ollama' else 'ollama')
	chain.append('local')
	return chain


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _generate_vllm(model, prompt, width, height, steps, seed, handle, explicit_model=False):
	"""Generate via a vLLM-Omni image server (OpenAI DALL-E compatible API).

	Endpoints: POST {VLLM_HOST}/images/generations. Each vLLM-Omni instance
	serves a single diffusion model, so `model` is only sent when the user
	explicitly requested one (mismatched names 400). Returns PIL Image on
	success or None on failure (caller falls through to the next backend)."""
	try:
		import requests
		host = (handle.Options.get('VLLM_HOST') if handle else '') or 'http://localhost:8000/v1'
		api_key = handle.Options.get('VLLM_API_KEY') if handle else ''
		timeout = (handle.Options.get('VLLM_TIMEOUT') if handle else None) or 120

		headers = {'Content-Type': 'application/json'}
		if api_key:
			headers['Authorization'] = 'Bearer {}'.format(api_key)

		body = {
			'prompt': prompt,
			'size': '{}x{}'.format(width, height),
			'n': 1,
			'response_format': 'b64_json',
		}
		if explicit_model:
			body['model'] = model
		if steps is not None:
			body['num_inference_steps'] = steps
		if seed is not None:
			body['seed'] = seed

		resp = requests.post(
			host.rstrip('/') + '/images/generations',
			json=body, headers=headers, timeout=timeout)
		resp.raise_for_status()
		items = resp.json().get('data') or []
		if not items:
			return None
		b64 = items[0].get('b64_json')
		if not b64:
			return None
		img = PILImage.open(BytesIO(base64.b64decode(b64)))
		if img.mode in ('RGBA', 'LA', 'P'):
			img = img.convert('RGBA')
		return img
	except Exception as e:
		print("  vLLM image generation failed: {}".format(e))
		return None


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
		from ollama import Client
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
	clean_model = model.split(':')[0]  # strip :latest etc.
	hf_model = HF_MODEL_MAP.get(clean_model, clean_model)

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
		# Strip workout/ prefix to prevent path duplication
		if out_name.startswith('workout/'):
			out_name = out_name[len('workout/'):]
	else:
		ts = datetime.now().strftime('%Y%m%d_%H%M%S')
		uid = uuid.uuid4().hex[:8]
		out_name = "gen_{}_{}.png".format(ts, uid)

	# Ensure workout/ directory exists (always cwd-relative)
	workout_dir = 'workout'
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
