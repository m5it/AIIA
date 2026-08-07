#--
# class CommandsCache — write-tool file buffer cache commands
class CommandsCache():
	#
	def CMD_CACHE(self, inp=""):
		"""!CACHE [SHOW <file> | CLEAR] — view/clear the write-tool file buffer cache."""
		cache = getattr(self.handle, 'file_buffer_cache', None) or {}
		parts = [p for p in inp.split(None, 2) if p]
		#
		if parts and parts[0].upper() == 'CLEAR':
			self.handle.file_buffer_cache = {}
			print("File buffer cache cleared ({} entries).".format(len(cache)))
			return
		#
		if parts and parts[0].upper() == 'SHOW':
			key = parts[1] if len(parts) > 1 else ''
			content = cache.get(key)
			if content is None:
				matches = [k for k in cache if key in k]
				if len(matches) == 1:
					key = matches[0]
					content = cache[key]
			if content is None:
				print("Cached file '{}' not found. Use !CACHE to list cached files.".format(key))
				return
			preview = content if len(content) <= 1000 else content[:1000] + "\n... ({} chars total)".format(len(content))
			print("### {} ({} chars)\n{}".format(key, len(content), preview))
			return
		#
		if not cache:
			print("File buffer cache is empty. It is populated when write tools "
				"(WriteFile/CreateFile/AppendFile/ReplaceLine/Sed) run while a plan is active.")
			return
		total = sum(len(c) for c in cache.values())
		print("File buffer cache ({} files, {} chars):".format(len(cache), total))
		for fileName, content in cache.items():
			print("- {} ({} chars)".format(fileName, len(content)))
