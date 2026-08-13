import os, json, time
from src.functions import fwrite

class TipManager():
	#
	def __init__(self, opts):
		self.handle = opts.get('handle')
		self.handle.hLG.echo("TipManager.__init__() STARTED!",{'color':True})
		self.base_path = self.handle.Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
	#
	def _path(self, source, title=None):
		p = os.path.join(self.base_path, source)
		if title:
			p = os.path.join(p, title)
		return p
	#
	def _list_titles(self, source):
		"""List tip titles under a source. Recurses into project subdirs.
		Returns a list of (source_path, title) tuples."""
		path = self._path(source)
		if not os.path.isdir(path):
			return []
		result = []
		for entry in sorted(os.listdir(path)):
			entry_path = os.path.join(path, entry)
			if not os.path.isdir(entry_path):
				continue
			files = [f for f in os.listdir(entry_path) if f.endswith('.json')]
			subdirs = [f for f in os.listdir(entry_path)
					   if os.path.isdir(os.path.join(entry_path, f))]
			if files and not subdirs:
				# Leaf directory: a tip title.
				result.append((source, entry))
			elif subdirs:
				# Project subdirectory: recurse.
				for sub_source, sub_title in self._list_titles("{}/{}".format(source, entry)):
					result.append((sub_source, sub_title))
		return result
	#
	def _list_entries(self, source, title):
		path = self._path(source, title)
		if not os.path.isdir(path):
			return []
		files = sorted([f for f in os.listdir(path) if f.endswith('.json')])
		result = []
		for f in files:
			try:
				with open(os.path.join(path, f)) as fp:
					result.append(json.load(fp))
			except: pass
		return result
	#
	def save(self, title, source, entries):
		path = self._path(source, title)
		os.makedirs(path, exist_ok=True)
		data = {
			'title': title,
			'source': source,
			'saved_at': int(time.time()),
			'sessionId': self.handle.Options.get('AI_SESS_ID', 0),
			'entries': entries,
		}
		fname = "{}.json".format(data['saved_at'])
		fwrite(os.path.join(path, fname), json.dumps(data), True)
		return data
	#
	def get_last_exchange(self):
		msgs = self.handle.hHM.msgs
		if len(msgs) < 2:
			return None
		last_assistant = None
		last_user = None
		for i in range(len(msgs) - 1, -1, -1):
			msg = msgs[i]
			if msg.get('role') == 'assistant' and last_assistant is None:
				last_assistant = msg
			elif msg.get('role') == 'user' and last_assistant is not None:
				last_user = msg
				break
		if last_user is None or last_assistant is None:
			return None
		return [last_user, last_assistant]
	#
	def get_exchange_at(self, num):
		msgs = self.handle.hHM.msgs
		if num < 0 or num >= len(msgs):
			return None
		start = msgs[num]
		entries = [start]
		if start.get('role') == 'user':
			if num + 1 < len(msgs) and msgs[num + 1].get('role') == 'assistant':
				entries.append(msgs[num + 1])
		elif start.get('role') == 'assistant':
			if num > 0 and msgs[num - 1].get('role') == 'user':
				entries.insert(0, msgs[num - 1])
		return entries
	#
	def list(self, source=None):
		result = {}
		for s in (['user', 'model'] if source is None else [source]):
			for source_path, title in self._list_titles(s):
				entries = self._list_entries(source_path, title)
				if entries:
					result["{}/{}".format(source_path, title)] = {
						'source': source_path,
						'title': title,
						'count': len(entries),
					}
		return result
	#
	def get(self, title, source=None):
		"""Retrieve entries for a title. source may be a path like 'model/p_HASH'.
		When source is None, search recursively under both 'user' and 'model'."""
		if source:
			return self._list_entries(source, title)
		combined = []
		for s in ['user', 'model']:
			for source_path, t in self._list_titles(s):
				if t == title:
					combined.extend(self._list_entries(source_path, title))
		return combined
	#
	def reinsert(self, title, source=None):
		if title in self.handle._consumed_tips:
			return 0
		entries = self.get(title, source)
		if not entries:
			return 0
		self.handle._consumed_tips.add(title)
		# Mode-aware filtering for the instruct_* tip: it contains both plan
		# and build instruction entries. Only reinsert the entries for the
		# current mode so the model doesn't receive conflicting instructions.
		mode = self.handle.Options.get('MODE', 'build')
		is_instruct_tip = title.startswith('instruct_')
		if is_instruct_tip:
			other_mode = 'plan' if mode == 'build' else 'build'
			other_prefix = '[{} MODE INSTRUCTIONS]'.format(other_mode.upper())
			other_tool_prefix = '[{} MODE TOOL REFERENCE]'.format(other_mode.upper())
			other_workflow_prefix = '[{} MODE WORKFLOW EXAMPLE]'.format(other_mode.upper())
		count = 0
		for data in entries:
			for msg in data.get('entries', []):
				content = msg.get('content', '')
				if is_instruct_tip and (
						content.startswith(other_prefix)
						or content.startswith(other_tool_prefix)
						or content.startswith(other_workflow_prefix)):
					continue
				# Tips replay as system instructions — the training data and
				# LLM role validation only know system/user/assistant/tool.
				# Coerce legacy 'model' entries so old tips stay valid.
				role = msg.get('role', 'user')
				if role == 'model':
					role = 'system'
				self.handle.Response(role, {
					'content': content,
					'thinking': msg.get('thinking', None),
					'name': msg.get('name', None),
					'rowId': msg.get('rowId', self.handle.Options['AI_ROW_ID']),
				})
				self.handle.Options['AI_ROW_ID'] += 1
				count += 1
		# After reinserting an instruct tip, run a cleanup pass so any stale
		# mode instructions already in the context are removed.
		if is_instruct_tip and hasattr(self.handle, '_set_mode_instructions'):
			try:
				self.handle._set_mode_instructions(mode)
			except Exception:
				pass
		return count
	#
	def delete(self, title, source=None):
		removed = 0
		if source:
			path = self._path(source, title)
			if os.path.isdir(path):
				for f in os.listdir(path):
					os.remove(os.path.join(path, f))
				os.rmdir(path)
				removed += 1
		else:
			for s in ['user', 'model']:
				for source_path, t in self._list_titles(s):
					if t == title:
						path = self._path(source_path, title)
						if os.path.isdir(path):
							for f in os.listdir(path):
								os.remove(os.path.join(path, f))
							os.rmdir(path)
							removed += 1
		return removed
	#
	def delete_entry(self, title, entry_num, source=None):
		if source:
			paths = [self._path(source, title)]
		else:
			paths = []
		for s in ['user', 'model']:
			for source_path, t in self._list_titles(s):
				if t == title:
					paths.append(self._path(source_path, title))
		for path in paths:
			if not os.path.isdir(path):
				continue
			files = sorted([f for f in os.listdir(path) if f.endswith('.json')])
			if entry_num < 0 or entry_num >= len(files):
				continue
			fpath = os.path.join(path, files[entry_num])
			if os.path.exists(fpath):
				os.remove(fpath)
				return True
		return False
	#
	def delete_all(self, source=None):
		removed = 0
		for s in (['user', 'model'] if source is None else [source]):
			path = self._path(s)
			if not os.path.isdir(path):
				continue
			for title in os.listdir(path):
				tpath = os.path.join(path, title)
				if os.path.isdir(tpath):
					for f in os.listdir(tpath):
						os.remove(os.path.join(tpath, f))
					os.rmdir(tpath)
					removed += 1
		return removed
	#
	# === Tool result caching ===
	#
	def _cache_path(self, toolname, key_hash=None):
		p = os.path.join(self.base_path, '_cache', toolname)
		if key_hash:
			p = os.path.join(p, "{}.json".format(key_hash))
		return p
	#
	def set_cache(self, toolname, key_hash, result, ttl=None):
		if ttl is None:
			ttl = self.handle.Options.get('TOOL_CACHE_TTL', 86400)
		path = self._cache_path(toolname, key_hash)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		# Get tool file mtime for invalidation on tool update
		tool_file = os.path.join(self.handle.Options.get('tools_path', 'tools'), "tool_{}.py".format(toolname))
		tool_mtime = 0
		if os.path.exists(tool_file):
			tool_mtime = int(os.path.getmtime(tool_file))
		data = {
			'result': result,
			'saved_at': int(time.time()),
			'ttl': ttl,
			'toolname': toolname,
			'key_hash': key_hash,
			'tool_mtime': tool_mtime,
		}
		fwrite(path, json.dumps(data), True)
	#
	def get_cache(self, toolname, key_hash):
		path = self._cache_path(toolname, key_hash)
		if not os.path.exists(path):
			return None
		try:
			with open(path) as fp:
				data = json.load(fp)
		except Exception:
			return None
		now = int(time.time())
		saved_at = data.get('saved_at', 0)
		ttl = data.get('ttl', 0)
		# TTL expiry
		if ttl > 0 and now - saved_at > ttl:
			os.remove(path)
			return None
		# Tool file mtime change -> cache invalid
		tool_file = os.path.join(self.handle.Options.get('tools_path', 'tools'), "tool_{}.py".format(toolname))
		if os.path.exists(tool_file):
			current_mtime = int(os.path.getmtime(tool_file))
			if data.get('tool_mtime', 0) != current_mtime:
				os.remove(path)
				return None
		return data.get('result')
	#
	def clear_cache(self, toolname=None, key_hash=None):
		if toolname is None:
			return self.clear_all_caches()
		if key_hash:
			path = self._cache_path(toolname, key_hash)
			if os.path.exists(path):
				os.remove(path)
				return 1
			return 0
		path = self._cache_path(toolname)
		if not os.path.isdir(path):
			return 0
		count = 0
		for f in os.listdir(path):
			if f.endswith('.json'):
				os.remove(os.path.join(path, f))
				count += 1
		try:
			os.rmdir(path)
		except Exception:
			pass
		return count
	#
	def clear_all_caches(self):
		path = os.path.join(self.base_path, '_cache')
		if not os.path.isdir(path):
			return 0
		count = 0
		for toolname in os.listdir(path):
			tpath = os.path.join(path, toolname)
			if os.path.isdir(tpath):
				for f in os.listdir(tpath):
					if f.endswith('.json'):
						os.remove(os.path.join(tpath, f))
						count += 1
				try:
					os.rmdir(tpath)
				except Exception:
					pass
		return count
