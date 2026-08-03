#
# WorkClient — HTTP client for the aiia_work marketplace API.
#
# Implements the REST contract for projects, requests, and API keys:
#   projects : POST/GET/PATCH  /projects[/{id}][/status]
#   requests : POST            /requests/{project_id}/apply
#              GET             /requests/my
#              PATCH           /requests/{id}/accept | /requests/{id}/decline
#   apikeys  : POST            /apikeys/generate   (SSO bearer auth)
#              GET             /apikeys
#              DELETE          /apikeys/{id}
#   bridge   : POST            /framework/command
#
# Write calls require an API key (`X-Api-Key: aiia_...`). The API key is
# resolved in priority order: env `AIIA_WORK_API_KEY` > config option
# `AIIA_WORK_API_KEY` > stored key file (`~/.config/aiia/aiia_work.json`).
#
import json, os, time

DEFAULT_BASE_URL = "https://apis.aiia-frame.work/rest/aiia_work"
DEFAULT_KEY_FILE = os.path.expanduser("~/.config/aiia/aiia_work.json")

VALID_ROLES = ("giver", "worker", "both")
VALID_STATUSES = ("open", "in_progress", "completed", "closed")


class WorkError(Exception):
	#
	def __init__(self, status, detail, endpoint=None):
		self.status = status
		self.detail = detail
		self.endpoint = endpoint
		if status:
			message = "HTTP {}: {}".format(status, detail)
		else:
			message = str(detail)
		super().__init__(message)


class _Response:
	#
	def __init__(self, status_code, text):
		self.status_code = status_code
		self.text = text or ""
	#
	def json(self):
		try:
			return json.loads(self.text)
		except (ValueError, TypeError):
			return {}


def _http_transport(timeout):
	#
	def transport(method, url, headers, body):
		import requests
		resp = requests.request(method, url, headers=headers, json=body, timeout=timeout)
		return _Response(resp.status_code, resp.text)
	return transport


class WorkClient:
	#
	def __init__(self, options=None, api_key=None, sso_token=None, base_url=None,
				 key_file=None, timeout=None, retries=2, transport=None):
		self.options = options if options is not None else {}
		self.base_url = (base_url or self.options.get("AIIA_WORK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
		self.key_file = key_file or self.options.get("AIIA_WORK_KEY_FILE") or DEFAULT_KEY_FILE
		self.timeout = timeout if timeout is not None else self.options.get("AIIA_WORK_TIMEOUT", 30)
		self.retries = retries if retries is not None else self.options.get("AIIA_WORK_RETRIES", 2)
		self.api_key = api_key if api_key is not None else self._resolve_api_key()
		self.sso_token = sso_token if sso_token is not None else (self.options.get("AIIA_WORK_SSO_TOKEN") or "")
		if transport is None:
			transport = _http_transport(self.timeout)
		self._transport = transport
	#
	# --- API key resolution / persistence ---
	#
	def _resolve_api_key(self):
		key = os.environ.get("AIIA_WORK_API_KEY")
		if key:
			return key
		key = self.options.get("AIIA_WORK_API_KEY")
		if key:
			return key
		return self._read_key_file(self.key_file)
	#
	@staticmethod
	def _read_key_file(path):
		try:
			with open(path, "r") as f:
				data = json.load(f)
		except (IOError, OSError, ValueError):
			return None
		return data.get("plain_key") or data.get("api_key")
	#
	def save_api_key(self, plain_key, meta=None):
		data = {"plain_key": plain_key}
		if meta:
			data.update(meta)
		os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
		with open(self.key_file, "w") as f:
			json.dump(data, f)
		os.chmod(self.key_file, 0o600)
		self.api_key = plain_key
	#
	# --- request core ---
	#
	def _request(self, method, path, body=None, auth="auto"):
		url = self.base_url + path
		headers = {"Content-Type": "application/json"}
		if auth == "sso":
			if not self.sso_token:
				raise WorkError(401, "no SSO token configured (env AIIA_WORK_SSO_TOKEN or config AIIA_WORK_SSO_TOKEN)")
			headers["Authorization"] = "Bearer {}".format(self.sso_token)
		elif auth == "key":
			if not self.api_key:
				raise WorkError(401, "no API key configured (env AIIA_WORK_API_KEY, config AIIA_WORK_API_KEY, or !WORK KEYGEN)")
			headers["X-Api-Key"] = self.api_key
		else:
			if self.api_key:
				headers["X-Api-Key"] = self.api_key
			elif self.sso_token:
				headers["Authorization"] = "Bearer {}".format(self.sso_token)
		last = None
		for attempt in range(self.retries + 1):
			try:
				resp = self._transport(method, url, headers, body)
			except WorkError:
				raise
			except Exception as e:
				last = e
				if attempt >= self.retries:
					break
				time.sleep(0.5 * (attempt + 1))
				continue
			if resp.status_code >= 500:
				last = WorkError(resp.status_code, self._detail(resp), url)
				if attempt >= self.retries:
					break
				time.sleep(0.5 * (attempt + 1))
				continue
			if resp.status_code >= 400:
				raise WorkError(resp.status_code, self._detail(resp), url)
			if resp.status_code == 204:
				return None
			return resp.json()
		if isinstance(last, WorkError):
			raise last
		raise WorkError(0, "request failed: {}".format(last), url)
	#
	@staticmethod
	def _detail(resp):
		data = resp.json()
		if isinstance(data, dict) and data.get("detail"):
			return str(data["detail"])
		return resp.text.strip() or "unknown error"
	#
	# --- API keys ---
	#
	def generate_api_key(self, label="", role="both"):
		if role not in VALID_ROLES:
			raise WorkError(400, "role must be one of: {}".format(", ".join(VALID_ROLES)))
		body = {"role": role}
		if label:
			body["label"] = label
		return self._request("POST", "/apikeys/generate", body, auth="sso")
	#
	def list_api_keys(self):
		return self._request("GET", "/apikeys")
	#
	def revoke_api_key(self, key_id):
		return self._request("DELETE", "/apikeys/{}".format(key_id))
	#
	# --- projects ---
	#
	def create_project(self, title, description="", budget=None, currency="USD", tags=None):
		if not title or not str(title).strip():
			raise WorkError(400, "title is required")
		body = {"title": str(title).strip(), "description": description, "currency": currency}
		if budget is not None:
			body["budget"] = budget
		if tags:
			body["tags"] = tags
		return self._request("POST", "/projects", body)
	#
	def list_projects(self):
		return self._request("GET", "/projects")
	#
	def get_project(self, project_id):
		return self._request("GET", "/projects/{}".format(project_id))
	#
	def update_project_status(self, project_id, status):
		if status not in VALID_STATUSES:
			raise WorkError(400, "status must be one of: {}".format(", ".join(VALID_STATUSES)))
		return self._request("PATCH", "/projects/{}/status".format(project_id), {"status": status})
	#
	# --- requests ---
	#
	def apply_to_project(self, project_id, message=""):
		return self._request("POST", "/requests/{}/apply".format(project_id), {"message": message})
	#
	def my_requests(self):
		return self._request("GET", "/requests/my")
	#
	def accept_request(self, request_id):
		return self._request("PATCH", "/requests/{}/accept".format(request_id))
	#
	def decline_request(self, request_id):
		return self._request("PATCH", "/requests/{}/decline".format(request_id))
	#
	# --- framework bridge ---
	#
	def framework_command(self, command, payload=None):
		if not command or not str(command).strip():
			raise WorkError(400, "command is required")
		return self._request("POST", "/framework/command", {"command": str(command).strip(), "payload": payload or {}})
