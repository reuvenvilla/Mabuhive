"""
api/resources/users.py

User records keyed by Supabase user UID. Supabase Auth owns identity
(email, password, OAuth linkage); this collection mirrors the editable
display-side bits: username, description, avatar.

Routes (wired in server/router.py):

    GET   /api/users/me              -> own record (auth; 404 if not created)
    POST  /api/users/me              -> create own record (auth; needs username)
    PUT   /api/users/me              -> update own record (auth)
    GET   /api/users/<username>      -> someone else's record (public view)

Visibility:
    Public view  -> uid, username, avatar_url, description
    Owner view   -> public view + email, provider, providers, created_at, updated_at

The owner view is returned from /me. The /<username> endpoint hands back
the public view unless the requester IS that user, in which case they get
the owner view.

There is intentionally NO auto-create on first read: the client decides
when to create (typically by routing the user to /user-create after a 404
on /me). That gives the user a chance to pick their username instead of
getting a derived one.
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
from api.storage import get_storage

COLLECTION = "users"

# Fields the client is allowed to set on create.
CREATE_FIELDS = ["username", "description", "avatar_url"]

# Fields the client is allowed to update.
EDITABLE_FIELDS = ["username", "description", "avatar_url"]

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
USERNAME_RESERVED = {"me", "create", "new", "edit", "admin", "root", "system"}


# ── Views ────────────────────────────────────────────────────────────────────

def public_view(record: dict) -> dict:
    """Fields safe for anyone to see."""
    return {
        "uid":         record.get("id"),
        "username":    record.get("username"),
        "avatar_url":  record.get("avatar_url"),
        "description": record.get("description"),
        "created_at":  record.get("created_at"),
    }


def owner_view(record: dict) -> dict:
    """Full record — only returned to the record's owner."""
    return {
        "uid":         record.get("id"),
        "username":    record.get("username"),
        "avatar_url":  record.get("avatar_url"),
        "description": record.get("description"),
        "email":       record.get("email"),
        "provider":    record.get("provider"),
        "providers":   record.get("providers", []),
        "created_at":  record.get("created_at"),
        "updated_at":  record.get("updated_at"),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_by_username(username: str) -> Optional[dict]:
    """Linear scan — fine for the local backend; swap for an indexed
    query when this moves to Supabase Postgres."""
    target = (username or "").lower()
    for rec in get_storage().list(COLLECTION):
        if (rec.get("username") or "").lower() == target:
            return rec
    return None


def _validate_username(name: str) -> Optional[str]:
    """Return None if valid, otherwise an error message."""
    if not USERNAME_RE.match(name or ""):
        return "username must be 3-32 chars, letters/numbers/_/- only"
    if name.lower() in USERNAME_RESERVED:
        return f"username '{name}' is reserved"
    return None


def _parse_json_body(request) -> tuple[Optional[dict], Optional[JsonResponse]]:
    if not request.body:
        return {}, None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        return None, json_error(f"invalid JSON body: {e}", status=400)
    if not isinstance(data, dict):
        return None, json_error("body must be a JSON object", status=400)
    return data, None


def _sync_auth_fields(uid: str, user: dict, existing: dict) -> dict:
    """Keep auth-side fields (email, provider) in sync with the JWT in case
    they changed (account linking, email update, etc.)."""
    patch = {}
    if user.get("email") and user["email"] != existing.get("email"):
        patch["email"] = user["email"]
    if user.get("provider") and user["provider"] != existing.get("provider"):
        patch["provider"] = user["provider"]
    if user.get("providers") and user["providers"] != existing.get("providers"):
        patch["providers"] = user["providers"]
    if not patch:
        return existing
    return get_storage().update(COLLECTION, uid, patch) or existing


# ── Handlers ─────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class UserMeHandler(View):
    """GET / POST / PUT for the authenticated user's own record."""
    http_method_names = ["get", "post", "put"]

    def get(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        existing = get_storage().get(COLLECTION, user["uid"])
        if existing is None:
            return json_error("user record not created yet", status=404)
        existing = _sync_auth_fields(user["uid"], user, existing)
        return JsonResponse(owner_view(existing))

    def post(self, request) -> JsonResponse:
        """Create the authenticated user's record. Requires a username."""
        user, err = require_user(request)
        if err:
            return err

        if get_storage().get(COLLECTION, user["uid"]) is not None:
            return json_error("user record already exists", status=409)

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        username = (data.get("username") or "").strip()
        validation_err = _validate_username(username)
        if validation_err:
            return json_error(validation_err, status=400)

        conflict = find_by_username(username)
        if conflict and conflict.get("id") != user["uid"]:
            return json_error("username already taken", status=409)

        clean = {k: v for k, v in data.items() if k in CREATE_FIELDS}
        record = get_storage().create(COLLECTION, {
            "id":          user["uid"],
            "username":    username,
            "description": clean.get("description", ""),
            "avatar_url":  clean.get("avatar_url", ""),
            "email":       user.get("email", ""),
            "provider":    user.get("provider") or "email",
            "providers":   user.get("providers")
                            or ([user["provider"]] if user.get("provider") else ["email"]),
        })
        return JsonResponse(owner_view(record), status=201)

    def put(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        existing = get_storage().get(COLLECTION, user["uid"])
        if existing is None:
            return json_error("user record not created yet", status=404)

        data, perr = _parse_json_body(request)
        if perr:
            return perr

        clean = {k: v for k, v in data.items() if k in EDITABLE_FIELDS}

        if "username" in clean:
            candidate = (clean["username"] or "").strip()
            validation_err = _validate_username(candidate)
            if validation_err:
                return json_error(validation_err, status=400)
            conflict = find_by_username(candidate)
            if conflict and conflict.get("id") != user["uid"]:
                return json_error("username already taken", status=409)
            clean["username"] = candidate

        record = get_storage().update(COLLECTION, user["uid"], clean)
        if record is None:
            return json_error("user record not found", status=404)
        return JsonResponse(owner_view(record))


class UserByUsernameHandler(View):
    """GET a user's record by username. Returns the owner view if the
    requester is that same user, otherwise the public view."""
    http_method_names = ["get"]

    def get(self, request, username: str) -> JsonResponse:
        record = find_by_username(username)
        if record is None:
            return json_error(f"user not found: {username}", status=404)

        requester = verify_token(request)
        if requester and requester.get("uid") == record.get("id"):
            return JsonResponse(owner_view(record))
        return JsonResponse(public_view(record))
