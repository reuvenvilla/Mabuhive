"""
api/resources/quest.py

Quest records stored in Supabase Postgres (table: public.quests), with
join records in public.quest_participants.

Routes (wired in server/router.py):

    POST /api/quests                          create a quest in a hive (auth)
    GET  /api/quests/<id>                     read one quest
    PUT  /api/quests/<id>                     update own quest's description + img_url
    POST /api/quests/<id>/join                join a quest (auth)
    GET  /api/hives/<hive_id>/quests          list quests in a hive
                                              ?type=joinable | joined | mine
                                              + page/size pagination

Quest "joinable" = time_finished IS NULL AND caller is not in
quest_participants. "joined" = caller has a quest_participants row,
completed_at IS NULL. "mine" = created_by = caller.
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

TABLE              = "quests"
PARTICIPANTS_TABLE = "quest_participants"
HIVE_MEMBERS_TABLE = "hive_members"

TITLE_MAX       = 128
DESCRIPTION_MAX = 1000
DEFAULT_PAGE_SIZE = 7
MAX_PAGE_SIZE     = 50


# ── View shaping ─────────────────────────────────────────────────────────────

def public_view(rec: dict, creator: Optional[dict] = None) -> dict:
    return {
        "id":            rec.get("id"),
        "title":         rec.get("title") or "",
        "description":   rec.get("description") or "",
        "img_url":       rec.get("img_url") or "",
        "hive_id":       rec.get("hive_id"),
        "created_by":    rec.get("created_by"),
        "created_at":    rec.get("created_at"),
        "time_finished": rec.get("time_finished"),
        "creator_username": (creator or {}).get("username") or "",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_pagination(request) -> tuple[int, int, Optional[JsonResponse]]:
    try:
        page = int(request.GET.get("page", "1"))
        size = int(request.GET.get("size", str(DEFAULT_PAGE_SIZE)))
    except ValueError:
        return 0, 0, json_error("page and size must be integers", status=400)
    page = max(page, 1)
    size = max(min(size, MAX_PAGE_SIZE), 1)
    return page, size, None


def _supabase_error(body, status: int) -> JsonResponse:
    if sb.is_undefined_table(body):
        return json_error(
            "Supabase table missing — check public.quests / quest_participants.",
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


def _is_member(user_id: str, hive_id: str, token: Optional[str]) -> bool:
    """Quick yes/no on hive_members(user_id, hive_id)."""
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


def _attach_creators(rows: list, token: Optional[str]) -> list:
    """Look up usernames for the creators in `rows` and inline them."""
    if not rows:
        return []
    creator_ids = list({r.get("created_by") for r in rows if r.get("created_by")})
    if not creator_ids:
        return [public_view(r) for r in rows]
    status, users = sb.request(
        "users",
        params={
            "id":     f"in.({','.join(creator_ids)})",
            "select": "id,username",
        },
        user_token=token,
    )
    by_id = {}
    if status < 400 and isinstance(users, list):
        by_id = {u["id"]: u for u in users}
    return [public_view(r, by_id.get(r.get("created_by"))) for r in rows]


def _build_views_with_hive(rows: list, token: Optional[str]) -> list:
    """Same as _attach_creators, plus the parent hive's name on each
    view. Used by /api/quests (which spans hives) so each card can show
    where the quest lives."""
    if not rows:
        return []

    creator_ids = list({r.get("created_by") for r in rows if r.get("created_by")})
    hive_ids    = list({r.get("hive_id")    for r in rows if r.get("hive_id")})

    users_by_id = {}
    if creator_ids:
        s, users = sb.request(
            "users",
            params={"id": f"in.({','.join(creator_ids)})", "select": "id,username"},
            user_token=token,
        )
        if s < 400 and isinstance(users, list):
            users_by_id = {u["id"]: u for u in users}

    hives_by_id = {}
    if hive_ids:
        s, hives = sb.request(
            "hives",
            params={"id": f"in.({','.join(hive_ids)})", "select": "id,name"},
            user_token=token,
        )
        if s < 400 and isinstance(hives, list):
            hives_by_id = {h["id"]: h for h in hives}

    out = []
    for r in rows:
        view = public_view(r, users_by_id.get(r.get("created_by")))
        h    = hives_by_id.get(r.get("hive_id"))
        view["hive_name"] = (h or {}).get("name") or ""
        out.append(view)
    return out


# ── /api/quests ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class QuestCollection(View):
    """GET  /api/quests?type=joined|completed|mine — list across all hives.
       POST /api/quests — create a quest in a hive."""
    http_method_names = ["get", "post"]

    # ── GET /api/quests ───────────────────────────────────────────────────
    def get(self, request) -> JsonResponse:
        """List the caller's quests across every hive they're in.

            type=joined     quests the caller has joined (any status)
            type=completed  quests the caller has finished (completed_at not null)
            type=mine       quests the caller created
        """
        user, err = require_user(request)
        if err:
            return err

        page, size, perr = _parse_pagination(request)
        if perr:
            return perr

        kind = (request.GET.get("type") or "joined").lower()
        token = user.get("token")

        common = {
            "select": "*",
            "order":  "created_at.desc",
            "offset": str((page - 1) * size),
            "limit":  str(size + 1),
        }

        if kind == "mine":
            params = {**common, "created_by": f"eq.{user['uid']}"}
            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        elif kind == "completed":
            p_status, pdata = sb.request(
                PARTICIPANTS_TABLE,
                params={
                    "user_id":      f"eq.{user['uid']}",
                    "completed_at": "not.is.null",
                    "select":       "quest_id",
                },
                user_token=token,
            )
            if p_status >= 400:
                return _supabase_error(pdata, p_status)
            quest_ids = [
                p["quest_id"]
                for p in (pdata if isinstance(pdata, list) else [])
                if p.get("quest_id")
            ]
            if not quest_ids:
                return JsonResponse({"items": [], "page": page, "size": size, "has_more": False})
            params = {**common, "id": f"in.({','.join(quest_ids)})"}
            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        else:
            # joined — any quest_participants row for this user, regardless
            # of completion. Default tab on /quests.
            p_status, pdata = sb.request(
                PARTICIPANTS_TABLE,
                params={
                    "user_id": f"eq.{user['uid']}",
                    "select":  "quest_id",
                },
                user_token=token,
            )
            if p_status >= 400:
                return _supabase_error(pdata, p_status)
            quest_ids = [
                p["quest_id"]
                for p in (pdata if isinstance(pdata, list) else [])
                if p.get("quest_id")
            ]
            if not quest_ids:
                return JsonResponse({"items": [], "page": page, "size": size, "has_more": False})
            params = {**common, "id": f"in.({','.join(quest_ids)})"}
            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        has_more = len(rows) > size
        if has_more:
            rows = rows[:size]

        items = _build_views_with_hive(rows, token)
        return JsonResponse({
            "items":    items,
            "page":     page,
            "size":     size,
            "has_more": has_more,
        })

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        hive_id = (data.get("hive_id") or "").strip()
        title   = (data.get("title") or "").strip()
        if not hive_id:
            return json_error("missing required field: hive_id", status=400)
        if not title:
            return json_error("missing required field: title", status=400)
        if len(title) > TITLE_MAX:
            return json_error(f"title must be <= {TITLE_MAX} chars", status=400)

        description = (data.get("description") or "").strip()[:DESCRIPTION_MAX]
        img_url     = (data.get("img_url") or "").strip()

        token = user.get("token")

        # Must belong to the hive to create a quest in it.
        if not _is_member(user["uid"], hive_id, token):
            return json_error("you must be a member of this hive", status=403)

        record = {
            "hive_id":     hive_id,
            "title":       title,
            "description": description,
            "img_url":     img_url,
            "created_by":  user["uid"],
        }
        status, body = sb.request(
            TABLE,
            method="POST",
            user_token=token,
            body=record,
            prefer="return=representation",
        )
        if status >= 400:
            return _supabase_error(body, status)

        created = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else None)
        if not created or not created.get("id"):
            return json_error("quest creation returned no row", status=502)

        # Auto-join the creator. Treated as non-fatal: the quest itself is
        # the important artifact, and the user can join manually from the
        # quest page if this insert ever fails. PK is (quest_id, user_id),
        # so 23505 just means they were already a participant somehow —
        # silently OK to ignore.
        warn = None
        j_status, j_body = sb.request(
            PARTICIPANTS_TABLE,
            method="POST",
            user_token=token,
            body={
                "quest_id": created["id"],
                "user_id":  user["uid"],
                "status":   "joined",
            },
        )
        if j_status >= 400 and not sb.is_unique_violation(j_body):
            warn = sb.error_message(j_body, j_status)

        items = _attach_creators([created], token)
        result = items[0]
        if warn:
            result["warning"] = f"quest created, but auto-join failed: {warn}"
        return JsonResponse(result, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class QuestItem(View):
    """GET/PUT /api/quests/<id>. PUT is owner-only and limited to
    description + img_url (per the edit-pencil UX)."""
    http_method_names = ["get", "put"]

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
            return json_error(f"quest not found: {id}", status=404)
        items = _attach_creators(rows, token)
        return JsonResponse(items[0])

    def put(self, request, id: str) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        token = user.get("token")

        # Ownership check — only the creator can edit.
        f_status, fdata = sb.request(
            TABLE,
            params={"id": f"eq.{id}", "select": "created_by,hive_id", "limit": "1"},
            user_token=token,
        )
        if f_status >= 400:
            return _supabase_error(fdata, f_status)
        rows = fdata if isinstance(fdata, list) else []
        if not rows:
            return json_error(f"quest not found: {id}", status=404)
        if rows[0].get("created_by") != user["uid"]:
            return json_error("you can only edit your own quests", status=403)

        # Pencil UI only edits description + img_url.
        patch = {}
        if "description" in data:
            patch["description"] = (data.get("description") or "")[:DESCRIPTION_MAX]
        if "img_url" in data:
            patch["img_url"] = (data.get("img_url") or "").strip()
        if not patch:
            return json_error("no editable fields provided", status=400)

        u_status, ubody = sb.request(
            TABLE,
            method="PATCH",
            user_token=token,
            params={"id": f"eq.{id}"},
            body=patch,
            prefer="return=representation",
        )
        if u_status >= 400:
            return _supabase_error(ubody, u_status)
        urows = ubody if isinstance(ubody, list) else ([ubody] if ubody else [])
        if not urows:
            return json_error("update returned no row", status=502)
        items = _attach_creators(urows, token)
        return JsonResponse(items[0])


# ── /api/quests/<id>/join ────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class QuestJoinHandler(View):
    """POST /api/quests/<id>/join — insert a quest_participants row.
    Rejects joining a finished quest."""
    http_method_names = ["post"]

    def post(self, request, id: str) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        token = user.get("token")

        # Fetch quest to verify it exists + isn't finished.
        q_status, qdata = sb.request(
            TABLE,
            params={"id": f"eq.{id}", "select": "id,time_finished,hive_id", "limit": "1"},
            user_token=token,
        )
        if q_status >= 400:
            return _supabase_error(qdata, q_status)
        qrows = qdata if isinstance(qdata, list) else []
        if not qrows:
            return json_error(f"quest not found: {id}", status=404)
        quest = qrows[0]
        if quest.get("time_finished"):
            return json_error("quest is finished — cannot join", status=409)

        # Insert the join row. PK is (quest_id, user_id) so 23505 means
        # they already joined.
        j_status, jbody = sb.request(
            PARTICIPANTS_TABLE,
            method="POST",
            user_token=token,
            body={
                "quest_id": id,
                "user_id":  user["uid"],
                "status":   "joined",
            },
            prefer="return=representation",
        )
        if j_status >= 400:
            if sb.is_unique_violation(jbody):
                return json_error("you've already joined this quest", status=409)
            return _supabase_error(jbody, j_status)
        row = jbody[0] if isinstance(jbody, list) and jbody else jbody
        return JsonResponse({"ok": True, "participant": row}, status=201)


# ── /api/quests/<id>/participants ────────────────────────────────────────────

class QuestParticipantsHandler(View):
    """GET /api/quests/<id>/participants — list participants joined to
    users for username/avatar. Sort order matches the /quests/<id> list
    tab spec: completed first (oldest completed_at first), then not-yet-
    completed (oldest joined_at first)."""
    http_method_names = ["get"]

    def get(self, request, id: str) -> JsonResponse:
        requester = verify_token(request)
        token = requester.get("token") if requester else None

        status, parts = sb.request(
            PARTICIPANTS_TABLE,
            params={
                "quest_id": f"eq.{id}",
                "select":   "user_id,status,joined_at,completed_at",
                # NULLS LAST puts un-completed users after completed ones.
                # Within each bucket we sort ASC (oldest first).
                "order":    "completed_at.asc.nullslast,joined_at.asc",
            },
            user_token=token,
        )
        if status >= 400:
            return _supabase_error(parts, status)

        rows = parts if isinstance(parts, list) else []
        if not rows:
            return JsonResponse({"items": []})

        user_ids = list({p["user_id"] for p in rows if p.get("user_id")})
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

        items = []
        for p in rows:
            u = users_by_id.get(p.get("user_id")) or {}
            items.append({
                "user_id":      p.get("user_id"),
                "username":     u.get("username") or "",
                "avatar_url":   u.get("avatar_url") or "",
                "status":       p.get("status") or "joined",
                "joined_at":    p.get("joined_at"),
                "completed_at": p.get("completed_at"),
            })
        return JsonResponse({"items": items})


# ── /api/hives/<hive_id>/quests?type=joinable|joined|mine ────────────────────

class HiveQuestsHandler(View):
    """GET /api/hives/<hive_id>/quests — filtered quest list.

        type=joinable   open quests (time_finished IS NULL), caller not in participants
        type=joined     quests the caller has joined but not completed yet
        type=mine       quests the caller created in this hive
    """
    http_method_names = ["get"]

    def get(self, request, hive_id: str) -> JsonResponse:
        page, size, perr = _parse_pagination(request)
        if perr:
            return perr

        kind = (request.GET.get("type") or "joinable").lower()

        requester = verify_token(request)
        token = requester.get("token") if requester else None

        common = {
            "select":  "*",
            "order":   "created_at.desc",
            "offset":  str((page - 1) * size),
            "limit":   str(size + 1),
            "hive_id": f"eq.{hive_id}",
        }

        if kind == "mine":
            if not requester:
                return json_error("authentication required", status=401)
            params = {**common, "created_by": f"eq.{requester['uid']}"}
            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        elif kind == "joined":
            if not requester:
                return json_error("authentication required", status=401)
            p_status, pdata = sb.request(
                PARTICIPANTS_TABLE,
                params={
                    "user_id":      f"eq.{requester['uid']}",
                    "completed_at": "is.null",
                    "select":       "quest_id",
                },
                user_token=token,
            )
            if p_status >= 400:
                return _supabase_error(pdata, p_status)
            quest_ids = [
                p["quest_id"]
                for p in (pdata if isinstance(pdata, list) else [])
                if p.get("quest_id")
            ]
            if not quest_ids:
                return JsonResponse({"items": [], "page": page, "size": size, "has_more": False})

            params = {
                **common,
                "id":            f"in.({','.join(quest_ids)})",
                "time_finished": "is.null",
            }
            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        else:
            # joinable (default)
            params = {**common, "time_finished": "is.null"}

            exclude_ids: list[str] = []
            if requester:
                p_status, pdata = sb.request(
                    PARTICIPANTS_TABLE,
                    params={
                        "user_id": f"eq.{requester['uid']}",
                        "select":  "quest_id",
                    },
                    user_token=token,
                )
                if p_status < 400 and isinstance(pdata, list):
                    exclude_ids = [p["quest_id"] for p in pdata if p.get("quest_id")]
            if exclude_ids:
                params["id"] = f"not.in.({','.join(exclude_ids)})"

            status, data = sb.request(TABLE, params=params, user_token=token)
            if status >= 400:
                return _supabase_error(data, status)
            rows = data if isinstance(data, list) else []

        has_more = len(rows) > size
        if has_more:
            rows = rows[:size]
        items = _attach_creators(rows, token)
        return JsonResponse({
            "items":    items,
            "page":     page,
            "size":     size,
            "has_more": has_more,
        })
