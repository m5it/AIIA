import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiia_work.client import WorkError
from aiia_work.console import WorkConsole


class FakeClient:
	"""Duck-typed stand-in for WorkClient that records calls."""
	def __init__(self):
		self.calls = []
		self.options = {"AIIA_WORK_ROLE": "both"}

	def generate_api_key(self, label="", role="both"):
		self.calls.append(("generate_api_key", label, role))
		return {"id": "k1", "plain_key": "aiia_abc", "role": role, "label": label}

	def save_api_key(self, plain_key, meta=None):
		self.calls.append(("save_api_key", plain_key, meta))

	def list_api_keys(self):
		self.calls.append(("list_api_keys",))
		return [{"id": "k1", "role": "both", "label": "x", "created_at": "2026"}]

	def revoke_api_key(self, key_id):
		self.calls.append(("revoke_api_key", key_id))
		return None

	def create_project(self, **kwargs):
		self.calls.append(("create_project", kwargs))
		return {"id": "p1", "title": kwargs["title"], "status": "open",
				"budget": kwargs.get("budget"), "currency": kwargs.get("currency", "USD"),
				"tags": kwargs.get("tags", []), "description": kwargs.get("description", "")}

	def list_projects(self):
		self.calls.append(("list_projects",))
		return []

	def get_project(self, project_id):
		self.calls.append(("get_project", project_id))
		return {"id": project_id, "title": "T", "status": "open", "tags": []}

	def update_project_status(self, project_id, status):
		self.calls.append(("update_project_status", project_id, status))
		return {"id": project_id, "title": "T", "status": status, "tags": []}

	def apply_to_project(self, project_id, message=""):
		self.calls.append(("apply_to_project", project_id, message))
		return {"id": "r1", "project_id": project_id, "status": "pending", "message": message}

	def my_requests(self):
		self.calls.append(("my_requests",))
		return [{"id": "r1", "project_id": "p1", "status": "pending", "message": "hi"}]

	def accept_request(self, request_id):
		self.calls.append(("accept_request", request_id))
		return None

	def decline_request(self, request_id):
		self.calls.append(("decline_request", request_id))
		return None

	def framework_command(self, command, payload=None):
		self.calls.append(("framework_command", command, payload))
		return {"ok": True}


@pytest.fixture
def console():
	return WorkConsole(client=FakeClient())


def test_dispatch_create_with_flags(console):
	out = console.dispatch("!WORK CREATE Build a landing page --budget 500 --tags web,js --desc hello")
	call = console.client.calls[0]
	assert call[0] == "create_project"
	kwargs = call[1]
	assert kwargs["title"] == "Build a landing page"
	assert kwargs["budget"] == 500
	assert kwargs["tags"] == ["web", "js"]
	assert kwargs["description"] == "hello"
	assert kwargs["currency"] == "USD"
	assert "Project:" in out


def test_create_bad_budget(console):
	with pytest.raises(WorkError) as exc:
		console.dispatch("!WORK CREATE T --budget abc")
	assert exc.value.status == 400


def test_create_requires_title(console):
	with pytest.raises(WorkError) as exc:
		console.dispatch("!WORK CREATE")
	assert exc.value.status == 400


def test_dispatch_keygen(console):
	out = console.dispatch("!WORK KEYGEN mylabel worker")
	assert console.client.calls[0] == ("generate_api_key", "mylabel", "worker")
	assert console.client.calls[1][0] == "save_api_key"
	assert console.client.calls[1][1] == "aiia_abc"
	assert "aiia_abc" in out


def test_dispatch_keygen_default_role(console):
	console.dispatch("!WORK KEYGEN")
	assert console.client.calls[0] == ("generate_api_key", "", "both")


def test_dispatch_status(console):
	console.dispatch("!WORK STATUS p1 completed")
	assert console.client.calls[0] == ("update_project_status", "p1", "completed")


def test_dispatch_apply(console):
	console.dispatch("!WORK APPLY p1 I can do this")
	assert console.client.calls[0] == ("apply_to_project", "p1", "I can do this")


def test_dispatch_accept_decline(console):
	console.dispatch("!WORK ACCEPT r1")
	assert console.client.calls[0] == ("accept_request", "r1")
	console.dispatch("!WORK DECLINE r2")
	assert console.client.calls[1] == ("decline_request", "r2")


def test_dispatch_bridge_json(console):
	console.dispatch("!WORK CMD create_project {\"title\": \"x\"}")
	assert console.client.calls[0] == ("framework_command", "create_project", {"title": "x"})


def test_dispatch_bridge_bad_json(console):
	with pytest.raises(WorkError) as exc:
		console.dispatch("!WORK CMD create_project not-json")
	assert exc.value.status == 400


def test_bare_command_without_work_prefix(console):
	console.dispatch("LIST")
	assert console.client.calls[0] == ("list_projects",)


def test_unknown_command(console):
	with pytest.raises(WorkError) as exc:
		console.dispatch("!WORK BOGUS")
	assert exc.value.status == 400


def test_help(console):
	out = console.dispatch("!WORK HELP")
	assert "KEYGEN" in out
	assert "CREATE" in out


def test_loop_quits(console, monkeypatch, capsys):
	inputs = iter(["!WORK LIST", "QUIT"])
	monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
	console.loop()
	assert console.client.calls == [("list_projects",)]
	out = capsys.readouterr().out
	assert "No projects." in out
