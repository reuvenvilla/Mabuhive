"""
api/supabase_client.py

Thin wrapper around Supabase's PostgREST API. We don't pull in supabase-py
because (a) one HTTP helper is simpler than a transitive dep stack and
(b) we only need a handful of CRUD calls for the users table.

Auth model:
  - Anonymous reads use the anon key as both apikey and Authorization.
    Combined with an RLS "anyone can SELECT" policy, this exposes only
    the public columns.
  - Authenticated writes forward the *user's* JWT in Authorization. RLS
    then enforces "the caller can only insert/update their own row"
    without us re-implementing ownership checks here.

Returns (status, body) tuples so callers can branch on HTTP status and
PostgREST error codes (e.g. 23505 = unique violation, 42P01 = undefined
table). A network failure surfaces as (0, {"message": ...}).
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Union

PostgrestBody = Union[list, dict, None]
PostgrestResponse = tuple[int, PostgrestBody]


def _base_url() -> str:
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set")
    return url


def _anon_key() -> str:
    key = os.environ.get("SUPABASE_ANON_KEY") or ""
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY is not set")
    return key


def request(
    table: str,
    method: str = "GET",
    user_token: Optional[str] = None,
    params: Optional[dict[str, str]] = None,
    body: Optional[PostgrestBody] = None,
    prefer: Optional[str] = None,
    timeout: float = 10.0,
) -> PostgrestResponse:
    """
    Make a PostgREST API call. Falls back to the anon key when no user
    token is provided.
    """
    try:
        base = _base_url()
        anon = _anon_key()
    except RuntimeError as e:
        return 0, {"message": str(e)}

    url = f"{base}/rest/v1/{table}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "apikey":        anon,
        "Authorization": f"Bearer {user_token or anon}",
        "Accept":        "application/json",
    }
    data: Optional[bytes] = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer

    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except (json.JSONDecodeError, ValueError):
            return e.code, {"message": str(e)}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"message": str(e)}

    if not raw:
        return status, None
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, None


# ── Error helpers ────────────────────────────────────────────────────────────

def is_undefined_table(body: PostgrestBody) -> bool:
    """PostgREST surfaces a missing table with Postgres error code 42P01."""
    return isinstance(body, dict) and body.get("code") == "42P01"


def is_unique_violation(body: PostgrestBody) -> bool:
    """Postgres unique_violation = 23505."""
    return isinstance(body, dict) and body.get("code") == "23505"


def error_message(body: PostgrestBody, status: int) -> str:
    if isinstance(body, dict):
        for key in ("message", "msg", "details", "hint", "error"):
            val = body.get(key)
            if val:
                return str(val)
    return f"Supabase error (status {status})"


# ── Storage (objects API) ────────────────────────────────────────────────────
#
# Supabase Storage exposes an S3-ish HTTP API:
#   POST   /storage/v1/object/<bucket>/<path>       upload (binary body)
#   DELETE /storage/v1/object/<bucket>/<path>       delete
#   GET    /storage/v1/object/public/<bucket>/<p>   public download URL
#
# Auth: same model as REST API — anon key as `apikey`, user JWT in
# Authorization. RLS policies on storage.objects enforce per-bucket /
# per-folder ownership.

def storage_upload(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str,
    user_token: Optional[str] = None,
    upsert: bool = True,
    timeout: float = 30.0,
) -> tuple[int, PostgrestBody]:
    """Upload `data` to <bucket>/<path>. Returns (status, body)."""
    try:
        base = _base_url()
        anon = _anon_key()
    except RuntimeError as e:
        return 0, {"message": str(e)}

    quoted_path = urllib.parse.quote(path, safe="/")
    url = f"{base}/storage/v1/object/{bucket}/{quoted_path}"
    headers = {
        "apikey":        anon,
        "Authorization": f"Bearer {user_token or anon}",
        "Content-Type":  content_type or "application/octet-stream",
    }
    if upsert:
        headers["x-upsert"] = "true"

    req = urllib.request.Request(url, method="POST", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except (json.JSONDecodeError, ValueError):
            return e.code, {"message": str(e)}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"message": str(e)}

    if not raw:
        return status, None
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, None


def storage_delete(
    bucket: str,
    path: str,
    user_token: Optional[str] = None,
    timeout: float = 10.0,
) -> None:
    """Delete <bucket>/<path>. Best-effort — errors are swallowed because
    callers use this for cleanup of previous files where 'not found' is
    a perfectly valid outcome."""
    try:
        base = _base_url()
        anon = _anon_key()
    except RuntimeError:
        return

    quoted_path = urllib.parse.quote(path, safe="/")
    url = f"{base}/storage/v1/object/{bucket}/{quoted_path}"
    headers = {
        "apikey":        anon,
        "Authorization": f"Bearer {user_token or anon}",
    }
    req = urllib.request.Request(url, method="DELETE", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except Exception:
        pass


def storage_public_url(bucket: str, path: str) -> str:
    """Build the publicly-accessible URL for an object in a public bucket."""
    base = _base_url()
    quoted_path = urllib.parse.quote(path, safe="/")
    return f"{base}/storage/v1/object/public/{bucket}/{quoted_path}"
