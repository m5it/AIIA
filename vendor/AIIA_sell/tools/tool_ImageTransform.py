import os, json
from src.MediaHelper import MediaHelper

class ImageTransform():
	def __init__(self):
		self.info = {
			"name":"ImageTransform",
			"description":"Transform an image: resize, crop, convert format, flip, or rotate. Saves result to workout/.",
			"parameters":{
				"returnType":"string",
				"required":['fileName', 'operation'],
				"properties":{
					"fileName":{
						"type":"string",
						"description":"Path to the source image file"
					},
					"operation":{
						"type":"string",
						"description":"Operation: resize, crop, convert, flip, rotate"
					},
					"params":{
						"type":"string",
						"description":"JSON parameters for the operation. Examples:\n  resize: {\"maxWidth\":800,\"maxHeight\":600}\n  crop: {\"left\":0,\"top\":0,\"right\":400,\"bottom\":300}\n  convert: {\"format\":\"PNG\"}\n  flip: {\"direction\":\"horizontal\"}\n  rotate: {\"degrees\":90}"
					},
					"output":{
						"type":"string",
						"description":"Output filename (saved to workout/). If omitted, auto-generated."
					},
				},
			},
		}
	def run(self, fileName, operation, params="{}", output="", opts={}):
		print("ImageTransform.run() {} on {}".format(operation, fileName))
		if not os.path.exists(fileName):
			return "Error: File `{}` not found".format(fileName)

		try:
			parsed = json.loads(params) if isinstance(params, str) else params
		except Exception as e:
			return "Error: invalid params JSON: {}".format(e)

		out_path = None
		if output:
			base_dir = os.path.dirname(fileName)
			out_path = os.path.join(base_dir, output)

		try:
			op = operation.lower()
			if op == 'resize':
				mw = int(parsed.get('maxWidth', 800))
				mh = int(parsed.get('maxHeight', 600))
				ka = parsed.get('keepAspect', True)
				result = MediaHelper.resize_image(fileName, mw, mh, out_path, ka)
			elif op == 'crop':
				l = int(parsed.get('left', 0))
				t = int(parsed.get('top', 0))
				r = int(parsed.get('right', 100))
				b = int(parsed.get('bottom', 100))
				result = MediaHelper.crop_image(fileName, l, t, r, b, out_path)
			elif op == 'convert':
				fmt = parsed.get('format', 'PNG')
				result = MediaHelper.convert_image(fileName, fmt, out_path)
			elif op == 'flip':
				dir_ = parsed.get('direction', 'horizontal')
				result = MediaHelper.flip_image(fileName, dir_, out_path)
			elif op == 'rotate':
				deg = float(parsed.get('degrees', 90))
				expand = parsed.get('expand', True)
				result = MediaHelper.rotate_image(fileName, deg, out_path, expand)
			else:
				return "Error: unknown operation '{}'. Use: resize, crop, convert, flip, rotate".format(operation)

			info = MediaHelper.image_info(result)
			return "Transformed image saved to: {}\n  Dimensions: {}x{}\n  Format: {}".format(
				result, info['width'], info['height'], info['format'])
		except Exception as e:
			return "Error during {}: {}".format(operation, e)
