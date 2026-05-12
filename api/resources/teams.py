"""
api/resources/teams.py

Team = subgroup inside a hive, created by hive admins. Used as a visibility /
audience target on quests.

Endpoints:
    POST   /api/teams           create a team
    GET    /api/teams           list all teams
    GET    /api/teams/<id>      read one team
    PUT    /api/teams/<id>      update a team

Note: this template doesn't yet enforce that `hive_id` references a real hive
or that the requester is an admin of that hive. Add those checks in the
handler (or via RLS once you're on Supabase) before going to production.
"""
from .base import ResourceCollectionHandler, ResourceItemHandler

COLLECTION = "teams"

ALLOWED_FIELDS = [
    "hive_id",
    "name",
    "description",
    "created_by",
]

# A team must belong to a hive and must have a name.
REQUIRED_FIELDS = ["hive_id", "name"]


class TeamsCollection(ResourceCollectionHandler):
    collection = COLLECTION
    required_fields = REQUIRED_FIELDS
    allowed_fields = ALLOWED_FIELDS


class TeamsItem(ResourceItemHandler):
    collection = COLLECTION
    allowed_fields = ALLOWED_FIELDS
