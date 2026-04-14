"""
settings.py — Django project settings.
Lives at the project root. Referenced via DJANGO_SETTINGS_MODULE=settings.
All paths are resolved relative to this file's location (project root).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key-change-in-production")
DEBUG      = os.environ.get("DEBUG", "True") == "True"
# settings.py
raw_hosts = os.environ.get("ALLOWED_HOSTS", "").strip()
if not raw_hosts:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
else:
    ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",")]
# ── Apps & Middleware ─────────────────────────────────────────────────────────
# Our handlers need no Django app registration (no models, signals, or
# management commands). Keeping it out also avoids any import path ambiguity.
INSTALLED_APPS = [
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ── Routing ───────────────────────────────────────────────────────────────────
# All URI → handler wiring lives in server/dispatcher.py
# This part is responsible for redirecting to different hadlers
# depending on the path described (website.com/api/* -> API Handler, etc)
ROOT_URLCONF = "server.dispatcher"

# ── WSGI, Python specific, required for Django to run
WSGI_APPLICATION = "server.server.application"

# ── Templates ────────────────────────────────────────────────────────────────
# sitehandler.py reads pages directly from disk; Django templates not used here.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend" / "page"],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]

# ── No database (local file storage for now) ─────────────────────────────────
DATABASES = {}

# ── Storage paths ─────────────────────────────────────────────────────────────
FRONTEND_DIR  = BASE_DIR / "frontend"
PAGES_DIR     = FRONTEND_DIR / "page"
STATIC_DIR    = FRONTEND_DIR / "static"
BUILD_DIR     = BASE_DIR / "build"

# ── Static files ──────────────────────────────────────────────────────────────
# STATIC_URL must match the /api/static/ prefix used in the HTML pages.
#
# How static file serving works by environment:
#
#   Development (runserver):
#     Django StaticFilesHandler intercepts /api/static/* before the URL router,
#     finds files via STATICFILES_DIRS, and serves them directly.
#
#   Production (Gunicorn + NGINX):
#     collectstatic gathers STATICFILES_DIRS into STATIC_ROOT.
#     NGINX serves /api/static/* directly from STATIC_ROOT.
#
STATIC_URL       = "/api/static/"
STATIC_ROOT      = BUILD_DIR / "staticfiles"
STATICFILES_DIRS = [STATIC_DIR]   # where our source static files live

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
