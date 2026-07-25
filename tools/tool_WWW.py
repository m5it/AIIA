import subprocess, os, glob, sys, json, time, hashlib
from config import Options
from tools._koslenium_server import ensure_server, send, exec_script

_DEBUG = Options.get("DEBUG", False)
def _dbg(*a, **kw):
	if _DEBUG:
		print("WWW:", *a, **kw)

def _url_hash(url):
	return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

def _get_cache_dir():
	"""Resolve cache directory path."""
	cache_dir = Options.get('WWW_CACHE_DIR', 'workout/www_cache')
	if not os.path.isabs(cache_dir):
		cache_dir = os.path.join(os.getcwd(), cache_dir)
	return cache_dir

def _find_cached(url, ttl_hours):
	"""Check if a cached version of this URL exists within TTL."""
	cache_dir = _get_cache_dir()
	if not os.path.isdir(cache_dir):
		return None
	prefix = _url_hash(url) + '_'
	for f in sorted(os.listdir(cache_dir), reverse=True):
		if f.startswith(prefix) and f.endswith('.html'):
			fp = os.path.join(cache_dir, f)
			if ttl_hours > 0:
				age_h = (time.time() - os.path.getmtime(fp)) / 3600
				if age_h > ttl_hours:
					continue
			meta_path = fp.rsplit('.', 1)[0] + '.meta.json'
			meta = {}
			if os.path.isfile(meta_path):
				try:
					with open(meta_path) as mf:
						meta = json.load(mf)
				except Exception:
					pass
			return {"file": fp, "meta": meta}
	return None

def _save_to_cache(url, html, selector=None):
	"""Save HTML to cache with metadata. Returns the file path."""
	cache_dir = _get_cache_dir()
	os.makedirs(cache_dir, exist_ok=True)
	ts = time.strftime('%Y%m%d_%H%M%S')
	fname = '{}_{}.html'.format(_url_hash(url), ts)
	fp = os.path.join(cache_dir, fname)
	with open(fp, 'w', encoding='utf-8') as f:
		f.write(html)
	meta = {
		"url": url,
		"cached_at": time.strftime('%Y-%m-%dT%H:%M:%S'),
		"timestamp": time.time(),
		"char_count": len(html),
		"line_count": html.count('\n') + 1,
		"file": fname,
	}
	if selector:
		meta["selector"] = selector
	# Extract title if possible
	try:
		idx = html.lower().find('<title>')
		if idx >= 0:
			end = html.lower().find('</title>', idx + 7)
			if end > idx:
				meta["title"] = html[idx+7:end].strip()[:200]
	except Exception:
		pass
	meta_path = fp.rsplit('.', 1)[0] + '.meta.json'
	with open(meta_path, 'w', encoding='utf-8') as f:
		json.dump(meta, f, indent=2, ensure_ascii=False)
	return fp, meta

