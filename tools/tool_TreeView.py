import os

class TreeView():
	cache_ttl = 300

	def __init__(self):
		self.info = {
			"name":"TreeView",
			"description":"Generate an ASCII tree view of the project directory structure. Respects depth limits and excludes common noise dirs.",
			"parameters":{
				"returnType":"string",
				"required":[],
				"properties":{
					"path":{
						"type":"string",
						"description":"(Optional) Root path. Default: current directory."
					},
					"depth":{
						"type":"number",
						"description":"(Optional) Max recursion depth. Default: 3, 0 = unlimited."
					},
					"pattern":{
						"type":"string",
						"description":"(Optional) Show only files matching this glob pattern (e.g. *.py). Directories always shown."
					},
					"showHidden":{
						"type":"string",
						"description":"(Optional) Set 'true' to include hidden files/dirs (starting with .). Default: false."
					},
				},
			},
		}
		self._exclude_dirs = {
			'.git', '.venv', 'node_modules', '__pycache__',
			'.mypy_cache', '.pytest_cache', '.ruff_cache',
			'history', 'plans', '.gitlab', '.github',
		}
	#
	def run(self, path=".", depth=3, pattern="", showHidden="false", opts={}):
		root = path if path else "."
		if not os.path.isdir(root):
			return "Error: path '{}' is not a directory.".format(root)
		try:
			max_depth = int(depth)
		except Exception:
			return "Error: depth must be a number."
		if max_depth < 0:
			max_depth = 0
		show_hidden = showHidden and str(showHidden).strip().lower() == 'true'

		lines = []
		lines.append(os.path.basename(os.path.abspath(root)) or ".")
		self._walk(root, 0, max_depth, "", [], pattern, show_hidden, lines)
		return "\n".join(lines)
	#
	def _walk(self, dir_path, current_depth, max_depth, prefix, pipe_stack, pattern, show_hidden, lines):
		if max_depth > 0 and current_depth >= max_depth:
			return
		try:
			entries = sorted(os.scandir(dir_path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
		except PermissionError:
			lines.append(prefix + "  [permission denied]")
			return
		except OSError:
			return

		filtered = []
		for e in entries:
			name = e.name
			if name in self._exclude_dirs:
				continue
			if not show_hidden and name.startswith('.'):
				continue
			if e.is_dir(follow_symlinks=False):
				filtered.append((True, e))
			else:
				if pattern:
					import fnmatch
					if not fnmatch.fnmatch(name, pattern):
						continue
				filtered.append((False, e))

		for i, (is_dir, entry) in enumerate(filtered):
			is_last = i == len(filtered) - 1
			connector = "└── " if is_last else "├── "
			lines.append(prefix + connector + entry.name + ("/" if is_dir else ""))
			if is_dir:
				extension = "    " if is_last else "│   "
				self._walk(entry.path, current_depth + 1, max_depth, prefix + extension, pipe_stack + [not is_last], pattern, show_hidden, lines)
