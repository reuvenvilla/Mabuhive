"""
api/resources/quest_replies.py

Quest replies — Supabase table public.quest_replies.

Schema (from the user's setup):
    id              uuid PK
    created_at      timestamptz
    created_by      uuid  (references auth.users / public.users)
    quest_id        uuid  (FK to public.quests — added in the schema fix)
    fulfills_quest  bool default false
    img_url         text
    description     text   (a valid reply requires either img_url OR description)

Routes:
    GET  /api/quests/<quest_id>/replies      list replies for one quest, oldest first
    POST /api/quest-replies                   create a reply (auth)
    PUT  /api/quest-replies/<id>              toggle fulfills_quest (quest-creator only).
                                              Side-effect: when fulfills_quest flips,
                                              quest_participants(reply.created_by).completed_at
                                              is set / cleared accordingly.
"""
import json
from typing import Optional

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user, verify_token
from api import supabase_client as sb

REPLIES_TABLE       = "quest_replies"
QUESTS_TABLE        = "quests"
PARTICIPANTS_TABLE  = "quest_participants"
TEAM_MEMBERS_TABLE  = "team_members"

DESCRIPTION_MAX = 1000


# ── View shaping ─────────────────────────────────────────────────────────────

def public_view(rec: dict, author: Optional[dict] = None) -> dict:
    return {
        "id":             rec.get("id"),
        "quest_id":       rec.get("quest_id"),
        "created_by":     rec.get("created_by"),
        "created_at":     rec.get("created_at"),
        "description":    rec.get("description") or "",
        "img_url":        rec.get("img_url") or "",
        "fulfills_quest": bool(rec.get("fulfills_quest")),
        "author_username":   (author or {}).get("username") or "",
        "author_avatar_url": (author or {}).get("avatar_url") or "",
        "author_teams":      [],
    }


def _fetch_quest_hive_id(quest_id: str, token: Optional[str]) -> Optional[str]:
    status, data = sb.request(
        QUESTS_TABLE,
        params={"id": f"eq.{quest_id}", "select": "hive_id", "limit": "1"},
        user_token=token,
    )
    if status >= 400 or not isinstance(data, list) or not data:
        return None
    return data[0].get("hive_id")


def _attach_teams(rows: list, hive_id: Optional[str], token: Optional[str]) -> dict:
    if not rows or not hive_id:
        return {}

    author_ids = list({r.get("created_by") for r in rows if r.get("created_by")})
    if not author_ids:
        return {}

    status, memberships = sb.request(
        TEAM_MEMBERS_TABLE,
        params={
            "user_id": f"in.({','.join(author_ids)})",
            "select":  "team_id,user_id",
        },
        user_token=token,
    )
    if status >= 400 or not isinstance(memberships, list):
        return {}

    team_ids = list({m.get("team_id") for m in memberships if m.get("team_id")})
    if not team_ids:
        return {}

    status, teams = sb.request(
        "teams",
        params={
            "id":      f"in.({','.join(team_ids)})",
            "hive_id": f"eq.{hive_id}",
            "select":  "id,name,color",
        },
        user_token=token,
    )
    if status >= 400 or not isinstance(teams, list):
        return {}

    teams_by_id = {t.get("id"): t for t in teams if t.get("id")}
    out = {uid: [] for uid in author_ids}
    for m in memberships:
        user_id = m.get("user_id")
        team = teams_by_id.get(m.get("team_id"))
        if user_id and team:
            out.setdefault(user_id, []).append(team)
    return out


# ── Helpers ──────────────────────────────────────────────────────────────────

def _supabase_error(body, status: int) -> JsonResponse:
    if sb.is_undefined_table(body):
        return json_error(
            "Supabase table 'public.quest_replies' not found.", status=500,
        )
    return json_error(sb.error_message(body, status), status=502)


def _parse_json_body(request):
    if not request.body:
        return {}, None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        return None, json_error(f"invalid JSON body: {e}", status=400)
    if not isinstance(data, dict):
        return None, json_error("body must be a JSON object", status=400)
    return data, None


def _attach_authors(rows: list, token: Optional[str], hive_id: Optional[str] = None) -> list:
    """Look up usernames + avatars for the reply authors."""
    if not rows:
        return []
    author_ids = list({r.get("created_by") for r in rows if r.get("created_by")})
    by_id = {}
    if author_ids:
        status, users = sb.request(
            "users",
            params={
                "id":     f"in.({','.join(author_ids)})",
                "select": "id,username,avatar_url",
            },
            user_token=token,
        )
        if status < 400 and isinstance(users, list):
            by_id = {u["id"]: u for u in users}

    teams_by_author = _attach_teams(rows, hive_id, token) if hive_id else {}
    views = [public_view(r, by_id.get(r.get("created_by"))) for r in rows]
    for view in views:
        view["author_teams"] = teams_by_author.get(view.get("created_by"), [])
    return views


def _fetch_quest_owner(quest_id: str, token: Optional[str]):
    """Return the quests.created_by uuid for `quest_id`, or None."""
    status, data = sb.request(
        QUESTS_TABLE,
        params={"id": f"eq.{quest_id}", "select": "created_by,id", "limit": "1"},
        user_token=token,
    )
    if status >= 400 or not isinstance(data, list) or not data:
        return None
    return data[0].get("created_by")


