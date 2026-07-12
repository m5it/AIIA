"""
MediaHelper - Utility for image/video encoding, metadata, and basic transforms
"""
import os, base64, json, time, hashlib
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


class ImageCache:
	"""Cache image data on disk, reference by hash in chat history."""

	@staticmethod
	def get_cache_base(handle=None):
		"""Return the image cache directory path."""
		if handle:
			custom = handle.Options.get('AI_IMAGE_CACHE_PATH', '')
			if custom:
				return custom
		default = os.path.expanduser("~/.config/aiia/img_cache")
		os.makedirs(default, exist_ok=True)
		return default

	@staticmethod
	def save_to_cache(image_bytes, ext='.png'):
		"""Save image bytes to cache, return (sha256_hash, filename)."""
		h = hashlib.sha256(image_bytes).hexdigest()
		cache_dir = ImageCache.get_cache_base()
		fname = "{}{}".format(h, ext)
		fpath = os.path.join(cache_dir, fname)
		if not os.path.exists(fpath):
			with open(fpath, 'wb') as f:
				f.write(image_bytes)
		return h, fname

	@staticmethod
	def resolve_ref(hash_str):
		"""Given a SHA256 hash, find the cached image and return (base64_str, mime_type)."""
		cache_dir = ImageCache.get_cache_base()
		for fname in os.listdir(cache_dir):
			if fname.startswith(hash_str):
				fpath = os.path.join(cache_dir, fname)
				with open(fpath, 'rb') as f:
					data = f.read()
				mime = _guess_mime(fname)
				return base64.b64encode(data).decode('utf-8'), mime
		raise FileNotFoundError("Image cache entry not found: {}".format(hash_str))

	@staticmethod
	def resolve_all(msgs):
		"""Iterate messages, resolve image_refs to actual images in-place.
		Modifies the list in-place — intended for use on a deep copy."""
		for msg in msgs:
			refs = msg.pop('image_refs', None)
			if refs:
				images = []
				for ref in refs:
					try:
						b64, mime = ImageCache.resolve_ref(ref)
						images.append(b64)
					except FileNotFoundError:
						continue
				if images:
					msg['images'] = images

	@staticmethod
	def cleanup(max_age_hours=24):
		"""Remove cache files older than max_age_hours."""
		cache_dir = ImageCache.get_cache_base()
		now = time.time()
		for fname in os.listdir(cache_dir):
			fpath = os.path.join(cache_dir, fname)
			if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > max_age_hours * 3600:
				os.remove(fpath)

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
