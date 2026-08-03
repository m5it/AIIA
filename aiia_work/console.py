#
# WorkConsole — interactive client for the aiia_work marketplace.
#
# All commands are `!WORK ...` (no XML/AI tools here). Start with:
#   python run.py --work
#
#   !WORK KEYGEN [label] [role]        generate an API key (needs SSO token)
#   !WORK KEYS | KEYREVOKE <id>        list / revoke API keys
#   !WORK CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]
#   !WORK LIST | SHOW <id>             list / show projects
#   !WORK STATUS <id> <open|in_progress|completed|closed>
#   !WORK APPLY <project_id> <message>
#   !WORK MY | ACCEPT <rid> | DECLINE <rid>
#   !WORK CMD <name> [json]            framework bridge command
#   !WORK HELP | QUIT
#
import json
from aiia_work.client import WorkClient, WorkError

_COMMANDS = (
	("HELP", "Show this help"),
	("KEYGEN [label] [role]", "Generate an API key (role: giver|worker|both). Requires SSO"),
	("KEYS", "List API keys"),
	("KEYREVOKE <id>", "Revoke an API key"),
	("CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]", "Create a project"),
	("LIST", "List projects"),
	("SHOW <id>", "Show a project"),
	("STATUS <id> <status>", "Set project status (open|in_progress|completed|closed)"),
	("APPLY <project_id> <message>", "Apply to a project as a worker"),
	("MY", "List my requests"),
	("ACCEPT <request_id>", "Accept a worker request (project -> in_progress)"),
	("DECLINE <request_id>", "Decline a worker request"),
	("CMD <name> [json]", "Send a framework bridge command"),
	("QUIT", "Exit"),
)


def _split_flags(args):
	positional = []
	flags = {}
	i = 0
	while i < len(args):
		a = args[i]
		if a.startswith("--"):
			key = a[2:]
			if i + 1 < len(args):
				flags[key] = args[i + 1]
				i += 2
			else:
				flags[key] = ""
				i += 1
		else:
			positional.append(a)
			i += 1
	return positional, flags


def _fmt_project(p):
	lines = ["Project: {} ({})".format(p.get("title", "?"), p.get("id", "?"))]
	lines.append("  status: {}  budget: {} {}  tags: {}".format(
		p.get("status", "?"), p.get("budget", "?"), p.get("currency", ""),
		", ".join(p.get("tags", []) or [])))
	desc = (p.get("description") or "").strip()
	if desc:
		lines.append("  desc: {}".format(desc[:200]))
	return "\n".join(lines)


def _fmt_request(r):
	return "Request {} -> project {}  status={}  msg={}".format(
		r.get("id", "?"), r.get("project_id", "?"), r.get("status", "?"),
		(r.get("message") or "")[:120])


