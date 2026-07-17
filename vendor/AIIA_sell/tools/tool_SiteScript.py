"""
SiteScript tool — discover and execute per-website JS support scripts.

Usage:
  <SiteScript>
    <site>google.com</site>
    <script>support_search</script>
    <params>{"query":"python programming"}</params>
  </SiteScript>

  <SiteScript>
    <site>google.com</site>
    <action>info</action>
  </SiteScript>

  <SiteScript>
    <site>https://www.google.com</site>
    <script>support_load</script>
  </SiteScript>

The tool resolves the domain, finds the matching script in wwwurljssupport/,
loads the URL in the browser, executes the JS, and returns the result.
"""

import os, json, sys
from config import Options
from tools._site_script_resolver import resolve_script, list_sites, get_site_info
from tools._koslenium_server import ensure_server, send, exec_script


class SiteScript():
	def __init__(self):
		self.info = {
			"name":"SiteScript",
			"description":"Discover and execute per-website JS support scripts. Use <action>info</action> to list available scripts for a site, or <script>name</script> to execute one.",
			"parameters":{
				"returnType":"string",
				"required":[],
				"properties":{
					"site":{
						"type":"string",
						"description":"Domain name (google.com) or full URL (https://www.google.com) to resolve scripts for."
					},
					"script":{
						"type":"string",
						"description":"(Optional) Script name to execute (e.g. 'support_search', 'support_load', 'support_extract'). Omit to list available scripts."
					},
					"action":{
						"type":"string",
						"description":"(Optional) 'info' to show site documentation, 'list' to list all supported sites."
					},
					"params":{
						"type":"string",
						"description":"(Optional) JSON string of parameters to pass to the script (e.g. {\"query\":\"hello\"})."
					},
				},
			},
		}

	def run(self, opts={}, site=None, script=None, action=None, params=None):
		if action == 'list' or (not site and action == 'info'):
			# List all supported sites
			sites = list_sites(Options)
			if not sites:
				return "No site scripts found. Use <UpdateSiteScript> to create one."
			lines = ["=== Supported Sites (%d) ===" % len(sites)]
			for s in sites:
				scripts_str = ", ".join([x['title'] for x in s['scripts']]) if s['scripts'] else "(no scripts)"
				lines.append("  %s: %s" % (s['domain'], scripts_str))
				if s['has_info']:
					lines.append("    [has info.md]")
			return "\n".join(lines)

		if not site:
			return "Error: <site> is required. Use <action>list</action> to see supported sites."

		if action == 'info':
			info = get_site_info(site)
			if not info:
				return "No site scripts found for '%s'. Use <UpdateSiteScript> to create one." % site
			lines = ["=== Site: %s ===" % info['domain']]
			if info['info']:
				lines.append(info['info'])
			else:
				lines.append("(no info.md — scripts found: %d)" % len(info['scripts']))
			if info['scripts']:
				lines.append("\nAvailable scripts:")
				for s in info['scripts']:
					title = s.get('title') or s['name']
					lines.append("  %s (%s)" % (title, s['name']))
					if s.get('description'):
						lines.append("    Description: %s" % s['description'])
					if s.get('usage'):
						lines.append("    Usage: %s" % s['usage'])
					if s.get('params'):
						lines.append("    Params: %s" % s['params'])
					if s.get('returns'):
						lines.append("    Returns: %s" % s['returns'])
			return "\n".join(lines)

		if not script:
			result = resolve_script(site, None, Options)
			if not result:
				return "No site scripts found for '%s'. Use <SiteScript><site>%s</site><action>info</action></SiteScript> to see details." % (site, site)
			scripts = result.get('available_scripts', [])
			if not scripts:
				return "No scripts for '%s'. Use <UpdateSiteScript> to create one." % site
			return "Available scripts for %s: %s. Use <script>name</script> to execute one." % (site, ", ".join(scripts))

		# Resolve the specific script
		result = resolve_script(site, script, Options)
		if not result:
			return "Script '%s' not found for site '%s'. Use <SiteScript><site>%s</site><action>info</action></SiteScript> to see available scripts." % (script, site, site)

		content = result.get('content')
		if not content:
			return "Error: Could not read script '%s' for '%s'." % (script, site)

		# Parse params
		params_dict = {}
		if params:
			try:
				params_dict = json.loads(params)
			except (json.JSONDecodeError, TypeError):
				return "Error: Invalid JSON in <params>: %s" % params

		# Ensure browser server is running
		port = ensure_server()
		if not port:
			return "Error: Could not start koslenium browser server."

		# Navigate to the site if needed
		domain = result.get('domain', site)
		nav_url = "https://www.%s" % domain if '.' in domain and '://' not in site else site
		if '://' not in nav_url:
			nav_url = "https://%s" % nav_url

		# Check if we need to navigate first (for load scripts, already handled)
		# For all scripts, navigate to the base URL first to ensure the page context is right
		nav_cmd = {
			'url': nav_url,
			'wait': 3000,
			'text': True,
		}
		try:
			send(port, nav_cmd)
		except Exception as e:
			return "Error navigating to %s: %s" % (nav_url, e)

		# Inject params into script and execute
		params_js = json.dumps(params_dict)
		full_script = "var PARAMS = %s;\n%s" % (params_js, content)

		try:
			result_data = exec_script(port, full_script, wait=2000)
			if result_data is None:
				return "(script returned no result)"
			# Try to format as JSON for readability
			try:
				parsed = json.loads(result_data)
				return json.dumps(parsed, indent=2, ensure_ascii=False)
			except (json.JSONDecodeError, TypeError):
				return str(result_data)
		except Exception as e:
			return "Error executing script: %s" % e
