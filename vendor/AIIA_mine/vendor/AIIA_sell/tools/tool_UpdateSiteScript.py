"""
UpdateSiteScript tool — create or update per-website JS support scripts.

The model discovers site-specific DOM patterns and saves them as reusable scripts.

Usage:
  <UpdateSiteScript>
    <site>google.com</site>
    <script>support_search</script>
    <content>
    // ==SiteScript==
    // name: support_search.js
    // site: google.com
    // params: query (string)
    // returns: JSON array of search results
    // ==/SiteScript==
    var query = PARAMS.query || "";
    var results = [];
    // ... DOM interaction logic ...
    return JSON.stringify(results);
    </content>
  </UpdateSiteScript>

  <UpdateSiteScript>
    <site>google.com</site>
    <action>delete</action>
    <script>support_old_thing</script>
  </UpdateSiteScript>
"""

import os, json, re, shutil
from config import Options
from tools._site_script_resolver import write_script, find_write_path, get_site_info, resolve_script

_MAX_HISTORY = 10


def _backup_existing(filepath):
	"""Backup an existing script to _history/name.v{N}.js. Keeps last 10 versions."""
	dirpath = os.path.dirname(filepath)
	basename = os.path.basename(filepath)
	name_no_ext = basename[:-3] if basename.endswith('.js') else basename
	hist_dir = os.path.join(dirpath, '_history')
	os.makedirs(hist_dir, exist_ok=True)
	# Find current max version
	max_v = 0
	pattern = re.compile(r'^%s\.v(\d+)\.js$' % re.escape(name_no_ext))
	for f in os.listdir(hist_dir):
		m = pattern.match(f)
		if m:
			v = int(m.group(1))
			if v > max_v:
				max_v = v
	new_v = max_v + 1
	backup_path = os.path.join(hist_dir, '%s.v%d.js' % (name_no_ext, new_v))
	shutil.copy2(filepath, backup_path)
	# Remove excess versions beyond max
	versions = []
	for f in os.listdir(hist_dir):
		m = pattern.match(f)
		if m:
			versions.append((int(m.group(1)), f))
	versions.sort()
	while len(versions) >= _MAX_HISTORY:
		old_v, old_f = versions.pop(0)
		try:
			os.remove(os.path.join(hist_dir, old_f))
		except Exception:
			pass
	return backup_path, new_v


class UpdateSiteScript():
	def __init__(self):
		self.info = {
			"name":"UpdateSiteScript",
			"description":"Create or update a per-website JS support script. Saves to wwwurljssupport/<domain>/<script>.js. Use <action>delete</action> to remove a script.",
			"parameters":{
				"returnType":"string",
				"required":["site", "script"],
				"properties":{
					"site":{
						"type":"string",
						"description":"Domain name (e.g. google.com) to add/update script for."
					},
					"script":{
						"type":"string",
						"description":"Script name (e.g. 'support_search', 'support_extract', 'support_load'). Do not include .js extension."
					},
					"content":{
						"type":"string",
						"description":"(Optional for update, required for create) Full JavaScript content including metadata header."
					},
					"action":{
						"type":"string",
						"description":"(Optional) 'delete' to remove a script. Default: create or update."
					},
					"info":{
						"type":"string",
						"description":"(Optional) Content for info.md — describes the site's scripts and capabilities."
					},
				},
			},
		}

	def run(self, opts={}, site=None, script=None, content=None, action=None, info=None):
		if not site:
			return "Error: <site> is required."
		if not script:
			return "Error: <script> name is required."

		script_name = script
		if not script_name.endswith('.js'):
			script_name = script_name + '.js'

		if action == 'delete':
			resolved = resolve_script(site, script_name, Options)
			if not resolved or not resolved.get('script_path'):
				return "Script '%s' not found for '%s'." % (script_name, site)
			try:
				os.remove(resolved['script_path'])
				return "Deleted: %s/%s" % (site, script_name)
			except Exception as e:
				return "Error deleting script: %s" % e

		if not content:
			return "Error: <content> is required to create/update a script. Use <action>delete</action> to remove scripts."

		# Resolve the domain path and check if script already exists
		domain_path = None
		resolved = resolve_script(site, script_name, Options)
		backup_info = None
		if resolved and resolved.get('script_path') and os.path.exists(resolved['script_path']):
			backup_path, ver = _backup_existing(resolved['script_path'])
			backup_info = (ver, backup_path)

		# Write the new script
		try:
			path = write_script(site, script_name, content, Options)
		except Exception as e:
			return "Error writing script: %s" % e

		# If info.md content provided, write it too
		if info:
			if not domain_path:
				domain_path = find_write_path(site, Options)
			info_path = os.path.join(domain_path, 'info.md')
			try:
				with open(info_path, 'w') as f:
					f.write(info)
			except Exception as e:
				return "Script saved to %s, but error writing info.md: %s" % (path, e)

		msg = "Saved: %s" % path
		if backup_info:
			msg += " (previous version backed up as .v%d.js)" % backup_info[0]
		return msg
