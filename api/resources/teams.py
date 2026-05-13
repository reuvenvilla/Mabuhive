"""
api/resources/teams.py

Team records stored in Supabase Postgres (table: public.teams), with
member rows in public.team_members.

Routes:
    POST /api/teams                       create a team inside a hive (auth)
    GET  /api/teams/<id>                  one team + members
    GET  /api/hives/<hive_id>/teams       list teams in a hive (with members inlined)

Membership rules:
    - Only members of the hive can create a team in it.
    - The creator is auto-added to the new team's team_members.
    - team_members has composite PK (team_id, user_id).
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

TABLE              = "teams"
MEMBERS_TABLE      = "team_members"
HIVE_MEMBERS_TABLE = "hive_members"

NAME_MAX = 64


def public_view(rec: dict, members: Optional[list] = None) -> dict:
    return {
        "id":           rec.get("id"),
        "name":         rec.get("name") or "",
        "color":        rec.get("color") or "#333333",
        "hive_id":      rec.get("hive_id"),
        "member_count": rec.get("member_count") or 0,
        "created_at":   rec.get("created_at"),
        "members":      members or [],
    }


def _supabase_error(body, status: int) -> JsonResponse:
    if sb.is_undefined_table(body):
        return json_error(
            "Supabase table missing — check public.teams / team_members.",
            status=500,
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


def _is_hive_member(user_id: str, hive_id: str, token: Optional[str]) -> bool:
    status, data = sb.request(
        HIVE_MEMBERS_TABLE,
        params={
            "user_id": f"eq.{user_id}",
            "hive_id": f"eq.{hive_id}",
            "select":  "user_id",
            "limit":   "1",
        },
        user_token=token,
    )
    return status < 400 and isinstance(data, list) and len(data) > 0


def _members_for(team_ids: list, token: Optional[str]) -> dict:
    """Pull team_members for the given team ids, joined to users for
    username/avatar. Returns dict {team_id: [members...]}."""
    out = {tid: [] for tid in team_ids}
    if not team_ids:
        return out

    m_status, mems = sb.request(
        MEMBERS_TABLE,
        params={
            "team_id": f"in.({','.join(team_ids)})",
            "select":  "team_id,user_id",
        },
        user_token=token,
    )
    if m_status >= 400 or not isinstance(mems, list):
        return out

    user_ids = list({m["user_id"] for m in mems if m.get("user_id")})
    users_by_id = {}
    if user_ids:
        u_status, users = sb.request(
            "users",
            params={
                "id":     f"in.({','.join(user_ids)})",
                "select": "id,username,avatar_url",
            },
            user_token=token,
        )
        if u_status < 400 and isinstance(users, list):
            users_by_id = {u["id"]: u for u in users}

    for m in mems:
        tid = m.get("team_id")
        u = users_by_id.get(m.get("user_id")) or {}
        if tid in out:
            out[tid].append({
                "user_id":    m.get("user_id"),
                "username":   u.get("username") or "",
                "avatar_url": u.get("avatar_url") or "",
            })

    for tid in out:
        out[tid].sort(key=lambda x: (x["username"] or "").lower())
    return out


@method_decorator(csrf_exempt, name="dispatch")
class TeamsCollection(View):
    """POST /api/teams — create a team inside a hive."""
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        hive_id = (data.get("hive_id") or "").strip()
        name    = (data.get("name") or "").strip()
        color   = (data.get("color") or "#333333").strip()

        if not hive_id:
            return json_error("missing required field: hive_id", status=400)
        if not name:
            return json_error("missing required field: name", status=400)
        if len(name) > NAME_MAX:
            return json_error(f"name must be <= {NAME_MAX} chars", status=400)

        token = user.get("token")
        if not _is_hive_member(user["uid"], hive_id, token):
            return json_error("you must be a member of this hive", status=403)

        status, body = sb.request(
            TABLE,
            method="POST",
            user_token=token,
            body={"hive_id": hive_id, "name": name, "color": color},
            prefer="return=representation",
        )
        if status >= 400:
            return _supabase_error(body, status)

        created = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else None)
        if not created or not created.get("id"):
            return json_error("team creation returned no row", status=502)

        # Auto-add the creator to the new team.
        m_status, m_body = sb.request(
            MEMBERS_TABLE,
            method="POST",
            user_token=token,
            body={"team_id": created["id"], "user_id": user["uid"]},
        )
        warn = None
        if m_status >= 400:
            warn = sb.error_message(m_body, m_status)

        rstatus, rbody = sb.request(
            TABLE,
            params={"id": f"eq.{created['id']}", "select": "*", "limit": "1"},
            user_token=token,
        )
        fresh = rbody[0] if isinstance(rbody, list) and rbody else created

        members = _members_for([fresh["id"]], token).get(fresh["id"], [])
        out = public_view(fresh, members)
        if warn:
            out["warning"] = f"team created, but couldn't auto-add you: {warn}"
        return JsonResponse(out, status=201)


class TeamsItem(View):
    """GET /api/teams/<id> — one team with members inlined."""
    http_method_names = ["get"]

    def get(self, request, id: str) -> JsonResponse:
        requester = verify_token(request)
        token = requester.get("token") if requester else None

        status, data = sb.request(
            TABLE,
            params={"id": f"eq.{id}", "select": "*", "limit": "1"},
            user_token=token,
        )
        if status >= 400:
            return _supabase_error(data, status)
        rows = data if isinstance(data, list) else []
        if not rows:
            return json_error(f"team not found: {id}", status=404)

        members = _members_for([id], token).get(id, [])
        return JsonResponse(public_view(rows[0], members))


class HiveTeamsHandler(View):
    """GET /api/hives/<hive_id>/teams — list teams in a hive with each
    team's members inlined."""
    http_method_names = ["get"]

    def get(self, request, hive_id: str) -> JsonResponse:
        requester = verify_token(request)
        token = requester.get("token") if requester else None

        status, data = sb.request(
            TABLE,
            params={
                "hive_id": f"eq.{hive_id}",
                "select":  "*",
                "order":   "created_at.asc",
            },
            user_token=token,
        )
        if status >= 400:
            return _supabase_error(data, status)

        rows = data if isinstance(data, list) else []
        team_ids = [r["id"] for r in rows if r.get("id")]
        members_by_team = _members_for(team_ids, token)

        items = [public_view(r, members_by_team.get(r["id"], [])) for r in rows]
        return JsonResponse({"items": items})
