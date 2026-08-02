from config import Options

def _list_personas():
	"""Scan instruct/ directory and return list of persona class names (sorted)."""
	import os
	cls_path = Options.get('INSTRUCT_PATH', 'instruct')
	base_path = Options.get('path', '')
	instruct_dir = "{}{}".format(base_path, cls_path)
	result = []
	if os.path.isdir(instruct_dir):
		for f in sorted(os.listdir(instruct_dir)):
			if f.endswith('.py') and f != '__init__.py':
				result.append(f[:-3])
	return result

def _resolve_persona(value):
	"""If value is a numeric index, resolve it to persona class name."""
	personas = _list_personas()
	try:
		idx = int(value)
		if 0 <= idx < len(personas):
			return personas[idx]
	except (ValueError, IndexError):
		pass
	return value
