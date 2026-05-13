"""
api/resources/hives.py

Hive records stored in Supabase Postgres (table: public.hives), with
membership tracked in public.hive_members.

Routes (wired in server/router.py):

    GET   /api/hives                  list / search / paginate (public)
    POST  /api/hives                  create a hive (auth; creator becomes admin)
    GET   /api/hives/me               list the authed user's hives
    GET   /api/hives/<id>             one hive

Query string for GET /api/hives:

    q       — case-insensitive substring match on hives.name
    page    — 1-based page index (default 1)
    size    — page size (default 8, max 50)

Member count comes from public.hives.member_count (kept current by the
trigger the user already set up). Creator's admin role on the hive is
recorded in public.hive_members at create time.

The local-file CRUD scaffold this file used to wrap is intentionally
gone; Supabase is the source of truth now.
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

TABLE          = "hives"
MEMBERS_TABLE  = "hive_members"

NAME_MAX        = 64
DESCRIPTION_MAX = 1000

DEFAULT_PAGE_SIZE = 8
MAX_PAGE_SIZE     = 50


# ── View shaping ─────────────────────────────────────────────────────────────

def public_view(rec: dict) -> dict:
    return {
        "id":           rec.get("id"),
        "name":         rec.get("name") or "",
        "description":  rec.get("description") or "",
        "img_url":    rec.get("img_url") or "",
        "member_count": rec.get("member_count") or 0,
        "created_at":   rec.get("created_at"),
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
            "Supabase table 'public.hives' or 'public.hive_members' not found.",
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


def _ilike_contains(needle: str) -> str:
    """Build an `ilike` filter value that matches anywhere in the string.
    PostgREST splits on commas, so commas in the search term get dropped."""
    safe = needle.replace(",", " ")
    return f"ilike.*{safe}*"


# ── Handlers ─────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class HivesCollection(View):
    """GET: discovery (public list with search + pagination).
       POST: create a hive (auth)."""
    http_method_names = ["get", "post"]

    # ── GET /api/hives ────────────────────────────────────────────────────
    def get(self, request) -> JsonResponse:
        page, size, perr = _parse_pagination(request)
        if perr:
            return perr

        q = (request.GET.get("q") or "").strip()
        params = {
            "select": "*",
            "order":  "created_at.desc",
            "offset": str((page - 1) * size),
            # Fetch one extra so the client can tell whether there's a next
            # page without us round-tripping for an exact count.
            "limit":  str(size + 1),
        }
        if q:
            params["name"] = _ilike_contains(q)

        requester = verify_token(request)
        token = requester.get("token") if requester else None

        status, data = sb.request(TABLE, params=params, user_token=token)
        if status >= 400:
            return _supabase_error(data, status)

        rows = data if isinstance(data, list) else []
        has_more = len(rows) > size
        if has_more:
            rows = rows[:size]

        return JsonResponse({
            "items":    [public_view(r) for r in rows],
            "page":     page,
            "size":     size,
            "has_more": has_more,
        })

    # ── POST /api/hives ───────────────────────────────────────────────────
    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        name = (data.get("name") or "").strip()
        if not name:
            return json_error("missing required field: name", status=400)
        if len(name) > NAME_MAX:
            return json_error(f"name must be <= {NAME_MAX} chars", status=400)

        description = (data.get("description") or "").strip()[:DESCRIPTION_MAX]
        img_url   = (data.get("img_url") or "").strip()

        token = user.get("token")

        # 1. Insert the hive row.
        status, body = sb.request(
            TABLE,
            method="POST",
            user_token=token,
            body={
                "name":        name,
                "description": description,
                "img_url":   img_url,
            },
            prefer="return=representation",
        )
        if status >= 400:
            return _supabase_error(body, status)

        created = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else None)
        if not created or not created.get("id"):
            return json_error("hive creation returned no row", status=502)

        # 2. Add the creator as admin in hive_members. The member_count
        #    trigger keeps hives.member_count fresh — no manual bump needed.
        m_status, m_body = sb.request(
            MEMBERS_TABLE,
            method="POST",
            user_token=token,
            body={
                "hive_id": created["id"],
                "user_id": user["uid"],
                "role":    "admin",
            },
        )
        if m_status >= 400:
            return json_error(
                "hive created, but couldn't add you as admin: "
                + sb.error_message(m_body, m_status),
                status=502,
            )

        # Re-fetch so the response includes the trigger-updated member_count.
        rstatus, rbody = sb.request(
            TABLE,
            params={"id": f"eq.{created['id']}", "select": "*", "limit": "1"},
            user_token=token,
        )
        fresh = rbody[0] if isinstance(rbody, list) and rbody else created
        return JsonResponse(public_view(fresh), status=201)


class HivesItem(View):
    """GET /api/hives/<id>."""
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
            return json_error(f"hive not found: {id}", status=404)
        return JsonResponse(public_view(rows[0]))


class HivesMineHandler(View):
    """GET /api/hives/me — hives the authenticated user belongs to."""
    http_method_names = ["get"]

    def get(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        token = user.get("token")
        q = (request.GET.get("q") or "").strip()

        # 1. Pull the user's memberships so we know which hives to fetch.
        m_status, mems = sb.request(
            MEMBERS_TABLE,
            params={
                "user_id": f"eq.{user['uid']}",
                "select":  "hive_id,role,joined_at",
            },
            user_token=token,
        )
        if m_status >= 400:
            return _supabase_error(mems, m_status)

        if not isinstance(mems, list) or not mems:
            return JsonResponse({"items": []})

        hive_ids   = [m["hive_id"] for m in mems if m.get("hive_id")]
        role_by_id = {m["hive_id"]: m.get("role") or "member" for m in mems}
        if not hive_ids:
            return JsonResponse({"items": []})

        # 2. Fetch the hives themselves.
        params = {
            "id":     f"in.({','.join(hive_ids)})",
            "select": "*",
            "order":  "name.asc",
        }
        if q:
            params["name"] = _ilike_contains(q)

        h_status, data = sb.request(TABLE, params=params, user_token=token)
        if h_status >= 400:
            return _supabase_error(data, h_status)

        rows = data if isinstance(data, list) else []
        items = []
        for rec in rows:
            view = public_view(rec)
            view["my_role"] = role_by_id.get(rec.get("id"), "member")
            items.append(view)
        return JsonResponse({"items": items})
