"""
api/read.py

Route: GET /api/read?path=<relative/path/under/mnt>

If <path> is a file -> returns its raw bytes (Content-Type sniffed).
If <path> is a dir  -> returns a JSON listing: {"path", "entries": [{name, type}]}
                       useful for navigating directories from the client.

400 on bad/missing path, 404 on not-found.
"""
import mimetypes
import os

from django.http import HttpResponse, JsonResponse
from django.views import View

from . import resolve_path, json_error


class ReadHandler(View):
    http_method_names = ["get"]

    def get(self, request):
        rel = request.GET.get("path", "")
        try:
            full_path = resolve_path(rel)
        except ValueError as e:
            return json_error(str(e), status=400)

        if not os.path.exists(full_path):
            return json_error(f"not found: {rel}", status=404)

        # ── Directory: return JSON listing ───────────────────────────────────
        if os.path.isdir(full_path):
            entries = []
            for name in sorted(os.listdir(full_path)):
                child = os.path.join(full_path, name)
                entries.append({
                    "name": name,
                    "type": "dir" if os.path.isdir(child) else "file",
                })
            return JsonResponse({"path": rel, "entries": entries})

        # ── File: return raw bytes ───────────────────────────────────────────
        content_type, _ = mimetypes.guess_type(full_path)
        with open(full_path, "rb") as f:
            return HttpResponse(f.read(), content_type=content_type or "application/octet-stream")
