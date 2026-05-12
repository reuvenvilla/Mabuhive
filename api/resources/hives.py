"""
api/resources/hives.py

Hive = top-level group (groupchat-style container). Per the product spec, hives
are intentionally NOT owned by a single user. `created_by` is recorded for
audit only and is optional.

Endpoints:
    POST   /api/hives           create a hive
    GET    /api/hives           list all hives
    GET    /api/hives/<id>      read one hive
    PUT    /api/hives/<id>      update a hive
"""
from .base import ResourceCollectionHandler, ResourceItemHandler

COLLECTION = "hives"

# Fields accepted from the client on create/update. Anything else in the
# request body is silently dropped.
ALLOWED_FIELDS = [
    "name",
    "description",
    "icon_url",
    "created_by",   # uuid of the user who created the hive; audit-only
]

REQUIRED_FIELDS = ["name"]


class HivesCollection(ResourceCollectionHandler):
    collection = COLLECTION
    required_fields = REQUIRED_FIELDS
    allowed_fields = ALLOWED_FIELDS


class HivesItem(ResourceItemHandler):
    collection = COLLECTION
    allowed_fields = ALLOWED_FIELDS
