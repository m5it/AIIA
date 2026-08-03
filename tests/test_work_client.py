import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiia_work.client import WorkClient, WorkError, _Response, DEFAULT_BASE_URL


class FakeTransport:
	"""Records calls and replays a script of (status, text) pairs or exceptions."""
	def __init__(self, script=None):
		self.calls = []
		self.script = script or []
		self._i = 0

	def __call__(self, method, url, headers, body):
		self.calls.append((method, url, dict(headers), body))
		item = self._next()
		if isinstance(item, Exception):
			raise item
		return _Response(*item)

	def _next(self):
		if self._i < len(self.script):
			item = self.script[self._i]
			self._i += 1
			return item
		return (200, "{}")


def _make_client(transport, **kwargs):
	kwargs.setdefault("api_key", "k")
	return WorkClient(transport=transport, **kwargs)


def test_default_base_url():
	client = WorkClient(api_key="k", transport=FakeTransport())
	assert client.base_url == DEFAULT_BASE_URL
	assert not client.base_url.endswith("/")


def test_base_url_option():
	client = WorkClient(api_key="k", options={"AIIA_WORK_BASE_URL": "http://localhost:8006/rest/aiia_work"}, transport=FakeTransport())
	assert client.base_url == "http://localhost:8006/rest/aiia_work"


def test_headers_use_api_key():
	transport = FakeTransport()
	client = _make_client(transport)
	client.list_projects()
	method, url, headers, body = transport.calls[0]
	assert headers.get("X-Api-Key") == "k"
	assert "Authorization" not in headers
	assert method == "GET"
	assert url.endswith("/projects")


def test_headers_use_sso_when_no_key():
	transport = FakeTransport()
	client = WorkClient(api_key=None, sso_token="tok", transport=transport)
	client.list_projects()
	method, url, headers, body = transport.calls[0]
	assert headers.get("Authorization") == "Bearer tok"
	assert "X-Api-Key" not in headers


def test_generate_uses_sso_even_with_key():
	transport = FakeTransport([(200, '{"id":"k1","plain_key":"aiia_abc"}')])
	client = _make_client(transport, sso_token="tok")
	client.generate_api_key("mylabel", "giver")
	method, url, headers, body = transport.calls[0]
	assert url.endswith("/apikeys/generate")
	assert headers.get("Authorization") == "Bearer tok"
	assert "X-Api-Key" not in headers
	assert body == {"label": "mylabel", "role": "giver"}


def test_generate_requires_sso():
	client = _make_client(FakeTransport())
	with pytest.raises(WorkError) as exc:
		client.generate_api_key()
	assert exc.value.status == 401


def test_generate_role_validation():
	client = _make_client(FakeTransport(), sso_token="tok")
	with pytest.raises(WorkError) as exc:
		client.generate_api_key("", "admin")
	assert exc.value.status == 400


def test_create_project_body():
	transport = FakeTransport()
	client = _make_client(transport)
	client.create_project("My project", description="desc", budget=500, currency="USD", tags=["a", "b"])
	method, url, headers, body = transport.calls[0]
	assert method == "POST"
	assert url.endswith("/projects")
	assert body["title"] == "My project"
	assert body["budget"] == 500
	assert body["currency"] == "USD"
	assert body["tags"] == ["a", "b"]


def test_create_project_omits_none_budget():
	transport = FakeTransport()
	client = _make_client(transport)
	client.create_project("T", description="d")
	body = transport.calls[0][3]
	assert body["title"] == "T"
	assert "budget" not in body
	assert "tags" not in body


def test_create_project_requires_title():
	client = _make_client(FakeTransport())
	with pytest.raises(WorkError) as exc:
		client.create_project("  ")
	assert exc.value.status == 400


def test_status_validation():
	client = _make_client(FakeTransport())
	with pytest.raises(WorkError) as exc:
		client.update_project_status("p1", "bogus")
	assert exc.value.status == 400
	assert len(client._transport.calls) == 0


def test_4xx_raises():
	transport = FakeTransport([(403, '{"detail":"forbidden"}')])
	client = _make_client(transport)
	with pytest.raises(WorkError) as exc:
		client.list_projects()
	assert exc.value.status == 403
	assert exc.value.detail == "forbidden"


