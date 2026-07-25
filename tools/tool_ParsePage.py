import os, json, sys
from config import Options

try:
	from bs4 import BeautifulSoup
except ImportError:
	BeautifulSoup = None

_DEBUG = Options.get("DEBUG", False)
def _dbg(*a, **kw):
	if _DEBUG:
		print("ParsePage:", *a, file=sys.stderr, **kw)

def _resolve_file(file_name):
	"""Resolve file path — try workout/ then workout/www_cache/ then raw path."""
	tool_dir = os.path.dirname(os.path.abspath(__file__))
	project_root = os.path.join(tool_dir, '..')
	candidates = [
		os.path.join(project_root, file_name),
		os.path.join(project_root, 'workout', file_name),
		file_name,
	]
	for p in candidates:
		if os.path.isfile(p):
			return p
	return file_name

class ParsePage():
	def __init__(self):
		self.info = {
			"name": "ParsePage",
			"description": "Parse a cached HTML page locally using BeautifulSoup. Extract scripts, links, metadata, text, or run CSS selector queries without re-fetching.",
			"parameters": {
				"returnType": "string",
				"required": ["fileName"],
				"properties": {
					"fileName": {
						"type": "string",
						"description": "Path to HTML file (e.g., workout/www_cache/a1b2c3_20260725_143022.html)"
					},
					"action": {
						"type": "string",
						"description": "What to extract: scripts, links, meta, text, tree, query (default: meta)"
					},
					"selector": {
						"type": "string",
						"description": "CSS selector for query action (e.g., div.article p, #main a)"
					},
					"limit": {
						"type": "string",
						"description": "Max results to return (default: 50)"
					},
					"full": {
						"type": "string",
						"description": "If 'true', return full content (inline scripts, full text). Default: truncated."
					},
				},
			},
		}

	def run(self, fileName, opts={}, action=None, selector=None, limit=None, full=None):
		if BeautifulSoup is None:
			return "Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4"

		file_path = _resolve_file(fileName)
		if not os.path.isfile(file_path):
			return "Error: file not found: {}".format(file_path)

		try:
			with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
				html = f.read()
		except Exception as e:
			return "Error reading file: {}".format(e)

		if not html.strip():
			return "Error: file is empty"

		soup = BeautifulSoup(html, 'html.parser')
		act = (action or 'meta').lower().strip()
		lim = int(limit) if limit else 50
		want_full = full and str(full).lower() == 'true'

		if act == 'scripts':
			return self._extract_scripts(soup, lim, want_full)
		elif act == 'links':
			return self._extract_links(soup, lim)
		elif act == 'meta':
			return self._extract_meta(soup)
		elif act == 'text':
			return self._extract_text(soup, lim, want_full)
		elif act == 'tree':
			return self._extract_tree(soup, lim)
		elif act == 'query':
			return self._query(soup, selector, lim, want_full)
		else:
			return "Error: unknown action '{}'. Use: scripts, links, meta, text, tree, query".format(act)

	def _extract_scripts(self, soup, lim, full):
		scripts = soup.find_all('script')
		if not scripts:
			return json.dumps({"count": 0, "scripts": []}, indent=2)

		result = []
		for i, s in enumerate(scripts[:lim]):
			entry = {"index": i}
			src = s.get('src')
			if src:
				entry["src"] = src
				entry["type"] = "external"
			else:
				entry["type"] = "inline"
				text = s.get_text(strip=True)
				if full:
					entry["content"] = text
				else:
					entry["content"] = text[:500] + ("..." if len(text) > 500 else "")
					entry["char_count"] = len(text)
			type_attr = s.get('type')
			if type_attr:
				entry["html_type"] = type_attr
			async_attr = s.get('async')
			if async_attr is not None:
				entry["async"] = True
			defer_attr = s.get('defer')
			if defer_attr is not None:
				entry["defer"] = True
			result.append(entry)

		return json.dumps({"count": len(scripts), "showing": len(result), "scripts": result}, indent=2, ensure_ascii=False)

	def _extract_links(self, soup, lim):
		links = []
		# <a> tags
		for a in soup.find_all('a', href=True)[:lim]:
			entry = {
				"tag": "a",
				"href": a['href'],
				"text": a.get_text(strip=True)[:200],
			}
			if a.get('rel'):
				entry["rel"] = a['rel']
			links.append(entry)
		# <link> tags
		for link in soup.find_all('link', href=True)[:lim - len(links)]:
			entry = {
				"tag": "link",
				"href": link['href'],
				"rel": link.get('rel', []),
				"type": link.get('type', ''),
				"media": link.get('media', ''),
			}
			links.append(entry)
		return json.dumps({"count": len(links), "links": links}, indent=2, ensure_ascii=False)

	def _extract_meta(self, soup):
		result = {}

		title = soup.find('title')
		if title:
			result["title"] = title.get_text(strip=True)

		canonical = soup.find('link', rel='canonical')
		if canonical:
			result["canonical"] = canonical.get('href', '')

		metas = {}
		for m in soup.find_all('meta'):
			name = m.get('name') or m.get('property') or m.get('http-equiv')
			if name:
				metas[name] = m.get('content', '')
		if metas:
			result["meta"] = metas

		# Count elements
		result["element_counts"] = {
			"scripts": len(soup.find_all('script')),
			"links": len(soup.find_all('a', href=True)),
			"images": len(soup.find_all('img')),
			"stylesheets": len(soup.find_all('link', rel='stylesheet')),
			"forms": len(soup.find_all('form')),
			"iframes": len(soup.find_all('iframe')),
		}

		return json.dumps(result, indent=2, ensure_ascii=False)

	def _extract_text(self, soup, lim, full):
		# Remove script and style tags
		for tag in soup.find_all(['script', 'style', 'noscript']):
			tag.decompose()

		text = soup.get_text(separator=' ', strip=True)
		if not full:
			text = text[:3000] + ("..." if len(text) > 3000 else "")

		# Count
		total_chars = len(soup.get_text(separator=' ', strip=True))

		return json.dumps({
			"total_chars": total_chars,
			"showing_chars": len(text),
			"text": text,
		}, indent=2, ensure_ascii=False)

	def _extract_tree(self, soup, lim):
		"""ASCII tree view of the DOM structure."""
		lines = []
		def _walk(tag, depth, max_depth):
			if depth > max_depth:
				return
			if not hasattr(tag, 'name') or tag.name is None:
				return
			indent = "  " * depth
			name = tag.name
			classes = '.' + '.'.join(tag.get('class', [])) if tag.get('class') else ''
			tag_id = '#' + tag['id'] if tag.get('id') else ''
			text_preview = ''
			if tag.string and tag.string.strip():
				text_preview = ' "' + tag.string.strip()[:40] + '"'
			lines.append("{}<{}{}{}>{}".format(indent, name, tag_id, classes, text_preview))
			count = 0
			for child in tag.children:
				if hasattr(child, 'name') and child.name:
					_walk(child, depth + 1, max_depth)
					count += 1
					if count >= 30:
						lines.append("{}  ... ({} more children)".format(indent, len(list(tag.children)) - count))
						break

		for child in soup.children:
			if hasattr(child, 'name') and child.name:
				_walk(child, 0, lim)

		return "\n".join(lines) if lines else "(empty document)"

	def _query(self, soup, selector, lim, full):
		if not selector:
			return "Error: selector is required for query action. Example: div.article p"
		try:
			elements = soup.select(selector)
		except Exception as e:
			return "Error: invalid CSS selector: {}".format(e)

		results = []
		for el in elements[:lim]:
			entry = {
				"tag": el.name,
				"text": el.get_text(strip=True)[:300],
				"html": str(el) if full else str(el)[:500],
			}
			attrs = dict(el.attrs)
			if attrs:
				entry["attributes"] = attrs
			results.append(entry)

		return json.dumps({
			"selector": selector,
			"count": len(elements),
			"showing": len(results),
			"results": results,
		}, indent=2, ensure_ascii=False)

class parsepage(ParsePage):
	pass
