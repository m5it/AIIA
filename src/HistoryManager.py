import os,json,subprocess
from src.functions import *
#
class HistoryManager():
	#
	def __init__(self,opts):
		#print("HistoryManager.__init__() START, DEBUG, opts: ",opts)
		self.handle    = opts.get('handle')
		self.opt_quiet = opts['quiet'] if 'quiet' in opts else False
		self.opt_path  = opts['path'] if 'path' in opts else self.handle.Options['history_path']
		self.handle.hLG.echo("HistoryManager.__init__() STARTED!",{'color':True})
		
		self.history   = "" # name of choosed history file
		self.available = []
		self.msgs      = []
		# count tokens
		self.token_prompt   = 0
		self.token_response = 0
	
	@property
	def _history_dir(self):
		return "{}/history".format(self.handle.Options.get('path', '').rstrip('/'))

	@property
	def _names_path(self):
		return os.path.join(self._history_dir, 'names.json')

	def _load_names(self):
		p = self._names_path
		if not os.path.exists(p):
			return {}
		try:
			with open(p) as f:
				return json.load(f)
		except Exception:
			return {}

	def set_name(self, index, name):
		try:
			idx = int(index)
		except (ValueError, TypeError):
			return "Error: index must be a number."
		if not self.available:
			self.Update()
		self.available.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]), reverse=False)
		if idx < 0 or idx >= len(self.available):
			return "Error: index {} out of range (0-{}).".format(idx, len(self.available) - 1)
		fname = self.available[idx]
		key = fname[:-4] if fname.endswith('.dbk') else fname
		clean = name.strip().replace(' ', '_')
		if not clean:
			return "Error: name cannot be empty."
		names = self._load_names()
		names[key] = clean
		with open(self._names_path, 'w') as f:
			json.dump(names, f, indent=2)
		return "Named history '{}' as '{}'.".format(fname, clean)

	def get_name(self, key):
		return self._load_names().get(key, None)

	def set_current_name(self, name):
		fname = self.handle.Options.get('AI_FILE_HISTORY', '')
		if not fname:
			return "Error: no active history file."
		key = fname[:-4] if fname.endswith('.dbk') else fname
		clean = name.strip().replace(' ', '_')
		if not clean:
			return "Error: name cannot be empty."
		names = self._load_names()
		names[key] = clean
		with open(self._names_path, 'w') as f:
			json.dump(names, f, indent=2)
		return "Named current history '{}' as '{}'.".format(fname, clean)
	
	#
	def _get_date(self, file_path):
		"""Get date from first JSON line of a .dbk file (fast, one-line read)."""
		try:
			with open(file_path) as f:
				for line in f:
					line = line.strip()
					if not line or not line.startswith('{'):
						continue
					try:
						return json.loads(line).get('date', '?')
					except Exception:
						return '?'
		except Exception:
			return '?'
		return '?'

	def _get_preview(self, file_path, max_len=80):
		"""Get a preview string from a .dbk file: date + first user message snippet."""
		try:
			with open(file_path) as f:
				date_str = '?'
				for line in f:
					line = line.strip()
					if not line or not line.startswith('{'):
						continue
					try:
						msg = json.loads(line)
					except Exception:
						continue
					if date_str == '?':
						date_str = msg.get('date', '?')
					if msg.get('role') == 'user':
						content = msg.get('content', '')
						preview = content.replace('\n', ' ').replace('\r', '')[:max_len]
						if len(content) > max_len:
							preview += '...'
						return date_str, preview
			return date_str, '(system only)'
		except Exception:
			return '?', '(unreadable)'

	def _search(self, query):
		"""Search .dbk files for query. Returns list of dicts sorted by date desc."""
		results = []
		try:
			proc = subprocess.run(
				['grep', '-ril', '--include=*.dbk', query, self._history_dir],
				capture_output=True, text=True, timeout=30
			)
			if proc.returncode not in (0, 1):
				return []
			matches = [os.path.basename(f) for f in proc.stdout.strip().split('\n') if f]
		except Exception:
			return []
		for fname in matches:
			file_path = os.path.join(self._history_dir, fname)
			date_str, preview = self._get_preview(file_path)
			try:
				idx = self.available.index(fname)
			except ValueError:
				continue
			results.append({'filename': fname, 'index': idx, 'date': date_str, 'preview': preview})
		results.sort(key=lambda x: x['date'], reverse=True)
		return results

	# update self.available (list history files)
	def Update(self):
		#
		self.available = []
		#
		if not os.path.isdir(self._history_dir):
			return
		for tmp in os.listdir(self._history_dir):
			if rmatch(tmp,r"^[a-f0-9]+_\d+\..*") or rmatch(tmp,r"^\d+\..*"):
				self.available.append(tmp)
	
	# method get() - load chat history from a file (append to self.msgs)
	# If path is provided, loads from that exact file (e.g. HISTORY.md with embedded JSON comments).
	# Otherwise loads from the standard history/ file path.
	def Get(self, path=None):
		#
		self.msgs = []
		#
		if path:
			file_path = path
		else:
			file_path = "{}/{}".format(self._history_dir, self.history)
		#
		if not os.path.exists(file_path):
			return
		#
		with open(file_path) as tmp:
			for line in tmp:
				line = line.strip()
				if not line:
					continue
				# Parse JSON from HTML comment <!-- {...} -->
				if line.startswith('<!--') and line.endswith('-->'):
					json_str = line[4:-3].strip()
					try:
						self.msgs.append(json.loads(json_str))
					except Exception:
						continue
				# Also support plain JSON-lines (backward compat with .dbk files)
				elif line.startswith('{'):
					try:
						self.msgs.append(json.loads(line))
					except Exception:
						continue
	
	#
	def GetLast(self):
		self.history = self.available[ len(self.available)-1 ]
		self.Get()
		self.choosed = True
	
	#
	def CheckDraft(self):
		if self.handle.Options['DRAFT_CONTENT'] is not None:
			response = self.handle.Stream( self.handle.Options['DRAFT_CONTENT'] )
			self.handle.Options['DRAFT_CONTENT'] = None
	
	#
	def Available(self, compact=False):
		self.Update()
		self.available.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]), reverse=False)
		if self.opt_quiet == False:
			if not self.available:
				print("No history files found.")
				return
			if compact:
				dates = set()
				for h in self.available:
					d = self._get_date(os.path.join(self._history_dir, h))
					if d and d != '?':
						dates.add(d)
				date_range = ''
				if dates:
					date_range = ', {} to {}'.format(min(dates), max(dates))
				print("{} sessions{} — type 's <query>' to search, or a number to load.".format(
					len(self.available), date_range))
			else:
				names = self._load_names()
				for i, history in enumerate(self.available):
					display = history
					key = history[:-4] if history.endswith('.dbk') else history
					alias = names.get(key)
					if alias:
						display = "{} ({})".format(history, alias)
					file_path = os.path.join(self._history_dir, history)
					d = self._get_date(file_path)
					print("{:>3}.) {} [{}] {}".format(
						i, display, d, len(fread(file_path))))
	#
	def _show_list(self, items, names):
		for i, item in enumerate(items):
			display = item['filename']
			key = item['filename'][:-4] if item['filename'].endswith('.dbk') else item['filename']
			alias = names.get(key)
			if alias:
				display = "{} ({})".format(item['filename'], alias)
			print(" {:>3}.) {} [{}] {}".format(
				i, display, item['date'], item['preview']))
	#
	def Choose(self):
		self.handle.hLG.echo("Choose history START...: ",{'color':True,'colorValue':'orange','debugOnly':False})
		choosed = False
		self.available = []
		names = self._load_names()
		#
		self.Available(compact=True)
		#
		while choosed == False and len(self.available):
			self.handle.hLG.echo("Choose: ",{'color':True,'colorValue':'orange','debugOnly':False})
			tmp = user_input()
			if tmp == 'x' or not tmp:
				self.handle.hLG.echo("Canceling...",{'color':True,'colorValue':'red','debugOnly':False})
				choosed = True
				break
			# search
			elif tmp.startswith('s ') or tmp.startswith('/ '):
				if self._choose_search(tmp, names):
					choosed = True
					break
			# view from full list
			elif tmp.startswith('v '):
				self._view_file(tmp, None, names)
			# load from full list
			else:
				try:
					self.history = self.available[int(tmp)]
					self.Get()
					choosed = True
				except Exception as E:
					print("Invalid input. Try a number, 's <query>', or 'x'.")
	#
	def _choose_search(self, tmp, names):
		"""Handle the `s `/`/ ` search flow, including the search-results
		sub-loop. Returns True when a session was chosen (exit the outer
		loop), False to continue."""
		results = self._search_and_show(tmp[2:], names)
		if results is None:
			return False
		# enter sub-loop for search results
		while True:
			self.handle.hLG.echo("Result {}/{}. Choose (s new search, a all, x cancel): ".format(
				len(results), len(self.available)),
				{'color':True,'colorValue':'orange','debugOnly':False})
			sub = user_input()
			if sub == 'x' or not sub:
				return True
			elif sub.startswith('s ') or sub.startswith('/ '):
				results = self._search_and_show(sub[2:], names)
				if results is None:
					continue
				continue
			elif sub == 'a':
				break
			elif sub.startswith('v '):
				self._view_file(sub, results, names)
				continue
			elif self._pick_result(sub, results):
				return True
		return False

	def _search_and_show(self, arg, names):
		"""Run a search, print the results, and return the results list —
		or None when the query is empty or nothing matched."""
		query = arg.strip()
		if not query:
			print("Usage: s <search query>")
			return None
		print('Searching "{}"...'.format(query))
		results = self._search(query)
		if not results:
			print("No matches.")
			return None
		self._show_list(results, names)
		return results

	def _pick_result(self, sub, results):
		"""Select a session by number from the search results. Returns
		True when a session was chosen."""
		try:
			idx = int(sub)
		except ValueError:
			print("Invalid input. Try a number, 's', 'a', or 'x'.")
			return False
		if 0 <= idx < len(results):
			self.history = results[idx]['filename']
			self.Get()
			return True
		print("Number out of range (0-{}).".format(len(results) - 1))
		return False
	#
	def _view_file(self, cmd, items, names):
		a = cmd.split()
		if len(a) < 2:
			print("Usage: v <number>")
			return
		try:
			idx = int(a[1])
		except ValueError:
			print("Invalid number.")
			return
		if items is not None:
			if 0 <= idx < len(items):
				tmpname = items[idx]['filename']
			else:
				print("Number out of range (0-{}).".format(len(items) - 1))
				return
		else:
			if 0 <= idx < len(self.available):
				tmpname = self.available[idx]
			else:
				print("Number out of range (0-{}).".format(len(self.available) - 1))
				return
		file_path = os.path.join(self._history_dir, tmpname)
		key = tmpname[:-4] if tmpname.endswith('.dbk') else tmpname
		alias = names.get(key)
		if alias:
			print("--- {} ({}) ---".format(tmpname, alias))
		else:
			print("--- {} ---".format(tmpname))
		print(fread(file_path))
	
