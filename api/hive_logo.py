"""
api/hive_logo.py

Hive logo upload, end-to-end in Supabase Storage.

    POST /api/hive-logo  (multipart, field name: "logo")

The hive doesn't exist yet at upload time (the client uploads, gets a
URL back, then POSTs to /api/hives with that URL in `img_url`), so we
key files by the uploader's uid + a millisecond timestamp:

    hive_logos/<uid>/<ts>.<ext>

RLS on storage.objects (see SUPABASE_SETUP.md) requires the first folder
segment to match the uploader's auth.uid(), so a malicious client can't
write under another user's path.

Tradeoff: a user that picks a logo, uploads, then bails before creating
the hive leaves an orphan file behind. The files are <5 MB each and the
RLS policy lets the user delete their own, so we can sweep them later
if it ever becomes a real concern.
"""
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user
from api import supabase_client as sb

BUCKET = "hive_logos"

ALLOWED_TYPES = {
    "image/png":  ".png",
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/gif":  ".gif",
    "image/webp": ".webp",
}

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@method_decorator(csrf_exempt, name="dispatch")
class HiveLogoUploadHandler(View):
    """Accept an authenticated multipart upload and push it to the
    hive_logos bucket. Returns the public URL the client can stamp onto
    the hive row."""
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        upload = request.FILES.get("logo")
        if upload is None:
            return json_error("missing form field: logo", status=400)

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

        uid       = user["uid"]
        token     = user.get("token")
        timestamp = int(time.time() * 1000)
        path      = f"{uid}/{timestamp}{ext}"

        data = upload.read()
        status, body = sb.storage_upload(
            BUCKET, path, data, content_type,
            user_token=token, upsert=False,
        )
        if status >= 400:
            msg = sb.error_message(body, status)
            if (status == 404
                or "bucket" in msg.lower()
                or "not found" in msg.lower()):
                return json_error(
                    f"hive_logos bucket missing or unwritable: {msg}. "
                    "See SUPABASE_SETUP.md section 8.",
                    status=502,
                )
            return json_error(msg, status=502)

        return JsonResponse({
            "img_url": sb.storage_public_url(BUCKET, path),
            "path":      path,
        })
