#--
# class CommandsSites — site-script commands
class CommandsSites():
	#
	def CMD_SITE_LIST(self, inp=""):
		"""List all sites with available scripts."""
		from tools._site_script_resolver import list_sites
		sites = list_sites(self.handle.Options)
		if not sites:
			print("No site scripts found. Use <UpdateSiteScript> to create one.")
			return 2
		print("Supported websites (%d):" % len(sites))
		for s in sites:
			scripts = ", ".join(s['scripts']) if s['scripts'] else "(no scripts yet)"
			print("  %s: %s" % (s['domain'], scripts))
		return 2

	def CMD_SITE(self, inp=""):
		"""Show info for a specific site."""
		a = inp.strip().split(None, 1)
		if len(a) < 2:
			print("Usage: !SITE <domain>")
			print("Example: !SITE google.com")
			return 2
		from tools._site_script_resolver import get_site_info
		info = get_site_info(a[1], self.handle.Options)
		if not info:
			print("No site scripts found for '%s'." % a[1])
			print("Use <UpdateSiteScript> to create one.")
			return 2
		print("Site: %s" % info['domain'])
		print("Path: %s" % info['path'])
		if info['info']:
			print("\n--- info.md ---")
			print(info['info'])
		if info['scripts']:
			print("\nScripts (%d):" % len(info['scripts']))
			for s in info['scripts']:
				meta = s.get('meta', {})
				desc = meta.get('description', '') or ''
				print("  %s%s" % (s['name'], " — %s" % desc if desc else ""))
		else:
			print("\nNo scripts yet. Use !SITE_UPDATE %s <script_name> to add one." % info['domain'])
		return 2

	def CMD_SITE_UPDATE(self, inp=""):
		"""Create or update a site script from stdin or interactively."""
		a = inp.strip().split(None, 2)
		if len(a) < 3:
			print("Usage: !SITE_UPDATE <domain> <script_name>")
			print("Example: !SITE_UPDATE google.com support_search")
			print("Then paste the JS content and end with Ctrl+D (or Ctrl+Z on Windows).")
			return 2
		domain = a[1]
		script = a[2]
		from tools._site_script_resolver import write_script
		print("Paste JS content (end with Ctrl+D on a new line, or Ctrl+C to cancel):")
		lines = []
		try:
			while True:
				line = input()
				lines.append(line)
		except (EOFError, KeyboardInterrupt):
			pass
		content = "\n".join(lines)
		if not content.strip():
			print("No content provided. Aborting.")
			return 2
		try:
			path = write_script(domain, script, content, self.handle.Options)
			print("Saved: %s" % path)
		except Exception as e:
			print("Error: %s" % e)
		return 2

