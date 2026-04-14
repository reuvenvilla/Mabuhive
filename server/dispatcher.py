"""
server/dispatcher.py

Central dispatcher -- maps every URI pattern to its handler.
To add a new feature: import its handler and add a path() here.

URI                        Handler            Description
-------------------------  -----------------  ----------------------------------
/api/static/<filepath>     StaticHandler      Serves frontend/static/ files
/api/echo                  EchoHandler        Echoes back the HTTP request
/                          SiteHandler        Serves frontend/page/home.html
/<page_name>               SiteHandler        Serves frontend/page/<page>.html
"""
import os
from django.urls import path, re_path

from .statichandler import StaticHandler, STATIC_ROOT
from .echohandler   import EchoHandler
from .sitehandler   import SiteHandler, PAGES_ROOT

# Print resolved paths once at startup so misconfiguration is immediately visible
print(f"  [dispatcher] static root : {STATIC_ROOT}  exists={os.path.isdir(STATIC_ROOT)}")
print(f"  [dispatcher] pages  root : {PAGES_ROOT}  exists={os.path.isdir(PAGES_ROOT)}")

urlpatterns = [
    # ── API routes ────────────────────────────────────────────────────────────
    path("api/static/<path:filepath>", StaticHandler.as_view(), name="static"),
    path("api/echo",                   EchoHandler.as_view(),   name="echo"),

    # ── Page routes ──────────────────────────────────────────────────────────
    path("", SiteHandler.as_view(), {"page_name": "home"}, name="home"),
    re_path(r"^(?P<page_name>[a-zA-Z0-9_-]+)/?$", SiteHandler.as_view(), name="page"),
]
