"""
server/router.py

Central URL → handler routing table. Wired up via ROOT_URLCONF in settings.py.

URI                              Handler                  Description
-------------------------------  -----------------------  ------------------------------------
/public/<filepath>               StaticHandler            Serves files from /public/
/api/config                      ConfigHandler            Public Supabase URL + anon key
/api/echo                        EchoHandler              Echoes back the HTTP request
/api/create                      CreateHandler            Writes a file under /mnt/?path=...
/api/read                        ReadHandler              Reads a file (or lists a dir) at ?path=
/api/update                      UpdateHandler            Overwrites a file at ?path=
/api/delete                      DeleteHandler            Deletes a file or empty dir at ?path=
/api/hives                       HivesCollection          POST create / GET list
/api/hives/<id>                  HivesItem                GET read  / PUT update
/api/teams                       TeamsCollection          POST create / GET list
/api/teams/<id>                  TeamsItem                GET read  / PUT update
/api/users/me                    UserMeHandler            GET/POST/PUT own record (auth)
/api/users/<username>            UserByUsernameHandler    GET someone's record (public view)
/api/avatar                      AvatarUploadHandler      POST multipart avatar upload (auth)
/                                SiteHandler              Serves public/home.html
/user                            SiteHandler              Serves public/user.html (own user)
/user-create                     SiteHandler              Serves public/user-create.html
/user/<username>                 SiteHandler              Serves public/user.html (someone else)
/<page_name>                     SiteHandler              Serves public/<page_name>.html

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
from api.config import ConfigHandler
from api.avatar import AvatarUploadHandler
from api.hive_logo import HiveLogoUploadHandler
from api.quest_image import QuestImageUploadHandler
from api.reply_image import ReplyImageUploadHandler

from api.resources.hives import (
    HivesCollection, HivesItem, HivesMineHandler, HiveMembersHandler,
    HiveJoinHandler, HiveLeaveHandler,
)
from api.resources.quest import (
    QuestCollection, QuestItem, QuestJoinHandler, HiveQuestsHandler,
    QuestParticipantsHandler,
)
from api.resources.quest_replies import (
    QuestRepliesHandler, QuestRepliesCollection, QuestRepliesItem,
)
from api.resources.teams import (
    TeamsCollection, TeamsItem, HiveTeamsHandler,
)
from api.resources.users import UserMeHandler, UserByUsernameHandler

# Print resolved paths once at startup so misconfiguration is immediately visible
print(f"  [router] public root : {PUBLIC_ROOT}  exists={os.path.isdir(PUBLIC_ROOT)}")
print(f"  [router] pages  root : {PAGES_ROOT}   exists={os.path.isdir(PAGES_ROOT)}")

urlpatterns = [
    # ── Static files ─────────────────────────────────────────────────────────
    # Avatars no longer served here — they live in the Supabase Storage
    # bucket and the public URL is written straight into users.avatar_url.
    path("public/<path:filepath>",  StaticHandler.as_view(),       name="static"),

    # ── API: misc ────────────────────────────────────────────────────────────
    path("api/config", ConfigHandler.as_view(), name="api-config"),
    path("api/echo",   EchoHandler.as_view(),   name="echo"),
    path("api/create", CreateHandler.as_view(), name="api-create"),
    path("api/read",   ReadHandler.as_view(),   name="api-read"),
    path("api/update", UpdateHandler.as_view(), name="api-update"),
    path("api/delete", DeleteHandler.as_view(), name="api-delete"),

    # ── API: hives (Supabase) ────────────────────────────────────────────────
    # /me must precede /<id> so it wins the route match.
    path("api/hives",                          HivesCollection.as_view(),  name="hives-list"),
    path("api/hives/me",                       HivesMineHandler.as_view(), name="hives-mine"),
    path("api/hives/<str:id>",                 HivesItem.as_view(),        name="hives-item"),
    path("api/hives/<str:id>/members",         HiveMembersHandler.as_view(), name="hive-members"),
    path("api/hives/<str:id>/join",            HiveJoinHandler.as_view(),    name="hive-join"),
    path("api/hives/<str:id>/leave",           HiveLeaveHandler.as_view(),   name="hive-leave"),
    path("api/hives/<str:hive_id>/quests",     HiveQuestsHandler.as_view(),  name="hive-quests"),
    path("api/hives/<str:hive_id>/teams",      HiveTeamsHandler.as_view(),   name="hive-teams"),
    path("api/hive-logo",                      HiveLogoUploadHandler.as_view(), name="hive-logo-upload"),

    # ── API: quests (Supabase) ───────────────────────────────────────────────
    path("api/quests",                 QuestCollection.as_view(), name="quests-create"),
    path("api/quests/<str:id>",        QuestItem.as_view(),       name="quests-item"),
    path("api/quests/<str:id>/join",         QuestJoinHandler.as_view(),         name="quests-join"),
    path("api/quests/<str:id>/participants", QuestParticipantsHandler.as_view(), name="quests-participants"),
    path("api/quests/<str:quest_id>/replies", QuestRepliesHandler.as_view(),     name="quests-replies"),
    path("api/quest-image",            QuestImageUploadHandler.as_view(), name="quest-image-upload"),
    path("api/quest-replies",          QuestRepliesCollection.as_view(),  name="quest-replies-list"),
    path("api/quest-replies/<str:id>", QuestRepliesItem.as_view(),        name="quest-replies-item"),
    path("api/reply-image",            ReplyImageUploadHandler.as_view(), name="reply-image-upload"),

    # ── API: teams (Supabase) ────────────────────────────────────────────────
    path("api/teams",            TeamsCollection.as_view(), name="teams-list"),
    path("api/teams/<str:id>",   TeamsItem.as_view(),       name="teams-item"),

    # ── API: users (Supabase auth) ───────────────────────────────────────────
    # /me must be registered before /<username> so it wins the match.
    path("api/users/me",               UserMeHandler.as_view(),         name="users-me"),
    path("api/users/<str:username>",   UserByUsernameHandler.as_view(), name="users-by-username"),
    path("api/avatar",                 AvatarUploadHandler.as_view(),   name="avatar-upload"),

    # ── Page routes ──────────────────────────────────────────────────────────
    # Specific multi-segment routes are registered before the catch-all
    # /<page_name> (which only matches a single segment anyway).
    path("", SiteHandler.as_view(), {"page_name": "home"}, name="home"),
    re_path(
        r"^user/(?P<username>[a-zA-Z0-9_-]+)/?$",
        SiteHandler.as_view(),
        {"page_name": "user"},
        name="user-by-username-page",
    ),
    re_path(
        r"^hives/create/?$",
        SiteHandler.as_view(),
        {"page_name": "hives-create"},
        name="hives-create-page",
    ),
    re_path(
        r"^hives/(?P<hive_id>[a-zA-Z0-9_-]+)/?$",
        SiteHandler.as_view(),
        {"page_name": "hive"},
        name="hive-detail-page",
    ),
    re_path(
        r"^quests/(?P<quest_id>[a-zA-Z0-9_-]+)/?$",
        SiteHandler.as_view(),
        {"page_name": "quest"},
        name="quest-detail-page",
    ),
    re_path(r"^(?P<page_name>[a-zA-Z0-9_-]+)/?$", SiteHandler.as_view(), name="page"),
]
