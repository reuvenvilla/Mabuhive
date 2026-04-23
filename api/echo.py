"""
api/echo.py

Echoes back the full HTTP request as JSON.
Route: ALL methods → /api/echo

Useful for:
  - Debugging what headers/body the client is sending
  - Verifying NGINX proxy_pass headers are forwarded correctly
  - Smoke-testing that the router is wired up

Example response:
  {
    "method": "POST",
    "path": "/api/echo",
    "headers": { "Content-Type": "application/json", ... },
    "query_params": { "foo": ["bar"] },
    "body": { ... }
  }
"""
import json

from django.http import JsonResponse
from django.views import View


class EchoHandler(View):
    # Accept every HTTP verb
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch so every method hits the same echo logic."""
        body = self._parse_body(request)
        payload = {
            "method":       request.method,
            "path":         request.path,
            "headers":      dict(request.headers),
            "query_params": dict(request.GET.lists()),   # preserves multi-values
            "body":         body,
        }
        return JsonResponse(payload, json_dumps_params={"indent": 2})

    @staticmethod
    def _parse_body(request):
        """Try JSON first, fall back to raw string, return None if empty."""
        if not request.body:
            return None
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return request.body.decode("utf-8", errors="replace")
