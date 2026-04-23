"""
api/update.py

Route: PUT /api/update?path=<relative/path/under/mnt>
Body : raw bytes  -> overwrites <project_root>/mnt/<path>

The file MUST already exist (use /api/create for new files). 404 if missing,
400 on bad/missing path.
"""
import os

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import resolve_path, json_error


@method_decorator(csrf_exempt, name="dispatch")
class UpdateHandler(View):
    http_method_names = ["put"]

    def put(self, request) -> JsonResponse:
        rel = request.GET.get("path", "")
        try:
            full_path = resolve_path(rel)
        except ValueError as e:
            return json_error(str(e), status=400)

        if not os.path.isfile(full_path):
            return json_error(f"file not found: {rel}", status=404)

        with open(full_path, "wb") as f:
            f.write(request.body)

        return JsonResponse({"updated": rel, "bytes": len(request.body)})
