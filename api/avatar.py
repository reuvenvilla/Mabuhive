"""
api/avatar.py

Avatar upload + serving. Avatars live under `<project>/mnt/avatars/<uid>.<ext>`
so they sit alongside the rest of the local file storage.

    POST /api/avatar              multipart upload (field name: "avatar")
    GET  /avatars/<filename>      serve a stored avatar

POST is authenticated — the caller can only overwrite their own avatar
(uid is taken from the JWT, not from the request). On success the profile's
avatar_url is updated and the public URL is returned.

Why a custom serve route instead of /public? Avatars live in /mnt, not
/public — keeping user data out of the static-assets directory means
collectstatic in production won't try to bundle every user's avatar
into the deploy image.
"""
import mimetypes
import os
from pathlib import Path

from django.http import Http404, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user
from api.resources.users import COLLECTION as USERS_COLLECTION
from api.storage import get_storage

AVATARS_DIR = Path(__file__).resolve().parent.parent / "mnt" / "avatars"

ALLOWED_TYPES = {
    "image/png":  ".png",
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/gif":  ".gif",
    "image/webp": ".webp",
}

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _avatar_url_for(filename: str) -> str:
    return f"/avatars/{filename}"


def _remove_old_avatar(uid: str, new_ext: str) -> None:
    """If the user previously uploaded a different format, drop the old file."""
    for ext in set(ALLOWED_TYPES.values()):
        if ext == new_ext:
            continue
        old = AVATARS_DIR / f"{uid}{ext}"
        if old.exists():
            try:
                old.unlink()
            except OSError:
                pass


@method_decorator(csrf_exempt, name="dispatch")
class AvatarUploadHandler(View):
    """Accepts an authenticated multipart upload and writes it to disk."""
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        upload = request.FILES.get("avatar")
        if upload is None:
            return json_error("missing form field: avatar", status=400)

        if upload.size > MAX_BYTES:
            return json_error(
                f"file too large (max {MAX_BYTES // (1024*1024)} MB)",
                status=413,
            )

        content_type = (upload.content_type or "").lower()
        ext = ALLOWED_TYPES.get(content_type)
        if not ext:
            return json_error(
                f"unsupported file type: {content_type or 'unknown'}",
                status=415,
            )

        AVATARS_DIR.mkdir(parents=True, exist_ok=True)
        _remove_old_avatar(user["uid"], ext)

        filename = f"{user['uid']}{ext}"
        target   = AVATARS_DIR / filename

        with open(target, "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        # Update the user row. Bump a cache-buster onto the URL so the
        # browser doesn't keep showing the old image after re-upload.
        # The user record must already exist — clients call /api/users/me
        # POST first, before uploading an avatar.
        url = _avatar_url_for(filename) + f"?v={int(target.stat().st_mtime)}"
        record = get_storage().update(
            USERS_COLLECTION, user["uid"], {"avatar_url": url}
        )
        if record is None:
            return json_error(
                "create your user record before uploading an avatar",
                status=409,
            )

        return JsonResponse({
            "avatar_url": url,
            "user":       record,
        })


class AvatarServeHandler(View):
    """GET /avatars/<filename> — serves an uploaded avatar from disk."""
    http_method_names = ["get"]

    def get(self, request, filename: str) -> HttpResponse:
        root = os.path.realpath(str(AVATARS_DIR))
        requested = os.path.realpath(os.path.join(root, filename))

        if not requested.startswith(root + os.sep):
            raise Http404("Not found.")

        if not os.path.isfile(requested):
            raise Http404(f"Avatar not found: {filename}")

        content_type, _ = mimetypes.guess_type(requested)
        with open(requested, "rb") as f:
            response = HttpResponse(
                f.read(), content_type=content_type or "application/octet-stream"
            )
        response["Cache-Control"] = "public, max-age=3600"
        return response
