import os, base64
from io import BytesIO
from PIL import Image as PILImage
from src.MediaHelper import MediaHelper, ImageCache
from src.ToolParser import ToolParser

class ReadImage():
	def __init__(self):
		self.info = {
			"name":"ReadImage",
			"description":"Read an image file, return its metadata (dimensions, format, size), and inject the image into the conversation for the AI to analyze. Large images are automatically resized to fit context limits.",
			"parameters":{
				"returnType":"string",
				"required":['fileName'],
				"properties":{
					"fileName":{
						"type":"string",
						"description":"Path to the image file (PNG, JPEG, WEBP, GIF, etc.)"
					},
					"prompt":{
						"type":"string",
						"description":"Optional prompt or question about the image for the AI"
					},
				},
			},
		}
	def run(self, fileName, prompt="", opts={}):
		print("ReadImage.run() STARTING on name: {}".format(fileName))
		if not os.path.exists(fileName):
			return "Error: File `{}` not found".format(fileName)

		try:
			info = MediaHelper.image_info(fileName)
			handle = ToolParser._current_handle
			max_dim = 0
			if handle:
				max_dim = handle.Options.get('MAX_INJECT_IMAGE_DIMENSION', 1024)
				max_inject = handle.Options.get('AI_MAX_IMAGE_INJECT', 3145728)

			# Resize if needed to keep request body size reasonable
			img_for_cache = None
			resized_w, resized_h = info['width'], info['height']
			if max_dim > 0 and (info['width'] > max_dim or info['height'] > max_dim):
				with PILImage.open(fileName) as img:
					img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
					buf = BytesIO()
					img.save(buf, format=info['format'] or 'PNG')
					img_for_cache = buf.getvalue()
					resized_w, resized_h = img.size
			else:
				with open(fileName, 'rb') as f:
					img_for_cache = f.read()

			# Check size against injection limit, downscale further if needed
			if handle and max_inject and len(img_for_cache) > max_inject:
				with PILImage.open(fileName) as img:
					# Progressively shrink until under limit
					scale = 0.75
					while len(img_for_cache) > max_inject and img.size[0] > 100 and img.size[1] > 100:
						new_w = int(img.size[0] * scale)
						new_h = int(img.size[1] * scale)
						img = img.resize((new_w, new_h), PILImage.LANCZOS)
						buf = BytesIO()
						img.save(buf, format='JPEG', quality=85)
						img_for_cache = buf.getvalue()
						scale *= 0.75
					resized_w, resized_h = img.size
				if handle:
					handle.hLG.echo(
						"  Compressed to {}x{} JPEG ({:.1f}KB) to fit injection limit".format(
							resized_w, resized_h, len(img_for_cache) / 1024),
						{'color':True, 'colorValue':'yellow','debugOnly':False})

			# Save to image cache, get hash reference
			ext = os.path.splitext(fileName)[1].lower() or '.png'
			img_hash, _ = ImageCache.save_to_cache(img_for_cache, ext)
		except Exception as e:
			return "Error reading image: {}".format(e)

		# Inject image into conversation as a user message (using lightweight ref)
		if handle:
			content = prompt if prompt else "Image: {} ({}x{}, {})".format(
				os.path.basename(fileName), info['width'], info['height'], info['format'])
			handle.Response('user', {
				'content': content,
				'image_refs': [img_hash],
			})
			if resized_w != info['width'] or resized_h != info['height']:
				handle.hLG.echo(
					"  Resized {}x{} → {}x{} for injection".format(
						info['width'], info['height'], resized_w, resized_h),
					{'color':True, 'colorValue':'yellow','debugOnly':False})

		meta = "Image: {}\n  Dimensions: {}x{}\n  Format: {}\n  Mode: {}\n  File size: {} bytes".format(
			fileName, info['width'], info['height'], info['format'], info['mode'], info['file_size'])

		if resized_w != info['width'] or resized_h != info['height']:
			meta += "\n  (resized to {}x{} for injection)".format(resized_w, resized_h)

		if prompt:
			meta += "\n  Prompt: {}".format(prompt)
		if not handle:
			meta += "\n  (Warning: no active handle — image was NOT injected into conversation)"
		else:
			vision_note = handle.Options.get('AI_VISION_NOTE', '')
			current = handle.Options.get('AI_MODEL', '')
			if vision_note and current:
				meta += "\n  Note: {}".format(vision_note)

		return meta
