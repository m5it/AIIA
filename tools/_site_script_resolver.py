"""
Site Script Resolver — discovers, loads, and resolves per-website JS support scripts.

Directory layout:
  wwwurljssupport/
    ├── google.com/
    │   ├── info.md             # Site metadata + per-script table
    │   ├── support_search.js   # Script with metadata header
    │   └── support_extract.js
    ├── github.com/
    │   └── ...

Script files have a metadata header:
  // ==SiteScript==
  // title: Google Search
  // name: support_search
  // site: google.com
  // description: Perform a search query and return structured results
  // usage: <SiteScript site="google.com" script="support_search" params='{"query":"text"}'/>
  // params: query (string) required — the search term
  // returns: JSON array of {title, url, snippet}
  // ==/SiteScript==

The resolver searches (priority order):
  1. Custom path (SITE_SCRIPTS_PATH option or --site-scripts-path CLI arg)
  2. Framework root: <framework>/wwwurljssupport/
  3. Global fallback: ~/.config/aiia/wwwurljssupport/
"""

import os, json, re
from urllib.parse import urlparse

# Metadata header markers
_HEADER_START = '// ==SiteScript=='
_HEADER_END = '// ==/SiteScript=='
_META_RE = re.compile(r'^//\s*(\w+)\s*:\s*(.+)$')

_DEFAULT_GLOBAL = os.path.expanduser('~/.config/aiia/wwwurljssupport')


def _framework_root():
	"""Return the framework root directory (where run.py and config.py live)."""
	return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_search_paths(opts=None):
	"""Return list of paths to search for site scripts, in priority order."""
	paths = []
	if opts:
		custom = opts.get('SITE_SCRIPTS_PATH')
		if custom:
			paths.append(custom)
	# Framework root: <framework>/wwwurljssupport
	fw_path = os.path.join(_framework_root(), 'wwwurljssupport')
	if fw_path not in paths:
		paths.append(fw_path)
	# Global fallback
	if _DEFAULT_GLOBAL not in paths:
		paths.append(_DEFAULT_GLOBAL)
	return paths


def _domain_from_url(url):
	"""Extract domain from a URL, stripping www. prefix."""
	parsed = urlparse(url)
	domain = parsed.netloc or parsed.path.split('/')[0]
	domain = domain.lower()
	if domain.startswith('www.'):
		domain = domain[4:]
	return domain


def _parse_script_metadata(content):
	"""Parse the metadata header from a script content string."""
	meta = {
		'name': None, 'title': None, 'site': None,
		'description': None, 'usage': None,
		'params': None, 'returns': None,
	}
	start = content.find(_HEADER_START)
	if start == -1:
		return meta
	end = content.find(_HEADER_END, start)
	if end == -1:
		return meta
	header = content[start + len(_HEADER_START):end]
	for line in header.strip().split('\n'):
		m = _META_RE.match(line.strip())
		if m:
			key = m.group(1).lower()
			val = m.group(2).strip()
			if key == 'name':
				meta['name'] = val
			elif key == 'title':
				meta['title'] = val
			elif key == 'site':
				meta['site'] = val
			elif key == 'description':
				meta['description'] = val
			elif key == 'usage':
				meta['usage'] = val
			elif key == 'params':
				meta['params'] = val
			elif key == 'returns':
				meta['returns'] = val
	return meta


def find_scripts(opts=None):
	"""Return a dict: {domain: {info: str, scripts: list, path: str}}"""
	results = {}
	searched_paths = set()
	for base in _get_search_paths(opts):
		if not os.path.isdir(base) or base in searched_paths:
			continue
		searched_paths.add(base)
		for domain_dir in sorted(os.listdir(base)):
			if domain_dir.startswith('_') or domain_dir.startswith('.'):
				continue
			domain_path = os.path.join(base, domain_dir)
			if not os.path.isdir(domain_path):
				continue
			domain = domain_dir.lower()
			if domain not in results:
				results[domain] = {'scripts': [], 'info': None, 'path': domain_path}
			info_path = os.path.join(domain_path, 'info.md')
			if os.path.isfile(info_path):
				try:
					with open(info_path, 'r') as f:
						results[domain]['info'] = f.read()
				except Exception:
					pass
			for fname in sorted(os.listdir(domain_path)):
				if fname.startswith('_') or fname.startswith('.'):
					continue
				if not fname.endswith('.js'):
					continue
				script_path = os.path.join(domain_path, fname)
				try:
					with open(script_path, 'r') as f:
						content = f.read()
					meta = _parse_script_metadata(content)
					results[domain]['scripts'].append({
						'name': fname,
						'path': script_path,
						'meta': meta,
						'content': content,
					})
				except Exception as e:
					results[domain]['scripts'].append({
						'name': fname,
						'path': script_path,
						'meta': {},
						'content': None,
						'error': str(e),
					})
	return results


