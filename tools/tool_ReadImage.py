import os, base64
from src.MediaHelper import MediaHelper
from src.ToolParser import ToolParser

class ReadImage():
	def __init__(self):
		self.info = {
			"name":"ReadImage",
			"description":"Read an image file, return its metadata (dimensions, format, size), and inject the image into the conversation for the AI to analyze.",
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
			b64, mime = MediaHelper.encode_image(fileName)
		except Exception as e:
			return "Error reading image: {}".format(e)

		# Inject image into conversation as a user message
		handle = ToolParser._current_handle
		if handle:
			content = prompt if prompt else "Image: {} ({}x{}, {})".format(
				os.path.basename(fileName), info['width'], info['height'], info['format'])
			handle.Response('user', {
				'content': content,
				'images': [b64],
			})

		meta = "Image: {}\n  Dimensions: {}x{}\n  Format: {}\n  Mode: {}\n  File size: {} bytes".format(
			fileName, info['width'], info['height'], info['format'], info['mode'], info['file_size'])

		if prompt:
			meta += "\n  Prompt: {}".format(prompt)
		if not handle:
			meta += "\n  (Warning: no active handle — image was NOT injected into conversation)"
		else:
			vision_note = handle.Options.get('AI_VISION_NOTE', '')
			current = handle.Options.get('AI_MODEL', '')
			if vision_note and current:
				meta += "\n  Note: If the AI cannot see the image, switch to a vision model with !MODEL (e.g. qwen3-vl:latest)"

		return meta
