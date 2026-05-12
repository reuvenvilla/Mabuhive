"""
server/router.py

Central URL → handler routing table. Wired up via ROOT_URLCONF in settings.py.

URI                          Handler             Description
---------------------------  ------------------  --------------------------------
/public/<filepath>           StaticHandler       Serves files from /public/
/api/echo                    EchoHandler         Echoes back the HTTP request
/api/create                  CreateHandler       Writes a file under /mnt/?path=...
/api/read                    ReadHandler         Reads a file (or lists a dir) at ?path=
/api/update                  UpdateHandler       Overwrites a file at ?path=
/api/delete                  DeleteHandler       Deletes a file or empty dir at ?path=
/api/hives                   HivesCollection     POST create / GET list
/api/hives/<id>              HivesItem           GET read  / PUT update
/api/users                   UsersCollection     POST create / GET list
/api/users/<id>              UsersItem           GET read  / PUT update
/api/teams                   TeamsCollection     POST create / GET list
/api/teams/<id>              TeamsItem           GET read  / PUT update
/                            SiteHandler         Serves public/home.html
/<page_name>                 SiteHandler         Serves public/<page_name>.html

Adding a new endpoint = create a handler file + add one path() entry below.
"""
import os
from django.urls import path, re_path

from .server import SiteHandler, PAGES_ROOT
from .static import StaticHandler, PUBLIC_ROOT

from api.echo   import EchoHandler
from api.create import CreateHandler
from api.read   import ReadHandler
from api.update import UpdateHandler
from api.delete import DeleteHandler

from api.resources.hives import HivesCollection, HivesItem
from api.resources.users import UsersCollection, UsersItem
from api.resources.teams import TeamsCollection, TeamsItem

# Print resolved paths once at startup so misconfiguration is immediately visible
print(f"  [router] public root : {PUBLIC_ROOT}  exists={os.path.isdir(PUBLIC_ROOT)}")
print(f"  [router] pages  root : {PAGES_ROOT}   exists={os.path.isdir(PAGES_ROOT)}")

urlpatterns = [
    # ── Static files ─────────────────────────────────────────────────────────
    path("public/<path:filepath>", StaticHandler.as_view(), name="static"),

    # ── API routes ───────────────────────────────────────────────────────────
    path("api/echo",   EchoHandler.as_view(),   name="echo"),
    path("api/create", CreateHandler.as_view(), name="api-create"),
    path("api/read",   ReadHandler.as_view(),   name="api-read"),
    path("api/update", UpdateHandler.as_view(), name="api-update"),
    path("api/delete", DeleteHandler.as_view(), name="api-delete"),

    # ── Resource CRUD (swappable storage backend) ────────────────────────────
    path("api/hives",            HivesCollection.as_view(), name="hives-list"),
    path("api/hives/<str:id>",   HivesItem.as_view(),       name="hives-item"),
    path("api/users",            UsersCollection.as_view(), name="users-list"),
    path("api/users/<str:id>",   UsersItem.as_view(),       name="users-item"),
    path("api/teams",            TeamsCollection.as_view(), name="teams-list"),
    path("api/teams/<str:id>",   TeamsItem.as_view(),       name="teams-item"),

    # ── Page routes ──────────────────────────────────────────────────────────
    path("", SiteHandler.as_view(), {"page_name": "home"}, name="home"),
    re_path(r"^(?P<page_name>[a-zA-Z0-9_-]+)/?$", SiteHandler.as_view(), name="page"),
]
