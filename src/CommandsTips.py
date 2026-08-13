#--
import os
# class CommandsTips — tip-management commands
class CommandsTips():
	#
	def CMD_TIP_LIST(self, inp=""):
		a = inp.split()
		source = a[1].strip().lower() if len(a) > 1 and a[1].strip().lower() in ('user','model') else None
		tips = self.handle.hTM.list(source)
		if not tips:
			print("No tips saved.")
			return 2
		print("Tips:")
		for key, info in sorted(tips.items()):
			print("  {}/{} -> {} entries".format(info['source'], info['title'], info['count']))
		return 2
	#
	def CMD_TIP_SAVE(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TS [history_num] <title>")
			return 2
		title = a[-1]
		if len(a) == 2:
			entries = self.handle.hTM.get_last_exchange()
			if entries is None:
				print("No exchange found to save.")
				return 2
		else:
			try:
				num = int(a[1])
			except ValueError:
				print("Usage: !TS [history_num] <title>")
				return 2
			entries = self.handle.hTM.get_exchange_at(num)
			if entries is None:
				print("Invalid history row number.")
				return 2
		self.handle.hTM.save(title, 'user', entries)
		self.handle.hLG.echo("Saved {} message(s) as tip '{}'".format(len(entries), title),{'color':True,'colorValue':'green'})
		return 2
	#
	def _parse_tip_ref(self, s):
		if '/' in s:
			parts = s.split('/', 1)
			if parts[0] in ('user', 'model'):
				return parts[0], parts[1]
		return None, s
	#
	def CMD_TIP_VIEW(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TV <title|source/title>")
			return 2
		source, title = self._parse_tip_ref(a[1])
		entries = self.handle.hTM.get(title, source)
		if not entries:
			print("No tips found for title '{}'".format(a[1]))
			return 2
		print("Tips for '{}':".format(a[1]))
		for i, data in enumerate(entries):
			print("\n--- Entry {} ({} source, session {}) ---".format(i, data.get('source','?'), data.get('sessionId','?')))
			for msg in data.get('entries', []):
				role = msg.get('role','?')
				content = msg.get('content','')
				trunc = content[:200].replace('\n',' ') + ('...' if len(content)>200 else '')
				print("  [{}] {}".format(role, trunc))
		return 2
	#
	def CMD_TIP_REINSERT(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TR <title|source/title>")
			return 2
		source, title = self._parse_tip_ref(a[1])
		if a[1] in self.handle._consumed_tips:
			print("Tip '{}' was already reinserted this session.".format(a[1]))
			return 2
		count = self.handle.hTM.reinsert(title, source)
		if count > 0:
			self.handle.hLG.echo("Reinserted {} message(s) from tip '{}'".format(count, a[1]),{'color':True,'colorValue':'green'})
		else:
			print("No entries found for tip '{}'.".format(a[1]))
		return 2
	#
	def CMD_TIP_DELETE(self, inp):
		a = inp.split()
		if len(a) < 2:
			print("Usage: !TD <title|source/title>")
			return 2
		source, title = self._parse_tip_ref(a[1])
		removed = self.handle.hTM.delete(title, source)
		if removed:
			self.handle.hLG.echo("Deleted tip '{}'".format(a[1]),{'color':True,'colorValue':'orange'})
		else:
			print("No tip titled '{}' found.".format(a[1]))
		return 2
	#
	def CMD_TIP_DELETE_ENTRY(self, inp):
		a = inp.split()
		if len(a) < 3:
			print("Usage: !TDR <title|source/title> <entry_num>")
			return 2
		source, title = self._parse_tip_ref(a[1])
		try:
			num = int(a[2])
		except ValueError:
			print("Entry number must be an integer.")
			return 2
		if self.handle.hTM.delete_entry(title, num, source):
			self.handle.hLG.echo("Deleted entry {} from tip '{}'".format(num, a[1]),{'color':True,'colorValue':'orange'})
		else:
			print("Entry not found.")
		return 2
	#
	def CMD_TIP_DELETE_ALL(self, inp=""):
		a = inp.split()
		source = a[1].strip().lower() if len(a) > 1 and a[1].strip().lower() in ('user','model') else None
		removed = self.handle.hTM.delete_all(source)
		self.handle.hLG.echo("Deleted {} tip title(s)".format(removed),{'color':True,'colorValue':'orange'})
		return 2
	#
	def CMD_TIP_CLEAN(self, inp=""):
		"""!TIP_CLEAN [pattern] — delete tip titles matching a glob pattern.
		Default pattern is 'session_*_cleared', which removes stale top-level
		session-cleared tips that predate project-scoped session storage."""
		import fnmatch
		a = inp.split()
		pattern = a[1] if len(a) > 1 else 'session_*_cleared'
		removed = 0
		for s in ['user', 'model']:
			path = self.handle.hTM._path(s)
			if not os.path.isdir(path):
				continue
			for title in os.listdir(path):
				if not os.path.isdir(os.path.join(path, title)):
					continue
				if fnmatch.fnmatch(title, pattern):
					removed += self.handle.hTM.delete(title, s)
		self.handle.hLG.echo("Deleted {} tip title(s) matching '{}'".format(removed, pattern),
			{'color': True, 'colorValue': 'orange'})
		return 2
	#
	def CMD_CACHE_CLEAR(self, inp=""):
		count = self.handle.hTM.clear_all_caches()
		self.handle._consumed_tips = set()
		self.handle.hLG.echo("Cleared {} cached tool result(s) and reset consumed tips.".format(count),{'color':True,'colorValue':'orange'})
		return 2
	#