def test_500_retries_then_raises(monkeypatch):
	monkeypatch.setattr(time, "sleep", lambda s: None)
	transport = FakeTransport([(500, '{"detail":"boom"}')] * 3)
	client = _make_client(transport, retries=2)
	with pytest.raises(WorkError) as exc:
		client.list_projects()
	assert exc.value.status == 500
	assert len(transport.calls) == 3


def test_500_then_success(monkeypatch):
	monkeypatch.setattr(time, "sleep", lambda s: None)
	transport = FakeTransport([(500, '{"detail":"boom"}'), (200, '{"items":[]}')])
	client = _make_client(transport, retries=2)
	assert client.list_projects() == {"items": []}
	assert len(transport.calls) == 2


def test_network_error_retries_then_fails(monkeypatch):
	monkeypatch.setattr(time, "sleep", lambda s: None)
	transport = FakeTransport([ConnectionError("down")] * 3)
	client = _make_client(transport, retries=2)
	with pytest.raises(WorkError) as exc:
		client.list_projects()
	assert exc.value.status == 0
	assert len(transport.calls) == 3


def test_apply_body():
	transport = FakeTransport()
	client = _make_client(transport)
	client.apply_to_project("p1", "hello world")
	method, url, headers, body = transport.calls[0]
	assert url.endswith("/requests/p1/apply")
	assert body == {"message": "hello world"}


def test_accept_decline_endpoints():
	transport = FakeTransport()
	client = _make_client(transport)
	client.accept_request("r1")
	assert transport.calls[0][1].endswith("/requests/r1/accept")
	assert transport.calls[0][0] == "PATCH"
	client.decline_request("r2")
	assert transport.calls[1][1].endswith("/requests/r2/decline")


def test_framework_command_body():
	transport = FakeTransport()
	client = _make_client(transport)
	client.framework_command("create_project", {"title": "x"})
	method, url, headers, body = transport.calls[0]
	assert url.endswith("/framework/command")
	assert body == {"command": "create_project", "payload": {"title": "x"}}


def test_framework_command_requires_name():
	client = _make_client(FakeTransport())
	with pytest.raises(WorkError) as exc:
		client.framework_command("  ")
	assert exc.value.status == 400


def test_env_overrides_option(monkeypatch):
	monkeypatch.setenv("AIIA_WORK_API_KEY", "env-key")
	client = WorkClient(api_key=None, options={"AIIA_WORK_API_KEY": "opt-key"}, transport=FakeTransport())
	assert client.api_key == "env-key"


def test_option_overrides_keyfile(tmp_path, monkeypatch):
	monkeypatch.delenv("AIIA_WORK_API_KEY", raising=False)
	key_file = str(tmp_path / "aiia_work.json")
	with open(key_file, "w") as f:
		json.dump({"plain_key": "from-file"}, f)
	client = WorkClient(api_key=None, options={"AIIA_WORK_API_KEY": "opt-key"}, key_file=key_file, transport=FakeTransport())
	assert client.api_key == "opt-key"


def test_api_key_from_keyfile(tmp_path, monkeypatch):
	monkeypatch.delenv("AIIA_WORK_API_KEY", raising=False)
	key_file = str(tmp_path / "aiia_work.json")
	with open(key_file, "w") as f:
		json.dump({"plain_key": "from-file"}, f)
	client = WorkClient(api_key=None, key_file=key_file, transport=FakeTransport())
	assert client.api_key == "from-file"


def test_save_api_key_persists(tmp_path, monkeypatch):
	monkeypatch.delenv("AIIA_WORK_API_KEY", raising=False)
	key_file = str(tmp_path / "sub" / "aiia_work.json")
	client = WorkClient(api_key="", key_file=key_file, transport=FakeTransport())
	client.save_api_key("aiia_abc", meta={"role": "worker"})
	assert client.api_key == "aiia_abc"
	with open(key_file) as f:
		assert json.load(f)["plain_key"] == "aiia_abc"
	reopened = WorkClient(api_key=None, key_file=key_file, transport=FakeTransport())
	assert reopened.api_key == "aiia_abc"


def test_204_returns_none():
	transport = FakeTransport([(204, "")])
	client = _make_client(transport)
	assert client.revoke_api_key("k1") is None
