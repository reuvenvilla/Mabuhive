"""
api/resources/quests.py

// TODO QUEST DESCRIPTION

Endpoints:
    POST   /api/quest           create a quest
    GET    /api/quest           list all quests
    GET    /api/quest/<id>      read one quest
    PUT    /api/quest/<id>      update a quest
"""
from .base import ResourceCollectionHandler, ResourceItemHandler

COLLECTION = "quest"

# Fields accepted from the client on create/update. Anything else in the
# request body is silently dropped.
ALLOWED_FIELDS = [
    "created-by",
    "title",
    "content",
    "image",
    "users_joined",
    "users_completed",
    "visibility",
    "conditions",
]

REQUIRED_FIELDS = ["title"]


class QuestCollection(ResourceCollectionHandler):
    collection = COLLECTION
    required_fields = REQUIRED_FIELDS
    allowed_fields = ALLOWED_FIELDS


class QuestItem(ResourceItemHandler):
    collection = COLLECTION
    allowed_fields = ALLOWED_FIELDS
