"""
api/resources/users.py

User profile records. NOTE: when you migrate to Supabase, the source of truth
for identity should be `auth.users` (Supabase Auth) and this collection should
become a `profiles` table keyed by the auth user's uuid. For now, while we're
on local storage, we own the full record.

Endpoints:
    POST   /api/users           create a user
    GET    /api/users           list all users
    GET    /api/users/<id>      read one user
    PUT    /api/users/<id>      update a user
"""
from .base import ResourceCollectionHandler, ResourceItemHandler

COLLECTION = "users"

ALLOWED_FIELDS = [
    "username",
    "display_name",
    "avatar_url",
    "email",
]

REQUIRED_FIELDS = ["username"]


class UsersCollection(ResourceCollectionHandler):
    collection = COLLECTION
    required_fields = REQUIRED_FIELDS
    allowed_fields = ALLOWED_FIELDS


class UsersItem(ResourceItemHandler):
    collection = COLLECTION
    allowed_fields = ALLOWED_FIELDS
