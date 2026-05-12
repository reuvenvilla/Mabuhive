"""
api/storage/__init__.py

Storage factory. Handlers call `get_storage()` and don't care which backend
they're talking to. Switch backends via env var:

    STORAGE_BACKEND=local      (default — JSON files under mnt/data/)
    STORAGE_BACKEND=supabase   (requires SUPABASE_URL + SUPABASE_KEY)

The instance is cached for the process lifetime; call `reset_storage()` from
tests when you need a fresh one.
"""
import os
from pathlib import Path
from typing import Optional

from .base import StorageBackend
from .local import LocalFileStorage

_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Return the active storage backend (cached)."""
    global _instance
    if _instance is not None:
        return _instance

    backend = os.environ.get("STORAGE_BACKEND", "local").lower()

    if backend == "local":
        # Default data directory: <project_root>/mnt/data/
        default_dir = Path(__file__).resolve().parent.parent.parent / "mnt" / "data"
        data_dir = os.environ.get("LOCAL_DATA_DIR", str(default_dir))
        _instance = LocalFileStorage(data_dir)

    elif backend == "supabase":
        # Imported lazily so the local backend doesn't require supabase-py.
        from .supabase import SupabaseStorage
        _instance = SupabaseStorage()

    else:
        raise ValueError(
            f"unknown STORAGE_BACKEND: {backend!r} (expected 'local' or 'supabase')"
        )

    return _instance


def reset_storage() -> None:
    """Drop the cached instance. Used by tests."""
    global _instance
    _instance = None


__all__ = ["StorageBackend", "get_storage", "reset_storage"]
