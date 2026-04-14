"""
server/server.py

Two roles:
  1. WSGI callable for production (Gunicorn):
       gunicorn server.server:application

  2. CLI entry point for development (Django runserver):
       python -m server.server runserver 0.0.0.0:8000

IMPORTANT: always invoke with `python -m server.server`, never as a direct
script (`python server/server.py`). Running as a script inserts /app/server
at sys.path[0], making `import server.dispatcher` resolve to server/server.py
(a file) instead of the server/ package — breaking all imports.
"""
import os
import sys

# ── Ensure project root is on sys.path ───────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# ── WSGI application (used by Gunicorn in production) ────────────────────────
from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()

# ── CLI entry point (used by runserver in development) ───────────────────────
if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