class WorkConsole:
	#
	def __init__(self, client=None, options=None):
		self.client = client or WorkClient(options=options)
		self._running = True
	#
	def loop(self, prompt="!WORK> "):
		print("aiia_work marketplace client — type !WORK HELP for commands, QUIT to exit.")
		while self._running:
			try:
				raw = input(prompt)
			except (EOFError, KeyboardInterrupt):
				print()
				break
			line = raw.strip()
			if not line:
				continue
			if line.upper() in ("QUIT", "EXIT", "Q", "X"):
				break
			try:
				out = self.dispatch(line)
				if out:
					print(out)
			except WorkError as e:
				print("Error: {}".format(e))
			except Exception as e:
				print("Error: {}".format(e))
	#
	def dispatch(self, line):
		tokens = line.split()
		if not tokens:
			return ""
		cmd = tokens[0].upper().lstrip("!")
		if cmd == "WORK":
			if len(tokens) < 2:
				return self.cmd_help([])
			cmd = tokens[1].upper()
			args = tokens[2:]
		else:
			args = tokens[1:]
		handler = {
			"HELP": self.cmd_help,
			"KEYGEN": self.cmd_keygen,
			"KEYS": self.cmd_keys,
			"KEYREVOKE": self.cmd_keyrevoke,
			"CREATE": self.cmd_create,
			"LIST": self.cmd_list,
			"SHOW": self.cmd_show,
			"STATUS": self.cmd_status,
			"APPLY": self.cmd_apply,
			"MY": self.cmd_my,
			"ACCEPT": self.cmd_accept,
			"DECLINE": self.cmd_decline,
			"CMD": self.cmd_bridge,
		}.get(cmd)
		if handler is None:
			raise WorkError(400, "unknown command: {}".format(cmd))
		return handler(args)
	#
	def cmd_help(self, args):
		out = ["Usage: !WORK <command>", ""]
		for name, desc in _COMMANDS:
			out.append("  {:<40} {}".format(name, desc))
		return "\n".join(out)
	#
	def cmd_keygen(self, args):
		label = args[0] if args else ""
		role = args[1] if len(args) > 1 else (self.client.options.get("AIIA_WORK_ROLE") or "both")
		data = self.client.generate_api_key(label, role)
		plain = data.get("plain_key") or data.get("key")
		if plain:
			self.client.save_api_key(plain, meta={"role": role, "label": label})
		return "Generated API key (role={}):\n{}\n(stored for reuse)".format(role, plain) if plain \
			else "API key generated (no plain key in response): {}".format(json.dumps(data))
	#
	def cmd_keys(self, args):
		keys = self.client.list_api_keys()
		items = keys if isinstance(keys, list) else keys.get("items", keys.get("keys", []))
		if not items:
			return "No API keys."
		lines = ["API keys:"]
		for k in items:
			lines.append("  {}  role={}  label={}  created={}".format(
				k.get("id", "?"), k.get("role", "?"), k.get("label", ""), k.get("created_at", "")))
		return "\n".join(lines)
	#
	def cmd_keyrevoke(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK KEYREVOKE <id>")
		self.client.revoke_api_key(args[0])
		return "API key {} revoked.".format(args[0])
	#
	def cmd_create(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK CREATE <title> [--desc ..] [--budget N] [--currency C] [--tags a,b]")
		positional, flags = _split_flags(args)
		if not positional:
			raise WorkError(400, "a title is required")
		kwargs = {"title": " ".join(positional), "description": flags.get("desc", "")}
		if "budget" in flags:
			try:
				kwargs["budget"] = int(flags["budget"])
			except ValueError:
				raise WorkError(400, "budget must be an integer")
		kwargs["currency"] = flags.get("currency", "USD")
		if "tags" in flags:
			kwargs["tags"] = [t.strip() for t in flags["tags"].split(",") if t.strip()]
		return _fmt_project(self.client.create_project(**kwargs))
	#
	def cmd_list(self, args):
		projects = self.client.list_projects()
		items = projects if isinstance(projects, list) else projects.get("items", projects.get("projects", []))
		if not items:
			return "No projects."
		return "\n\n".join(_fmt_project(p) for p in items)
	#
	def cmd_show(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK SHOW <id>")
		return _fmt_project(self.client.get_project(args[0]))
	#
	def cmd_status(self, args):
		if len(args) < 2:
			raise WorkError(400, "usage: !WORK STATUS <id> <open|in_progress|completed|closed>")
		proj = self.client.update_project_status(args[0], args[1])
		return _fmt_project(proj)
	#
	def cmd_apply(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK APPLY <project_id> <message>")
		message = " ".join(args[1:])
		req = self.client.apply_to_project(args[0], message)
		return _fmt_request(req) if isinstance(req, dict) else "Applied to project {}.".format(args[0])
	#
	def cmd_my(self, args):
		requests = self.client.my_requests()
		items = requests if isinstance(requests, list) else requests.get("items", requests.get("requests", []))
		if not items:
			return "No requests."
		return "\n".join(_fmt_request(r) for r in items)
	#
	def cmd_accept(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK ACCEPT <request_id>")
		self.client.accept_request(args[0])
		return "Request {} accepted.".format(args[0])
	#
	def cmd_decline(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK DECLINE <request_id>")
		self.client.decline_request(args[0])
		return "Request {} declined.".format(args[0])
	#
	def cmd_bridge(self, args):
		if not args:
			raise WorkError(400, "usage: !WORK CMD <name> [json]")
		payload = {}
		if len(args) > 1:
			try:
				payload = json.loads(" ".join(args[1:]))
			except ValueError:
				raise WorkError(400, "bridge payload must be valid JSON")
		result = self.client.framework_command(args[0], payload)
		return json.dumps(result, indent=2, sort_keys=True)
