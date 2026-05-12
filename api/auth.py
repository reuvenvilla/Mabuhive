"""
api/auth.py

Shared authentication helpers. We don't run our own user table — Supabase
Auth is the source of truth. The browser holds a JWT (access token) issued
by Supabase and sends it as an `Authorization: Bearer <token>` header on
every authenticated API call. The server verifies that token here.

Why verify via the Supabase API instead of decoding the JWT locally?

  * Supabase has been shifting between HS256 with a shared secret and
    asymmetric "JWT Signing Keys". The shape of `SUPABASE_JWT_SECRET`
    changes; the API endpoint always works.
  * We don't have to ship PyJWT or worry about audience/issuer drift.

Tradeoff: one HTTPS round trip to Supabase per uncached request. We mitigate
with a small in-memory TTL cache keyed by token, so a typical session reuses
the same lookup for the next 60 seconds.
"""
import json
import os
import time
import urllib.error
import urllib.request
from threading import Lock
from typing import Optional

from django.http import JsonResponse

# token -> {"user": <dict>, "expires_at": <unix ts>}
_TOKEN_CACHE: dict[str, dict] = {}
_TOKEN_CACHE_LOCK = Lock()
_TOKEN_CACHE_TTL = 60     # seconds
_TOKEN_CACHE_MAX = 1024   # bound memory


def _bearer(request) -> Optional[str]:
    """Pull the bearer token out of the Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return auth[7:].strip() or None


def _cache_get(token: str) -> Optional[dict]:
    now = time.time()
    with _TOKEN_CACHE_LOCK:
        entry = _TOKEN_CACHE.get(token)
        if entry and entry["expires_at"] > now:
            return entry["user"]
        # Drop stale or oversized entries opportunistically.
        if entry:
            _TOKEN_CACHE.pop(token, None)
    return None


def _cache_put(token: str, user: dict) -> None:
    with _TOKEN_CACHE_LOCK:
        if len(_TOKEN_CACHE) >= _TOKEN_CACHE_MAX:
            # Cheap eviction: drop oldest.
            try:
                oldest = min(_TOKEN_CACHE.items(), key=lambda kv: kv[1]["expires_at"])[0]
                _TOKEN_CACHE.pop(oldest, None)
            except ValueError:
                pass
        _TOKEN_CACHE[token] = {
            "user": user,
            "expires_at": time.time() + _TOKEN_CACHE_TTL,
        }


def _fetch_user_from_supabase(token: str) -> Optional[dict]:
    """Ask Supabase Auth who this token belongs to."""
    url  = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY") or ""
    if not (url and anon):
        return None

    req = urllib.request.Request(
        f"{url}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey":        anon,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError, ValueError):
        return None

    if not data.get("id"):
        return None

    app_meta = data.get("app_metadata") or {}
    return {
        "uid":       data["id"],
        "email":     data.get("email") or "",
        "provider":  app_meta.get("provider") or "",
        "providers": app_meta.get("providers") or [],
        "raw":       data,
    }


def verify_token(request) -> Optional[dict]:
    """
    Verify the request's bearer token and return a normalised user dict:

        {
          "uid":       "<supabase user uuid>",
          "email":     "<email or empty>",
          "provider":  "google" | "discord" | "email" | ...,
          "providers": ["google", ...],
          "raw":       <Supabase /auth/v1/user response>,
        }

    Returns None on missing/invalid/expired token, or if Supabase env vars
    are missing (useful in dev: auth-gated endpoints will 401 cleanly).
    """
    token = _bearer(request)
    if not token:
        return None

    cached = _cache_get(token)
    if cached is not None:
        return cached

    user = _fetch_user_from_supabase(token)
    if user is not None:
        _cache_put(token, user)
    return user


def require_user(request) -> tuple[Optional[dict], Optional[JsonResponse]]:
    """
    Convenience wrapper for handlers:

        user, err = require_user(request)
        if err:
            return err
        # ... user["uid"] is now safe to use
    """
    user = verify_token(request)
    if not user:
        return None, JsonResponse(
            {"error": "authentication required"}, status=401
        )
    return user, None
