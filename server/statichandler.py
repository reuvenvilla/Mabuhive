"""
server/statichandler.py

Serves static files from frontend/static/.
Route: GET /api/static/<filepath>

Example:  GET /api/static/css/global.css
          -> reads frontend/static/css/global.css
          -> responds with correct Content-Type
"""
import mimetypes
import os
from pathlib import Path

from django.http import Http404, HttpResponse
from django.views import View

# Resolve paths from this file's location so they're correct regardless of
# how the server is invoked or what cwd/PYTHONPATH is set to.
#   __file__  =  <project_root>/server/statichandler.py
#   _SERVER   =  <project_root>/server/
#   _ROOT     =  <project_root>/
_SERVER = Path(__file__).resolve().parent
_ROOT   = _SERVER.parent
STATIC_ROOT = str(_ROOT / "frontend" / "static")


class StaticHandler(View):

    def get(self, request, filepath: str) -> HttpResponse:
        static_root = os.path.realpath(STATIC_ROOT)
        requested   = os.path.realpath(os.path.join(static_root, filepath))

        # ── Security: block path traversal (e.g. ../../etc/passwd) ──────────
        if not requested.startswith(static_root + os.sep):
            raise Http404("Not found.")

        if not os.path.isfile(requested):
            raise Http404(f"Static file not found: {filepath}")

        content_type, encoding = mimetypes.guess_type(requested)
        content_type = content_type or "application/octet-stream"

        with open(requested, "rb") as f:
            response = HttpResponse(f.read(), content_type=content_type)

        if encoding:
            response["Content-Encoding"] = encoding

        return response
