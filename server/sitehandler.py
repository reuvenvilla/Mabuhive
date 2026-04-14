"""
server/sitehandler.py

Serves HTML pages from frontend/page/.
Route: GET /<page_name>  ->  frontend/page/<page_name>.html

Examples:
  GET /        ->  frontend/page/home.html
  GET /blog    ->  frontend/page/blog.html
"""
import os
from pathlib import Path

from django.http import Http404, HttpResponse
from django.views import View

# Resolve from __file__ so this works regardless of cwd or how the server
# was invoked.
#   __file__  =  <project_root>/server/sitehandler.py
_SERVER   = Path(__file__).resolve().parent
_ROOT     = _SERVER.parent
PAGES_ROOT = str(_ROOT / "frontend" / "page")


class SiteHandler(View):

    def get(self, request, page_name: str = "home") -> HttpResponse:
        pages_root = os.path.realpath(PAGES_ROOT)
        filename   = f"{page_name}.html"
        full_path  = os.path.realpath(os.path.join(pages_root, filename))

        # ── Security: block path traversal ───────────────────────────────────
        if not full_path.startswith(pages_root + os.sep):
            raise Http404("Not found.")

        if not os.path.isfile(full_path):
            raise Http404(f"Page not found: {page_name}")

        with open(full_path, "r", encoding="utf-8") as f:
            html = f.read()

        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        # ── Prevent caching in development ───────────────────────────────────
        response["Cache-Control"] = "no-cache"

        return response
