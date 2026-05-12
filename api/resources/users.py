"""
api/resources/users.py

User records stored in Supabase Postgres (table: public.users), keyed by
the same UUID as auth.users. Identity (email, password, OAuth linkage)
lives in Supabase Auth; this table mirrors the editable display-side
bits only: username, description, avatar_url.

Email + provider are NOT stored here — they come from the JWT verify
call in api.auth.verify_token, so they're always fresh and never get
out of sync with Supabase Auth.

Routes (wired in server/router.py):

    GET   /api/users/me              -> own record (auth; 404 if not created)
    POST  /api/users/me              -> create own record (auth; needs username)
    PUT   /api/users/me              -> update own record (auth)
    GET   /api/users/<username>      -> someone else's record (public view)

Visibility:
    Public view  -> uid, username, avatar_url, description, created_at
    Owner view   -> public view + email, provider, providers, updated_at

The owner view is returned from /me. /<username> hands back the public
view unless the requester IS that user.

Authorisation is enforced by Supabase RLS — we forward the user's JWT
on writes. Anonymous reads use the anon key (RLS public-read policy).

Run the SQL in SUPABASE_SETUP.md step 7 once per project before this
will work.
"""
import json
import re
from typing import Optional

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user, verify_token
from api import supabase_client as sb

TABLE = "users"

CREATE_FIELDS   = ["username", "description", "avatar_url"]
EDITABLE_FIELDS = ["username", "description", "avatar_url"]

USERNAME_RE       = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
USERNAME_RESERVED = {"me", "create", "new", "edit", "admin", "root", "system"}
DESCRIPTION_MAX   = 500


# ── View shaping ─────────────────────────────────────────────────────────────

def public_view(record: dict) -> dict:
    """Fields safe for anyone to see."""
    return {
        "uid":         record.get("id"),
        "username":    record.get("username"),
        "avatar_url":  record.get("avatar_url") or "",
        "description": record.get("description") or "",
        "created_at":  record.get("created_at"),
    }


def owner_view(record: dict, auth_user: Optional[dict] = None) -> dict:
    """Full record — only returned to the record's owner. Identity fields
    (email, provider) are merged in from Supabase Auth, not the table."""
    out = public_view(record)
    out["updated_at"] = record.get("updated_at")
    if auth_user is not None:
        out["email"]     = auth_user.get("email", "")
        out["provider"]  = auth_user.get("provider", "")
        out["providers"] = auth_user.get("providers", []) or []
    return out


# ── Lookup helpers ───────────────────────────────────────────────────────────

def _missing_table_error() -> JsonResponse:
    return json_error(
        "Supabase table 'public.users' not found. Run the SQL in "
        "SUPABASE_SETUP.md step 7 in the Supabase SQL editor.",
        status=500,
    )


def _supabase_error(body, status: int) -> JsonResponse:
    return json_error(sb.error_message(body, status), status=502)


def find_by_uid(uid: str, token: Optional[str] = None):
    status, data = sb.request(
        TABLE,
        params={"id": f"eq.{uid}", "select": "*", "limit": "1"},
        user_token=token,
    )
    if status >= 400:
        if sb.is_undefined_table(data):
            return None, _missing_table_error()
        return None, _supabase_error(data, status)
    rec = data[0] if isinstance(data, list) and data else None
    return rec, None


def find_by_username(username: str, token: Optional[str] = None):
    name = (username or "").strip()
    if not name:
        return None, None
    # ilike with no wildcards = case-insensitive equality.
    status, data = sb.request(
        TABLE,
        params={"username": f"ilike.{name}", "select": "*", "limit": "1"},
        user_token=token,
    )
    if status >= 400:
        if sb.is_undefined_table(data):
            return None, _missing_table_error()
        return None, _supabase_error(data, status)
    rec = data[0] if isinstance(data, list) and data else None
    return rec, None


# ── Validation ───────────────────────────────────────────────────────────────

def _validate_username(name: str) -> Optional[str]:
    if not USERNAME_RE.match(name or ""):
        return "username must be 3-32 chars, letters/numbers/_/- only"
    if name.lower() in USERNAME_RESERVED:
        return f"username '{name}' is reserved"
    return None


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


