"""
tests/test_handlers.py
Smoke tests for every registered route.

Run:  ./scripts/test.sh
      ./scripts/test.sh --docker
"""
import json

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def mnt(tmp_path, monkeypatch):
    """
    Redirect MNT_ROOT to a tmp dir for the duration of the test.
    The CRUD modules captured MNT_ROOT at import time via `from . import …`,
    so each module's local binding has to be patched separately.
    """
    import api
    import api.create, api.read, api.update, api.delete
    monkeypatch.setattr(api, "MNT_ROOT", str(tmp_path))
    for mod in (api.create, api.read, api.update, api.delete):
        if hasattr(mod, "MNT_ROOT"):
            monkeypatch.setattr(mod, "MNT_ROOT", str(tmp_path))
    return tmp_path


# ── Echo handler ──────────────────────────────────────────────────────────────

class TestEchoHandler:
    def test_get_returns_200(self, client):
        res = client.get("/api/echo")
        assert res.status_code == 200

    def test_response_is_json(self, client):
        res = client.get("/api/echo")
        data = json.loads(res.content)
        assert data["method"] == "GET"
        assert data["path"]   == "/api/echo"

    def test_post_echoes_body(self, client):
        payload = {"hello": "world"}
        res = client.post(
            "/api/echo",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = json.loads(res.content)
        assert data["method"] == "POST"
        assert data["body"]   == payload

    def test_query_params_echoed(self, client):
        res  = client.get("/api/echo?foo=bar&foo=baz")
        data = json.loads(res.content)
        assert "foo" in data["query_params"]


# ── Static handler ────────────────────────────────────────────────────────────

class TestStaticHandler:
    def test_existing_css_file(self, client):
        res = client.get("/public/css/global.css")
        assert res.status_code == 200
        assert "text/css" in res["Content-Type"]

    def test_existing_js_file(self, client):
        res = client.get("/public/js/utils.js")
        assert res.status_code == 200
        assert "javascript" in res["Content-Type"]

    def test_missing_file_returns_404(self, client):
        res = client.get("/public/css/does-not-exist.css")
        assert res.status_code == 404

    def test_path_traversal_blocked(self, client):
        # Django normalises ../ before the handler runs, so we get a routing
        # 301/404 — still a refusal.
        res = client.get("/public/../../settings.py")
        assert res.status_code in (301, 404)


# ── Site handler ──────────────────────────────────────────────────────────────

class TestSiteHandler:
    def test_root_serves_home(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"<!DOCTYPE html>" in res.content

    def test_blog_page(self, client):
        res = client.get("/blog")
        assert res.status_code == 200
        assert b"<!DOCTYPE html>" in res.content

    def test_missing_page_returns_404(self, client):
        res = client.get("/this-page-does-not-exist")
        assert res.status_code == 404


# ── CRUD API handlers ─────────────────────────────────────────────────────────

class TestCrudApi:
    def test_create_then_read(self, client, mnt):
        res = client.post(
            "/api/create?path=notes/hello.txt",
            data=b"hello world",
            content_type="text/plain",
        )
        assert res.status_code == 201
        assert (mnt / "notes" / "hello.txt").read_text() == "hello world"

        res = client.get("/api/read?path=notes/hello.txt")
        assert res.status_code == 200
        assert res.content == b"hello world"

    def test_create_rejects_overwrite(self, client, mnt):
        (mnt / "exists.txt").write_text("old")
        res = client.post("/api/create?path=exists.txt", data=b"new")
        assert res.status_code == 409

    def test_update_overwrites(self, client, mnt):
        (mnt / "x.txt").write_text("old")
        res = client.put("/api/update?path=x.txt", data=b"new")
        assert res.status_code == 200
        assert (mnt / "x.txt").read_text() == "new"

    def test_update_404_when_missing(self, client, mnt):
        res = client.put("/api/update?path=nope.txt", data=b"x")
        assert res.status_code == 404

    def test_delete_file(self, client, mnt):
        (mnt / "rm.txt").write_text("bye")
        res = client.delete("/api/delete?path=rm.txt")
        assert res.status_code == 200
        assert not (mnt / "rm.txt").exists()

    def test_read_directory_returns_listing(self, client, mnt):
        (mnt / "d").mkdir()
        (mnt / "d" / "a.txt").write_text("a")
        (mnt / "d" / "sub").mkdir()
        res = client.get("/api/read?path=d")
        assert res.status_code == 200
        data = json.loads(res.content)
        names = {e["name"]: e["type"] for e in data["entries"]}
        assert names == {"a.txt": "file", "sub": "dir"}

    def test_path_traversal_blocked(self, client, mnt):
        res = client.get("/api/read?path=../settings.py")
        assert res.status_code == 400

    def test_missing_path_param_rejected(self, client, mnt):
        res = client.get("/api/read")
        assert res.status_code == 400
