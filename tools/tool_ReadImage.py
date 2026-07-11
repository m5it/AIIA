import os, base64
from io import BytesIO
from PIL import Image as PILImage
from src.MediaHelper import MediaHelper
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

			# Resize if needed to keep request body size reasonable
			if max_dim > 0 and (info['width'] > max_dim or info['height'] > max_dim):
				with PILImage.open(fileName) as img:
					img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
					buf = BytesIO()
					img.save(buf, format=info['format'] or 'PNG')
					b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
					# guess mime from original file extension
					ext = os.path.splitext(fileName)[1].lower()
					mime_map = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg',
						'.gif':'image/gif','.webp':'image/webp','.bmp':'image/bmp'}
					mime = mime_map.get(ext, 'image/png')
				resized_w, resized_h = img.size
			else:
				b64, mime = MediaHelper.encode_image(fileName)
				resized_w, resized_h = info['width'], info['height']
		except Exception as e:
			return "Error reading image: {}".format(e)

		# Inject image into conversation as a user message
		if handle:
			content = prompt if prompt else "Image: {} ({}x{}, {})".format(
				os.path.basename(fileName), info['width'], info['height'], info['format'])
			handle.Response('user', {
				'content': content,
				'images': [b64],
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
