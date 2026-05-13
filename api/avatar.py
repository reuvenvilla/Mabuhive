"""
api/avatar.py

Avatar upload, end-to-end in Supabase:

    POST /api/avatar  (multipart, field name: "avatar")
        1. Validate the upload (type, size).
        2. Best-effort: delete the user's previous avatars in the bucket
           (any other allowed extension) so we don't leave orphans.
        3. Upload to Supabase Storage at `avatars/<uid>/avatar.<ext>`,
           sending the user's JWT — RLS on storage.objects enforces
           "user can only write into their own folder".
        4. PATCH public.users.avatar_url with the new public URL.

The avatars bucket is public-read; the file's URL is just
    <SUPABASE_URL>/storage/v1/object/public/avatars/<uid>/avatar.<ext>
plus a cache-buster query string so the browser picks up replacements.

No more local-disk serving — the bucket is the source of truth. See
SUPABASE_SETUP.md sections 7 + 8 for the table and bucket setup.
"""
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user
from api import supabase_client as sb
from api.resources.users import TABLE as USERS_TABLE

BUCKET = "avatars"

ALLOWED_TYPES = {
    "image/png":  ".png",
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/gif":  ".gif",
    "image/webp": ".webp",
}

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _other_extensions(active_ext: str) -> set[str]:
    return {ext for ext in ALLOWED_TYPES.values() if ext != active_ext}


@method_decorator(csrf_exempt, name="dispatch")
class AvatarUploadHandler(View):
    """Accept an authenticated multipart upload, push it to Supabase
    Storage, and stamp the new URL onto the user's row."""
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

        uid   = user["uid"]
        token = user.get("token")

        # Best-effort cleanup: drop any old avatar at a different extension
        # so we don't pile up orphans on every format change.
        for old_ext in _other_extensions(ext):
            sb.storage_delete(BUCKET, f"{uid}/avatar{old_ext}", user_token=token)

        path = f"{uid}/avatar{ext}"
        data = upload.read()
        status, body = sb.storage_upload(
            BUCKET, path, data, content_type,
            user_token=token, upsert=True,
        )
        if status >= 400:
            msg = sb.error_message(body, status)
            # Most common deployment-time failure: the bucket doesn't exist
            # or RLS forbids writes to it. Make the hint explicit.
            if status == 404 or "bucket" in msg.lower() or "not found" in msg.lower():
                return json_error(
                    f"avatars bucket missing or unwritable: {msg}. "
                    "See SUPABASE_SETUP.md section 8.",
                    status=502,
                )
            return json_error(msg, status=502)

        # Cache-bust the URL so the browser doesn't keep showing the old image.
        public_url = sb.storage_public_url(BUCKET, path) + f"?v={int(time.time())}"

        # Mirror the new URL onto the user row.
        status, body = sb.request(
            USERS_TABLE,
            method="PATCH",
            user_token=token,
            params={"id": f"eq.{uid}"},
            body={"avatar_url": public_url},
            prefer="return=representation",
        )
        if status >= 400:
            return json_error(sb.error_message(body, status), status=502)

        rows = body if isinstance(body, list) else ([body] if body else [])
        if not rows:
            return json_error(
                "create your user record before uploading an avatar",
                status=409,
            )

        return JsonResponse({
            "avatar_url": public_url,
            "user":       rows[0],
        })
