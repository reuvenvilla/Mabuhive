"""
api/quest_image.py

Quest image upload, end-to-end in Supabase Storage.

    POST /api/quest-image  (multipart, field name: "image")

Files land at `quest_images/<uploader_uid>/<ts>.<ext>` so multiple
uploads don't collide. RLS on storage.objects requires the first folder
segment to match the uploader's auth.uid().

The endpoint returns the public URL — clients include it in the
`img_url` field when POSTing to /api/quests or PATCHing via the edit
pencil.
"""
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.auth import require_user
from api import supabase_client as sb

BUCKET = "quest_images"

ALLOWED_TYPES = {
    "image/png":  ".png",
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/gif":  ".gif",
    "image/webp": ".webp",
}

MAX_BYTES = 5 * 1024 * 1024


@method_decorator(csrf_exempt, name="dispatch")
class QuestImageUploadHandler(View):
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        user, err = require_user(request)
        if err:
            return err

        upload = request.FILES.get("image")
        if upload is None:
            return json_error("missing form field: image", status=400)

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
                    f"quest_images bucket missing or unwritable: {msg}. "
                    "See SUPABASE_SETUP.md section 8.",
                    status=502,
                )
            return json_error(msg, status=502)

        return JsonResponse({
            "img_url": sb.storage_public_url(BUCKET, path),
            "path":    path,
        })