def resolve_script(url_or_domain, script_name=None, opts=None):
	"""
	Resolve a specific script for a URL or domain.
	Returns: {domain, script_name, script_path, content, meta, info, available_scripts, path}
	"""
	if '://' in url_or_domain or '.' in url_or_domain.replace('/', ''):
		domain = _domain_from_url(url_or_domain)
	else:
		domain = url_or_domain.lower()
	all_scripts = find_scripts(opts)
	if domain not in all_scripts:
		return None
	info = all_scripts[domain]
	if not script_name:
		return {
			'domain': domain,
			'script_name': None,
			'script_path': None,
			'content': None,
			'meta': {},
			'info': info.get('info'),
			'available_scripts': [s['name'] for s in info['scripts']],
			'path': info.get('path'),
		}
	sname = script_name
	if not sname.endswith('.js'):
		sname = sname + '.js'
	for s in info['scripts']:
		if s['name'] == sname or s['name'] == script_name:
			return {
				'domain': domain,
				'script_name': s['name'],
				'script_path': s['path'],
				'content': s.get('content'),
				'meta': s.get('meta', {}),
				'info': info.get('info'),
				'available_scripts': [s['name'] for s in info['scripts']],
				'path': info.get('path'),
			}
	return None


def resolve_load_script(url_or_domain, opts=None):
	"""Resolve the 'support_load.js' script for a URL (auto-exec on page load)."""
	return resolve_script(url_or_domain, 'support_load', opts)


def list_sites(opts=None):
	"""Return sorted list of domain names with available scripts and metadata."""
	all_scripts = find_scripts(opts)
	sites = []
	for domain, info in sorted(all_scripts.items()):
		scripts_list = []
		for s in info['scripts']:
			meta = s.get('meta', {})
			scripts_list.append({
				'name': s['name'],
				'title': meta.get('title') or meta.get('name') or s['name'],
				'description': meta.get('description', ''),
				'usage': meta.get('usage', ''),
			})
		sites.append({
			'domain': domain,
			'scripts': scripts_list,
			'has_info': info['info'] is not None,
			'path': info['path'],
		})
	return sites


def get_site_info(domain, opts=None):
	"""Get the info.md content and enriched script list for a domain."""
	all_scripts = find_scripts(opts)
	domain = domain.lower()
	if domain in all_scripts:
		info = all_scripts[domain]
		scripts_list = []
		for s in info['scripts']:
			meta = s.get('meta', {})
			scripts_list.append({
				'name': s['name'],
				'title': meta.get('title') or meta.get('name') or s['name'],
				'site': meta.get('site', domain),
				'description': meta.get('description', ''),
				'usage': meta.get('usage', ''),
				'params': meta.get('params', ''),
				'returns': meta.get('returns', ''),
			})
		return {
			'domain': domain,
			'info': info.get('info'),
			'scripts': scripts_list,
			'path': info['path'],
		}
	return None


def find_write_path(domain, opts=None):
	"""Find where to write a new script for a domain. Returns the domain directory path (creates if needed)."""
	paths = _get_search_paths(opts)
	for base in paths:
		if os.access(base, os.W_OK) or not os.path.exists(base):
			domain_path = os.path.join(base, domain.lower())
			break
	else:
		domain_path = os.path.join(paths[0], domain.lower())
	os.makedirs(domain_path, exist_ok=True)
	return domain_path


def write_script(domain, script_name, content, opts=None):
	"""Write a script file for a domain. Returns the path written to."""
	domain_path = find_write_path(domain, opts)
	if not script_name.endswith('.js'):
		script_name = script_name + '.js'
	script_path = os.path.join(domain_path, script_name)
	with open(script_path, 'w') as f:
		f.write(content)
	return script_path


def ensure_default_structure(opts=None):
	"""Ensure the base wwwurljssupport directories exist."""
	for base in _get_search_paths(opts):
		if not os.path.exists(base):
			try:
				os.makedirs(base, exist_ok=True)
			except Exception:
				pass
