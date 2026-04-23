"""
api/create.py

Route: POST /api/create?path=<relative/path/under/mnt>
Body : raw bytes  -> written to <project_root>/mnt/<path>

Creates parent directories as needed. Refuses to overwrite an existing file
(use /api/update for that). 409 on conflict, 400 on bad/missing path.
"""
import os

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import resolve_path, json_error


@method_decorator(csrf_exempt, name="dispatch")
class CreateHandler(View):
    http_method_names = ["post"]

    def post(self, request) -> JsonResponse:
        try:
            full_path = resolve_path(request.GET.get("path", ""))
        except ValueError as e:
            return json_error(str(e), status=400)

        if os.path.exists(full_path):
            return json_error(f"already exists: {request.GET.get('path')}", status=409)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(request.body)

        return JsonResponse(
            {"created": request.GET.get("path"), "bytes": len(request.body)},
            status=201,
        )
