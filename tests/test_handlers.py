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
        res = client.get("/api/static/css/global.css")
        assert res.status_code == 200
        assert "text/css" in res["Content-Type"]

    def test_existing_js_file(self, client):
        res = client.get("/api/static/js/utils.js")
        assert res.status_code == 200
        assert "javascript" in res["Content-Type"]

    def test_missing_file_returns_404(self, client):
        res = client.get("/api/static/css/does-not-exist.css")
        assert res.status_code == 404

    def test_path_traversal_blocked(self, client):
        res = client.get("/api/static/../../settings.py")
        assert res.status_code == 404


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
