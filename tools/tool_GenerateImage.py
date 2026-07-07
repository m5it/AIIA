import os, base64, uuid
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
from ollama import Client
from src.ToolParser import ToolParser

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

		# Resolve model: param > AI_IMAGE_GEN_MODEL config > current chat model > flux-schnell fallback
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

		# Build generation options
		gen_options = {}
		if seed is not None:
			gen_options['seed'] = seed

		# Build full prompt
		full_prompt = (prompt_prefix + "\n" + prompt) if prompt_prefix else prompt

		print("GenerateImage: model={}, {}x{}, steps={}".format(model, width, height, steps))

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
			client = Client()
			res = client.generate(
				model=model,
				prompt=full_prompt,
				width=width,
				height=height,
				steps=steps,
				options=gen_options if gen_options else None,
			)
		except Exception as e:
			err = str(e)
			if 'not found' in err.lower():
				return "Error: Model '{}' not found. Pull it first: ollama pull {}".format(model, model)
			return "Error generating image: {}".format(err)

		if not res.image:
			text = res.response or '(empty)'
			return "No image was generated (model returned text instead). Response: {}".format(text[:500])

		# Decode base64 image
		try:
			img_data = base64.b64decode(res.image)
			img = PILImage.open(BytesIO(img_data))
			# Ensure RGB mode for consistent saving
			if img.mode in ('RGBA', 'LA', 'P'):
				img = img.convert('RGBA')
		except Exception as e:
			return "Error decoding generated image data: {}".format(e)

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
			out_name, img.width, img.height, prompt[:200])
		if handle:
			handle.Response('user', {
				'content': content,
				'images': [b64_inject],
			})

		result = (
			"Image generated: {}\n"
			"  Model: {}\n"
			"  Dimensions: {}x{}\n"
			"  File: {}\n"
			"  Size: {} bytes\n"
			"  Prompt: {}".format(out_name, model, img.width, img.height, out_path, file_size, prompt)
		)
		return result


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
