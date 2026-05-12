"""
api/storage/base.py

Abstract storage interface. Any backend (local files, Supabase, Postgres, etc.)
implements this contract; handlers depend only on this ABC so the backend can
be swapped without touching the API layer.

A "collection" is a logical bucket of records (e.g. "hives", "users", "teams").
In the local backend it maps to a JSON file. In the Supabase backend it maps
to a Postgres table of the same name.

Records are plain dicts. Every record carries at least: id, created_at,
updated_at. The backend is responsible for assigning these on create.
"""
from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Contract every storage backend must implement."""

    @abstractmethod
    def list(self, collection: str) -> list[dict]:
        """Return every record in the collection (unordered)."""

    @abstractmethod
    def get(self, collection: str, id: str) -> Optional[dict]:
        """Return the record with this id, or None if not found."""

    @abstractmethod
    def create(self, collection: str, data: dict) -> dict:
        """
        Insert a new record. The backend assigns `id`, `created_at`,
        `updated_at` if not already present. Returns the stored record.
        """

    @abstractmethod
    def update(self, collection: str, id: str, data: dict) -> Optional[dict]:
        """
        Merge `data` into the existing record. Returns the updated record,
        or None if no record with this id exists.
        """

    @abstractmethod
    def delete(self, collection: str, id: str) -> bool:
        """Delete the record. Returns True if a row was deleted, else False."""
