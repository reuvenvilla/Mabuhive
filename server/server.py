"""
server/server.py

Two roles + one handler:

  1. WSGI callable for production (Gunicorn):
       gunicorn server.server:application

  2. CLI entry point for development (Django runserver):
       python -m server.server runserver 0.0.0.0:8000

  3. SiteHandler — serves HTML pages from /public/.
     Folded in here (rather than its own file) because page-serving is the
     server's primary job; the handler is small and tightly coupled to it.
       GET /              ->  public/home.html
       GET /<page_name>   ->  public/<page_name>.html

IMPORTANT: always invoke with `python -m server.server`, never as a direct
script (`python server/server.py`). Running as a script inserts /app/server
at sys.path[0], making `import server.router` resolve to server/server.py
(a file) instead of the server/ package — breaking all imports.
"""
import os
import sys
from pathlib import Path

# ── Ensure project root is on sys.path ───────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# ── WSGI application (used by Gunicorn in production) ────────────────────────
from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()

# ── SiteHandler ──────────────────────────────────────────────────────────────
# Imports must come AFTER get_wsgi_application() so Django settings are loaded.
from django.http import Http404, HttpResponse  # noqa: E402
from django.views import View                  # noqa: E402

#   __file__ = <project_root>/server/server.py
PAGES_ROOT = str(Path(__file__).resolve().parent.parent / "public")


class SiteHandler(View):
    """Serves <project_root>/public/<page_name>.html as text/html."""

    def get(self, request, page_name: str = "home") -> HttpResponse:
        pages_root = os.path.realpath(PAGES_ROOT)
        full_path  = os.path.realpath(os.path.join(pages_root, f"{page_name}.html"))

        # ── Security: block path traversal ───────────────────────────────────
        if not full_path.startswith(pages_root + os.sep):
            raise Http404("Not found.")

        if not os.path.isfile(full_path):
            raise Http404(f"Page not found: {page_name}")

        with open(full_path, "r", encoding="utf-8") as f:
            html = f.read()

        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Cache-Control"] = "no-cache"   # dev-friendly default
        return response


# ── CLI entry point (used by runserver in development) ───────────────────────
if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
