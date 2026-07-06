"""
MediaHelper - Utility for image/video encoding, metadata, and basic transforms
"""
import os, base64, json, time
from io import BytesIO
from PIL import Image as PILImage

class MediaHelper:
	@staticmethod
	def encode_image(path):
		"""Read an image file and return (base64_str, mime_type)."""
		if not os.path.exists(path):
			raise FileNotFoundError("Image not found: {}".format(path))
		with open(path, 'rb') as f:
			data = f.read()
		mime = _guess_mime(path)
		return base64.b64encode(data).decode('utf-8'), mime

	@staticmethod
	def image_info(path):
		"""Return image metadata dict: width, height, format, size, mode."""
		if not os.path.exists(path):
			raise FileNotFoundError("Image not found: {}".format(path))
		with PILImage.open(path) as img:
			info = {
				'width': img.width,
				'height': img.height,
				'format': img.format,
				'mode': img.mode,
				'file_size': os.path.getsize(path),
				'path': os.path.abspath(path),
			}
		return info

	@staticmethod
	def resize_image(path, max_width, max_height, out_path=None, keep_aspect=True):
		"""Resize image, maintaining aspect ratio by default. Saves to out_path or overwrites."""
		with PILImage.open(path) as img:
			if keep_aspect:
				img.thumbnail((max_width, max_height), PILImage.LANCZOS)
			else:
				img = img.resize((max_width, max_height), PILImage.LANCZOS)
			save_path = out_path or path
			img.save(save_path)
			return save_path

	@staticmethod
	def crop_image(path, left, top, right, bottom, out_path=None):
		"""Crop image to bounding box (left, top, right, bottom)."""
		with PILImage.open(path) as img:
			cropped = img.crop((left, top, right, bottom))
			save_path = out_path or path
			cropped.save(save_path)
			return save_path

	@staticmethod
	def convert_image(path, out_format='PNG', out_path=None):
		"""Convert image to another format. out_format: PNG, JPEG, WEBP, etc."""
		with PILImage.open(path) as img:
			# Handle RGBA -> RGB for JPEG
			if out_format.upper() == 'JPEG' and img.mode == 'RGBA':
				img = img.convert('RGB')
			save_path = out_path or _replace_ext(path, out_format.lower())
			img.save(save_path, format=out_format)
			return save_path

	@staticmethod
	def flip_image(path, direction='horizontal', out_path=None):
		"""Flip image. direction: 'horizontal' or 'vertical'."""
		with PILImage.open(path) as img:
			if direction == 'horizontal':
				flipped = img.transpose(PILImage.FLIP_LEFT_RIGHT)
			else:
				flipped = img.transpose(PILImage.FLIP_TOP_BOTTOM)
			save_path = out_path or path
			flipped.save(save_path)
			return save_path

	@staticmethod
	def rotate_image(path, degrees, out_path=None, expand=True):
		"""Rotate image by degrees clockwise."""
		with PILImage.open(path) as img:
			rotated = img.rotate(-degrees, expand=expand, resample=PILImage.LANCZOS)
			save_path = out_path or path
			rotated.save(save_path)
			return save_path


def _guess_mime(path):
	ext = os.path.splitext(path)[1].lower()
	mime_map = {
		'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
		'.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
		'.tiff': 'image/tiff', '.tif': 'image/tiff',
	}
	return mime_map.get(ext, 'application/octet-stream')

def _replace_ext(path, new_ext):
	base, _ = os.path.splitext(path)
	return "{}.{}".format(base, new_ext.lstrip('.'))
