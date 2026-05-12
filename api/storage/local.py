"""
api/storage/local.py

LocalFileStorage — stores each collection as a single JSON file under a data
directory (default: <project_root>/mnt/data/). Writes are atomic (write to
temp file + os.replace) and guarded by a per-collection lock so concurrent
requests in the same process can't corrupt the file.

File layout:
    mnt/data/hives.json   -> {"records": {"<id>": {...}, ...}}
    mnt/data/users.json
    mnt/data/teams.json

This is the dev-mode backend. Swap to Supabase by setting STORAGE_BACKEND=supabase
in the environment — no handler changes required.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from .base import StorageBackend


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalFileStorage(StorageBackend):
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # One lock per collection; created lazily on first access.
        self._locks: dict[str, Lock] = {}
        self._locks_guard = Lock()

    # ── Internals ────────────────────────────────────────────────────────────

    def _file_for(self, collection: str) -> Path:
        return self.data_dir / f"{collection}.json"

    def _lock_for(self, collection: str) -> Lock:
        # Double-checked locking so we don't take the guard on every call.
        if collection not in self._locks:
            with self._locks_guard:
                if collection not in self._locks:
                    self._locks[collection] = Lock()
        return self._locks[collection]

    def _load(self, collection: str) -> dict:
        path = self._file_for(collection)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("records", {})

    def _save(self, collection: str, records: dict) -> None:
        path = self._file_for(collection)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"records": records}, f, indent=2, sort_keys=True)
        os.replace(tmp, path)  # atomic on POSIX

    # ── Public API ───────────────────────────────────────────────────────────

    def list(self, collection: str) -> list[dict]:
        with self._lock_for(collection):
            return list(self._load(collection).values())

    def get(self, collection: str, id: str) -> Optional[dict]:
        with self._lock_for(collection):
            return self._load(collection).get(id)

    def create(self, collection: str, data: dict) -> dict:
        with self._lock_for(collection):
            records = self._load(collection)
            new_id = str(data.get("id") or uuid.uuid4())
            now = _now_iso()
            record = {
                **data,
                "id": new_id,
                "created_at": data.get("created_at") or now,
                "updated_at": now,
            }
            records[new_id] = record
            self._save(collection, records)
            return record

    def update(self, collection: str, id: str, data: dict) -> Optional[dict]:
        with self._lock_for(collection):
            records = self._load(collection)
            if id not in records:
                return None
            # Don't let updates change immutable fields.
            data = {k: v for k, v in data.items() if k not in ("id", "created_at")}
            records[id] = {**records[id], **data, "id": id, "updated_at": _now_iso()}
            self._save(collection, records)
            return records[id]

    def delete(self, collection: str, id: str) -> bool:
        with self._lock_for(collection):
            records = self._load(collection)
            if id not in records:
                return False
            del records[id]
            self._save(collection, records)
            return True