# ── /api/quests/<quest_id>/replies ───────────────────────────────────────────

class QuestRepliesHandler(View):
    """GET — list replies for a quest, oldest first."""
    http_method_names = ["get"]

    def get(self, request, quest_id: str) -> JsonResponse:
        requester = verify_token(request)
        token = requester.get("token") if requester else None

        status, data = sb.request(
            REPLIES_TABLE,
            params={
                "quest_id": f"eq.{quest_id}",
                "select":   "*",
                "order":    "created_at.asc",
            },
            user_token=token,
        )
        if status >= 400:
            return _supabase_error(data, status)
        rows = data if isinstance(data, list) else []
        hive_id = _fetch_quest_hive_id(quest_id, token)
        return JsonResponse({"items": _attach_authors(rows, token, hive_id)})


# ── /api/quest-replies ───────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class QuestRepliesCollection(View):
    """POST — create a reply (auth). Body: { quest_id, description?, img_url? }.
    A valid reply needs at least one of description / img_url."""
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        quest_id    = (data.get("quest_id") or "").strip()
        description = (data.get("description") or "").strip()[:DESCRIPTION_MAX]
        img_url     = (data.get("img_url") or "").strip()

        if not quest_id:
            return json_error("missing required field: quest_id", status=400)
        if not (description or img_url):
            return json_error(
                "reply must include a description, an image, or both",
                status=400,
            )

        token = user.get("token")

        # Make sure the quest exists (and grab the row so we can validate.)
        owner = _fetch_quest_owner(quest_id, token)
        if owner is None:
            return json_error(f"quest not found: {quest_id}", status=404)

        record = {
            "quest_id":       quest_id,
            "created_by":     user["uid"],
            "description":    description,
            "img_url":        img_url,
            "fulfills_quest": False,
        }
        status, body = sb.request(
            REPLIES_TABLE,
            method="POST",
            user_token=token,
            body=record,
            prefer="return=representation",
        )
        if status >= 400:
            return _supabase_error(body, status)
        created = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else None)
        if not created or not created.get("id"):
            return json_error("reply creation returned no row", status=502)
        hive_id = _fetch_quest_hive_id(quest_id, token)
        items = _attach_authors([created], token, hive_id)
        return JsonResponse(items[0], status=201)


# ── /api/quest-replies/<id> ──────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class QuestRepliesItem(View):
    """PUT — toggle fulfills_quest on a reply. Only the quest's creator
    can flip this. Also side-effects quest_participants.completed_at for
    the reply's author so they appear in / disappear from the completed
    list on the quest detail page."""
    http_method_names = ["put"]

    def put(self, request, id: str) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr
        if "fulfills_quest" not in data:
            return json_error("body must include fulfills_quest (bool)", status=400)
        fulfills = bool(data.get("fulfills_quest"))

        token = user.get("token")

        # Load the reply so we know its quest_id + author.
        r_status, rdata = sb.request(
            REPLIES_TABLE,
            params={"id": f"eq.{id}", "select": "*", "limit": "1"},
            user_token=token,
        )
        if r_status >= 400:
            return _supabase_error(rdata, r_status)
        rrows = rdata if isinstance(rdata, list) else []
        if not rrows:
            return json_error(f"reply not found: {id}", status=404)
        reply = rrows[0]

        # Only the quest's creator may flip fulfills_quest.
        owner = _fetch_quest_owner(reply["quest_id"], token)
        if owner is None:
            return json_error("parent quest not found", status=404)
        if owner != user["uid"]:
            return json_error("only the quest's creator can fulfill replies", status=403)

        # Flip the bool on the reply.
        u_status, ubody = sb.request(
            REPLIES_TABLE,
            method="PATCH",
            user_token=token,
            params={"id": f"eq.{id}"},
            body={"fulfills_quest": fulfills},
            prefer="return=representation",
        )
        if u_status >= 400:
            return _supabase_error(ubody, u_status)
        urows = ubody if isinstance(ubody, list) else ([ubody] if ubody else [])
        if not urows:
            return json_error("update returned no row", status=502)
        updated = urows[0]

        # Side-effect: mirror completed_at on the matching participant
        # row. If fulfills=True → completed_at = now; else clear it.
        # PostgREST: pass {"completed_at": "now()"} as a literal? No, easier
        # to pass an ISO timestamp the server computes, or `null`.
        from datetime import datetime, timezone
        completed_value = datetime.now(timezone.utc).isoformat() if fulfills else None
        p_status, pbody = sb.request(
            PARTICIPANTS_TABLE,
            method="PATCH",
            user_token=token,
            params={
                "quest_id": f"eq.{reply['quest_id']}",
                "user_id":  f"eq.{reply['created_by']}",
            },
            body={"completed_at": completed_value},
        )
        # If the reply author isn't in quest_participants, that's fine —
        # nothing to flip. Surface other errors as a warning only.
        warn = None
        if p_status >= 400:
            warn = sb.error_message(pbody, p_status)

        view = _attach_authors([updated], token)[0]
        if warn:
            view["warning"] = f"reply updated, but participant sync failed: {warn}"
        return JsonResponse(view)