class WWW():
	def __init__(self):
		self.info = {
			"name":"WWW",
			"description":"Fetch a web page. Uses a persistent JS-capable browser engine when available; falls back to a lightweight HTTP client for simple requests.",
			"parameters":{
				"returnType":"string",
				"required":["url"],
				"properties":{
					"url":{
						"type":"string",
						"description":"URL to fetch (e.g., https://www.google.com)"
					},
					"js":{
						"type":"string",
						"description":"Set to 'true' to enable JavaScript rendering (default: false for speed, auto-enables when browser/screenshot needed)"
					},
					"browser":{
						"type":"string",
						"description":"Set to 'true' to open a visible browser window for manual interaction (captcha solving)"
					},
					"text":{
						"type":"string",
						"description":"Set to 'true' to strip HTML and return readable text"
					},
					"links":{
						"type":"string",
						"description":"Set to 'true' to extract anchor links from the page"
					},
					"source":{
						"type":"string",
						"description":"Set to 'true' to show raw HTML (bypasses captcha detection)"
					},
					"screenshot":{
						"type":"string",
						"description":"File path to save a PNG screenshot (e.g., /tmp/page.png)"
					},
					"wait":{
						"type":"string",
						"description":"Extra wait time in milliseconds for JS rendering (default: 3000)"
					},
					"selector":{
						"type":"string",
						"description":"CSS selector to wait for before extracting content"
					},
					"jsExecute":{
						"type":"string",
						"description":"JavaScript expression to execute on the loaded page. Returns ONLY the JS result, not the full HTML. Example: Array.from(document.querySelectorAll('a')).map(a=>a.href). Useful for extracting specific data. Save successful scripts with <UpdateSiteScript> for reuse."
					},
					"siteScript":{
						"type":"string",
						"description":"Set to 'true' to auto-execute the site's support_load.js script after page load, or specify a script name like 'support_extract'. See also: <SiteScript> tool."
					},
					"cacheSource":{
						"type":"string",
						"description":"Set to 'true' to save the full HTML to disk (workout/www_cache/) with dedup. Returns file path + metadata. Use with <ParsePage> to analyze cached pages locally."
					},
				},
			},
		}

	def run(self, url, opts={}, js=None, browser=None, text=None, links=None,
			source=None, screenshot=None, wait=None, selector=None, siteScript=None,
			jsExecute=None, cacheSource=None):
		needs_js = (
			browser and str(browser).lower() == 'true'
			or screenshot
			or (js and str(js).lower() == 'true')
			or jsExecute
		)

		want_cache = cacheSource and str(cacheSource).lower() == 'true'
		ttl_hours = Options.get('WWW_CACHE_TTL_H', 24)

		# If cacheSource requested, check for existing cached version first
		if want_cache:
			cached = _find_cached(url, ttl_hours)
			if cached:
				_dbg("found cached version: {}".format(cached['file']))
				meta = cached['meta']
				abs_path = os.path.abspath(cached['file'])
				return (
					"Page already cached (use <ParsePage> to analyze it):\n"
					"  Path: {}\n"
					"  URL: {}\n"
					"  Cached at: {}\n"
					"  Size: {} chars ({} lines)\n"
					"  Title: {}\n\n"
					"Use <ParsePage> to extract data:\n"
					"<ParsePage><fileName>{}</fileName><action>meta</action></ParsePage>\n"
					"<ParsePage><fileName>{}</fileName><action>scripts</action></ParsePage>\n"
					"<ParsePage><fileName>{}</fileName><action>query</action><selector>CSS_SELECTOR</selector></ParsePage>"
				).format(
					abs_path,
					meta.get('url', url),
					meta.get('cached_at', 'unknown'),
					meta.get('char_count', 0),
					meta.get('line_count', 0),
					meta.get('title', '(no title)'),
					os.path.basename(cached['file']),
					os.path.basename(cached['file']),
					os.path.basename(cached['file']),
				)

		# Auto-enable cookies for JS/browser requests
		if needs_js and not Options.get("COOKIE_FILE"):
			default_cookie = os.path.expanduser("~/.config/aiia/cookies.json")
			Options["COOKIE_FILE"] = default_cookie
			os.makedirs(os.path.dirname(default_cookie), exist_ok=True)

		# Build command dict for server mode
		cmd = {'url': url}
		if browser and str(browser).lower() == 'true':
			cmd['browser'] = True
		if text and str(text).lower() == 'true':
			cmd['text'] = True
		if links and str(links).lower() == 'true':
			cmd['links'] = True
		if source and str(source).lower() == 'true':
			cmd['source'] = True
		if screenshot:
			cmd['screenshot'] = screenshot
		if wait:
			cmd['wait'] = int(wait)
		if selector:
			cmd['selector'] = selector
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			if not os.path.isabs(cookie_path):
				abs_cookie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cookie_path)
			else:
				abs_cookie = cookie_path
			cmd['cookie_file'] = abs_cookie

		# Try server if JS needed or if server already running
		if needs_js:
			port = ensure_server(browser=bool(cmd.get('browser')))
			if port:
				_dbg("using server path (port {})".format(port))
				result = send(port, cmd)
				if result is not None:
					if jsExecute:
						return self._run_js_execute(jsExecute, port, url)
					if want_cache:
						return self._cache_and_return(result, url, selector)
					result = self._check_source_size(result, source)
					return self._maybe_run_site_script(result, url, port, siteScript)
				_dbg("server returned None, falling back to one-shot")
			else:
				_dbg("no server port, falling back to one-shot")
			# Fall back to one-shot wwwjs
			return self._run_wwwjs(cmd)
		else:
			_dbg("no JS needed, using simple path")

		# Try server if already running (fast path even without JS)
		port = ensure_server()
		if port:
			result = send(port, cmd)
			if result is not None:
				if jsExecute:
					return self._run_js_execute(jsExecute, port, url)
				if want_cache:
					return self._cache_and_return(result, url, selector)
				result = self._check_source_size(result, source)
				return self._maybe_run_site_script(result, url, port, siteScript)

		# Fall back to lightweight www.jar
		result = self._run_www_jar(url, text, links)
		if want_cache and result and not result.startswith("Error"):
			return self._cache_and_return(result, url, selector)
		return result

	def _cache_and_return(self, html, url, selector=None):
		"""Save HTML to cache and return summary with ParsePage instructions."""
		try:
			fp, meta = _save_to_cache(url, html, selector)
			fname = os.path.basename(fp)
			abs_path = os.path.abspath(fp)
			return (
				"Page cached successfully:\n"
				"  Path: {}\n"
				"  URL: {}\n"
				"  Size: {} chars ({} lines)\n"
				"  Title: {}\n\n"
				"Use <ParsePage> to analyze the cached page:\n"
				"<ParsePage><fileName>{}</fileName><action>meta</action></ParsePage>\n"
				"<ParsePage><fileName>{}</fileName><action>scripts</action></ParsePage>\n"
				"<ParsePage><fileName>{}</fileName><action>links</action></ParsePage>\n"
				"<ParsePage><fileName>{}</fileName><action>text</action></ParsePage>\n"
				"<ParsePage><fileName>{}</fileName><action>query</action><selector>CSS_SELECTOR</selector></ParsePage>\n"
				"<ParsePage><fileName>{}</fileName><action>tree</action></ParsePage>"
			).format(
				abs_path,
				meta.get('url', url),
				meta.get('char_count', 0),
				meta.get('line_count', 0),
				meta.get('title', '(no title)'),
				fname, fname, fname, fname, fname, fname,
			)
		except Exception as e:
			_dbg("cache error: {}".format(e))
			return html

	def _maybe_run_site_script(self, page_content, url, port, siteScript):
		"""After page load, optionally execute a site script and append its output."""
		if not siteScript:
			return page_content
		try:
			from tools._site_script_resolver import resolve_load_script, resolve_script
			from tools._koslenium_server import exec_script as es
			script_name = str(siteScript).lower()
			if script_name == 'true':
				# Auto-resolve support_load.js
				resolved = resolve_load_script(url, Options)
			else:
				resolved = resolve_script(url, script_name, Options)
			if not resolved or not resolved.get('content'):
				_dbg("no site script found for {}".format(url))
				return page_content
			content = resolved['content']
			full_script = "var PARAMS = {};\n%s" % content
			result_data = es(port, full_script, wait=2000)
			if result_data:
				try:
					parsed = json.loads(result_data)
					formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
				except (json.JSONDecodeError, TypeError):
					formatted = str(result_data)
				return page_content + "\n\n=== Site Script Output (%s) ===\n%s" % (resolved.get('script_name', 'unknown'), formatted)
			return page_content
		except Exception as e:
			_dbg("site script error: {}".format(e))
			return page_content

	def _run_js_execute(self, js_code, port, url):
		"""Execute JS on the loaded page and return only the result."""
		_dbg("executing jsExecute on {}".format(url))
		result = exec_script(port, js_code, wait=2000)
		if result is None:
			return "Error: JS execution failed or returned no result"
		# Try to pretty-print JSON
		output = result
		try:
			parsed = json.loads(result)
			output = json.dumps(parsed, indent=2, ensure_ascii=False)
		except (json.JSONDecodeError, TypeError):
			pass
		domain = url.split('/')[2] if '//' in url else url
		suggestion = (
			"\n\n=== jsExecute Result ===\n%s"
			"\n\n=== Tip: Save this JS for reuse ==="
			"\nTo save for future visits, use:"
			"\n<UpdateSiteScript>"
			"\n<site>%s</site>"
			"\n<script>my_script_name</script>"
			"\n<content>// ==SiteScript==</content>"
			"\n</UpdateSiteScript>"
		) % (output, domain)
		return suggestion

	def _check_source_size(self, content, source_flag):
		"""If source is large, save to workout/ and return warning instead."""
		if not source_flag or str(source_flag).lower() != 'true':
			return content
		max_size = Options.get('WWW_SOURCE_MAX_SIZE', 80000)
		if not content or len(content) <= max_size:
			return content
		# Source too large — save to disk
		try:
			workout = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'workout')
			os.makedirs(workout, exist_ok=True)
			ts = time.strftime('%Y%m%d_%H%M%S')
			file_name = 'www_source_{}.html'.format(ts)
			file_path = os.path.join(workout, file_name)
			with open(file_path, 'w', encoding='utf-8') as f:
				f.write(content)
			line_count = content.count('\n') + 1
			char_count = len(content)
			approx_tokens = char_count // 4
			context_pct = int((approx_tokens / Options.get('AI_CONTEXT_LIMIT', 262144)) * 100)
			warning = (
				"Source too large: {:,} chars (~{:,} tokens, {}% of context).\n"
				"Saved to: {} ({:,} lines)\n\n"
				"Use <ReadFile> to read specific lines:\n"
				"<ReadFile><fileName>{}</fileName><fromLine>1</fromLine><toLine>100</toReadFile>\n\n"
				"Or use <Grep> to search within the file:\n"
				"<Grep><pattern>search term</pattern><fileName>{}</fileName></Grep>"
			).format(char_count, approx_tokens, context_pct, file_name, line_count, file_name, file_name)
			_dbg("source cached to {} ({:,} chars)".format(file_path, char_count))
			return warning
		except Exception as e:
			_dbg("source cache error: {}".format(e))
			return content

	def _run_www_jar(self, url, text, links):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		jars = glob.glob(os.path.join(tool_dir, "koslenium_driver", "www", "target", "www-*.jar"))
		if not jars:
			return "Error: www jar not found"
		jar = jars[0]
		cmd = ["java", "-jar", jar]
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
			if os.path.exists(abs_path):
				cmd.extend(["--cookie-file", abs_path])
		if links and str(links).lower() == "true":
			cmd.append("--links")
		if text and str(text).lower() == "true":
			cmd.append("--text")
		cmd.append(url)
		try:
			result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=".")
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				if output:
					output += "\n"
				output += "STDERR:\n{}".format(result.stderr)
			return output if output else "(no output)"
		except subprocess.TimeoutExpired:
			return "Error: www timed out (30s limit)"
		except FileNotFoundError:
			return "Error: java not found in PATH"
		except Exception as E:
			return "Error: {}".format(E)

	def _run_wwwjs(self, cmd_dict):
		tool_dir = os.path.dirname(os.path.abspath(__file__))
		run_script = os.path.join(tool_dir, "koslenium_driver", "run.sh")
		if not os.path.exists(run_script):
			return "Error: koslenium_driver/run.sh not found"

		cli = [run_script]
		cookie_path = Options.get("COOKIE_FILE")
		if cookie_path:
			abs_path = os.path.join(tool_dir, "..", cookie_path) if not os.path.isabs(cookie_path) else cookie_path
			cli.extend(["--cookie-file", abs_path])

		if cmd_dict.get('browser'):
			cli.append("--browser")
		if cmd_dict.get('text'):
			cli.append("--text")
		if cmd_dict.get('links'):
			cli.append("--links")
		if cmd_dict.get('source'):
			cli.append("--source")
		if cmd_dict.get('screenshot'):
			cli.extend(["--screenshot", cmd_dict['screenshot']])
		if cmd_dict.get('wait'):
			cli.extend(["--wait", str(cmd_dict['wait'])])
		if cmd_dict.get('selector'):
			cli.extend(["--selector", cmd_dict['selector']])
		cli.append(cmd_dict['url'])

		# Ensure display for headless JavaFX
		proc_env = os.environ.copy()
		from tools._koslenium_server import _ensure_display
		disp = _ensure_display()
		if disp:
			proc_env['DISPLAY'] = disp

		try:
			result = subprocess.run(cli, capture_output=True, text=True, timeout=300, cwd=".", env=proc_env)
			output = ""
			if result.stdout:
				output += result.stdout
			if result.stderr:
				if output:
					output += "\n"
				output += "STDERR:\n{}".format(result.stderr)
			return output if output else "(no output)"
		except subprocess.TimeoutExpired:
			return "Error: wwwjs timed out (300s limit)"
		except Exception as E:
			return "Error: {}".format(E)

class www(WWW):
	pass
