"""
server/static.py

Serves static files from /public/.
Route: GET /public/<filepath>

Examples:
  GET /public/css/global.css   ->  public/css/global.css
  GET /public/js/NavBar.jsx    ->  public/js/NavBar.jsx
  GET /public/images/logo.png  ->  public/images/logo.png

Path traversal (../) is blocked. Content-Type is sniffed from the filename.
"""
import mimetypes
import os
from pathlib import Path

from django.http import Http404, HttpResponse
from django.views import View

#   __file__ = <project_root>/server/static.py
PUBLIC_ROOT = str(Path(__file__).resolve().parent.parent / "public")


class StaticHandler(View):

    def get(self, request, filepath: str) -> HttpResponse:
        public_root = os.path.realpath(PUBLIC_ROOT)
        requested   = os.path.realpath(os.path.join(public_root, filepath))

        # ── Security: block path traversal (e.g. ../../etc/passwd) ──────────
        if not requested.startswith(public_root + os.sep):
            raise Http404("Not found.")

        if not os.path.isfile(requested):
            raise Http404(f"Static file not found: {filepath}")

        content_type, encoding = mimetypes.guess_type(requested)
        content_type = content_type or "application/octet-stream"

        with open(requested, "rb") as f:
            response = HttpResponse(f.read(), content_type=content_type)

        if encoding:
            response["Content-Encoding"] = encoding

        response["Cache-Control"] = "no-cache"   # dev-friendly default
        return response
