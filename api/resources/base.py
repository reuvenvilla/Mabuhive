"""
api/resources/base.py

Generic CRUD handlers parameterised by collection name + allowed/required
fields. A resource module (hives.py, users.py, teams.py) just subclasses
these and sets a few class attributes — no boilerplate per endpoint.

URL conventions:
    POST   /api/<collection>          create
    GET    /api/<collection>          list
    GET    /api/<collection>/<id>     read one
    PUT    /api/<collection>/<id>     update

Routing maps the first two to ResourceCollectionHandler, the second two to
ResourceItemHandler.
"""
import json
from typing import ClassVar

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from api import json_error
from api.storage import get_storage


def _parse_json_body(request) -> tuple[dict | None, JsonResponse | None]:
    """Decode the JSON body. Returns (data, None) on success, (None, error_response) otherwise."""
    if not request.body:
        return {}, None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        return None, json_error(f"invalid JSON body: {e}", status=400)
    if not isinstance(data, dict):
        return None, json_error("body must be a JSON object", status=400)
    return data, None


@method_decorator(csrf_exempt, name="dispatch")
class ResourceCollectionHandler(View):
    """
    Handles list + create for a collection.

    Subclass attributes:
        collection      — name of the collection in storage (e.g. "hives")
        required_fields — keys that must be present on create
        allowed_fields  — keys accepted on create (others silently dropped)
    """
    collection: ClassVar[str] = ""
    required_fields: ClassVar[list[str]] = []
    allowed_fields: ClassVar[list[str]] = []

    http_method_names = ["get", "post"]

    def get(self, request) -> JsonResponse:
        items = get_storage().list(self.collection)
        return JsonResponse({"items": items, "count": len(items)})

    def post(self, request) -> JsonResponse:
        data, err = _parse_json_body(request)
        if err:
            return err

        missing = [f for f in self.required_fields if f not in data or data[f] in (None, "")]
        if missing:
            return json_error(
                f"missing required field(s): {', '.join(missing)}",
                status=400,
            )

        clean = {k: v for k, v in data.items() if k in self.allowed_fields}
        record = get_storage().create(self.collection, clean)
        return JsonResponse(record, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ResourceItemHandler(View):
    """
    Handles read + update for a single item.

    Subclass attributes:
        collection     — name of the collection in storage
        allowed_fields — keys accepted on update (others silently dropped)
    """
    collection: ClassVar[str] = ""
    allowed_fields: ClassVar[list[str]] = []

    http_method_names = ["get", "put"]

    def _not_found(self, id: str) -> JsonResponse:
        # Trim trailing "s" for a slightly nicer error label.
        label = self.collection[:-1] if self.collection.endswith("s") else self.collection
        return json_error(f"{label} not found: {id}", status=404)

    def get(self, request, id: str) -> JsonResponse:
        record = get_storage().get(self.collection, id)
        if record is None:
            return self._not_found(id)
        return JsonResponse(record)

    def put(self, request, id: str) -> JsonResponse:
        data, err = _parse_json_body(request)
        if err:
            return err

        clean = {k: v for k, v in data.items() if k in self.allowed_fields}
        record = get_storage().update(self.collection, id, clean)
        if record is None:
            return self._not_found(id)
        return JsonResponse(record)
