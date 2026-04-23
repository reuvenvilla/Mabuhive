"""
api/delete.py

Route: DELETE /api/delete?path=<relative/path/under/mnt>

Removes a file, OR an empty directory. Refuses to recursively wipe non-empty
directories — caller must pass `&recursive=true` to do that, surfacing intent.

400 on bad/missing path, 404 on not-found, 409 if directory is non-empty
without recursive=true.
"""
import os
import shutil

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import MNT_ROOT, resolve_path, json_error


@method_decorator(csrf_exempt, name="dispatch")
class DeleteHandler(View):
    http_method_names = ["delete"]

    def delete(self, request) -> JsonResponse:
        rel = request.GET.get("path", "")
        try:
            full_path = resolve_path(rel)
        except ValueError as e:
            return json_error(str(e), status=400)

        # never let a caller wipe /mnt itself
        if full_path == os.path.realpath(MNT_ROOT):
            return json_error("refusing to delete /mnt root", status=400)

        if not os.path.exists(full_path):
            return json_error(f"not found: {rel}", status=404)

        recursive = request.GET.get("recursive", "").lower() in ("1", "true", "yes")

        if os.path.isdir(full_path):
            if os.listdir(full_path) and not recursive:
                return json_error(
                    f"directory not empty (pass recursive=true to force): {rel}",
                    status=409,
                )
            shutil.rmtree(full_path) if recursive else os.rmdir(full_path)
        else:
            os.remove(full_path)

        return JsonResponse({"deleted": rel})
