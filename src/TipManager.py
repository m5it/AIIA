import os, json, time
from src.functions import fwrite

class TipManager():
	#
	def __init__(self, opts):
		self.handle = opts['handle'] if 'handle' in opts else False
		self.handle.hLG.echo("TipManager.__init__() STARTED!",{'color':True})
		self.base_path = self.handle.Options.get('TIPS_PATH', os.path.expanduser('~/.config/ourai/tips'))
	#
	def _path(self, source, title=None):
		p = os.path.join(self.base_path, source)
		if title:
			p = os.path.join(p, title)
		return p
	#
	def _list_titles(self, source):
		path = self._path(source)
		if not os.path.isdir(path):
			return []
		return sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
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
			titles = self._list_titles(s)
			for t in titles:
				entries = self._list_entries(s, t)
				if entries:
					result["{}/{}".format(s, t)] = {
						'source': s,
						'title': t,
						'count': len(entries),
					}
		return result
	#
	def get(self, title, source=None):
		if source:
			return self._list_entries(source, title)
		combined = []
		for s in ['user', 'model']:
			combined.extend(self._list_entries(s, title))
		return combined
	#
	def reinsert(self, title, source=None):
		entries = self.get(title, source)
		if not entries:
			return 0
		count = 0
		for data in entries:
			for msg in data.get('entries', []):
				self.handle.Response(msg.get('role', 'user'), {
					'content': msg.get('content', ''),
					'thinking': msg.get('thinking', None),
					'name': msg.get('name', None),
					'rowId': msg.get('rowId', self.handle.Options['AI_ROW_ID']),
				})
				self.handle.Options['AI_ROW_ID'] += 1
				count += 1
		return count
	#
	def delete(self, title, source=None):
		removed = 0
		for s in (['user', 'model'] if source is None else [source]):
			path = self._path(s, title)
			if os.path.isdir(path):
				for f in os.listdir(path):
					os.remove(os.path.join(path, f))
				os.rmdir(path)
				removed += 1
		return removed
	#
	def delete_entry(self, title, entry_num, source=None):
		for s in (['user', 'model'] if source is None else [source]):
			path = self._path(s, title)
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