# ── Handlers ─────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class UserMeHandler(View):
    """GET / POST / PUT for the authenticated user's own record."""
    http_method_names = ["get", "post", "put"]

    def get(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        rec, ferr = find_by_uid(user["uid"], token=user.get("token"))
        if ferr:
            return ferr
        if rec is None:
            return json_error("user record not created yet", status=404)
        return JsonResponse(owner_view(rec, user))

    def post(self, request) -> JsonResponse:
        """
        Create the authenticated user's record.

        No SELECT pre-checks here on purpose: the previous version did a
        find_by_uid + find_by_username before inserting, which meant a
        transient SELECT failure (or an RLS misconfig) would block create
        even though the INSERT itself would have worked. We let Postgres
        be the source of truth — the PK ensures one row per uid and the
        unique index on lower(username) prevents duplicates — and we
        translate the 23505 error code into a meaningful 409.
        """
        user, err = require_user(request)
        if err:
            return err

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        username = (data.get("username") or "").strip()
        vmsg = _validate_username(username)
        if vmsg:
            return json_error(vmsg, status=400)

        record = {
            "id":          user["uid"],
            "username":    username,
            "description": (data.get("description") or "")[:DESCRIPTION_MAX],
            "avatar_url":  data.get("avatar_url") or "",
        }
        status, body = sb.request(
            TABLE,
            method="POST",
            user_token=user.get("token"),
            body=record,
            prefer="return=representation",
        )

        if status >= 400:
            if sb.is_undefined_table(body):
                return _missing_table_error()
            if sb.is_unique_violation(body):
                # 23505 hits on either the primary key (id) or the
                # case-insensitive username index. Tell them apart by
                # looking at the constraint name / error details.
                msg = ""
                if isinstance(body, dict):
                    msg = (body.get("message") or "") + " " + (body.get("details") or "")
                if "username" in msg.lower():
                    return json_error("username already taken", status=409)
                return json_error("user record already exists", status=409)
            return _supabase_error(body, status)

        rec = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else record)
        return JsonResponse(owner_view(rec, user), status=201)

    def put(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        existing, ferr = find_by_uid(user["uid"], token=user.get("token"))
        if ferr:
            return ferr
        if existing is None:
            return json_error("user record not created yet", status=404)

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        clean = {k: v for k, v in data.items() if k in EDITABLE_FIELDS}

        if "username" in clean:
            candidate = (clean["username"] or "").strip()
            vmsg = _validate_username(candidate)
            if vmsg:
                return json_error(vmsg, status=400)
            conflict, cerr = find_by_username(candidate, token=user.get("token"))
            if cerr:
                return cerr
            if conflict and conflict.get("id") != user["uid"]:
                return json_error("username already taken", status=409)
            clean["username"] = candidate

        if "description" in clean and isinstance(clean["description"], str):
            clean["description"] = clean["description"][:DESCRIPTION_MAX]

        if not clean:
            return JsonResponse(owner_view(existing, user))

        status, body = sb.request(
            TABLE,
            method="PATCH",
            user_token=user.get("token"),
            params={"id": f"eq.{user['uid']}"},
            body=clean,
            prefer="return=representation",
        )
        if status >= 400:
            if sb.is_undefined_table(body):
                return _missing_table_error()
            if sb.is_unique_violation(body):
                return json_error("username already taken", status=409)
            return _supabase_error(body, status)

        rec = body[0] if isinstance(body, list) and body else existing
        return JsonResponse(owner_view(rec, user))


class UserByUsernameHandler(View):
    """GET a user's record by username. Returns the owner view if the
    requester is that same user, otherwise the public view."""
    http_method_names = ["get"]

    def get(self, request, username: str) -> JsonResponse:
        # Verifying the token (if any) lets us hand back the owner view
        # when someone visits their own /user/<their-username> URL.
        requester = verify_token(request)
        token = requester.get("token") if requester else None

        rec, ferr = find_by_username(username, token=token)
        if ferr:
            return ferr
        if rec is None:
            return json_error(f"user not found: {username}", status=404)

        if requester and requester.get("uid") == rec.get("id"):
            return JsonResponse(owner_view(rec, requester))
        return JsonResponse(public_view(rec))
