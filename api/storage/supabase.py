"""
api/storage/supabase.py

SupabaseStorage — drop-in replacement for LocalFileStorage. Stubbed out for
now; flip the switch when you're ready by:

    1. pip install supabase
    2. set env vars:
         SUPABASE_URL=https://<project>.supabase.co
         SUPABASE_KEY=<service-role-or-anon-key>
         STORAGE_BACKEND=supabase
    3. uncomment the body of __init__ and each method below.

Schema expectation: each `collection` name maps 1:1 to a Postgres table with
at least `id uuid`, `created_at timestamptz`, `updated_at timestamptz`.
"""
import os
from typing import Optional

from .base import StorageBackend


class SupabaseStorage(StorageBackend):
    def __init__(self):
        # from supabase import create_client
        # url = os.environ["SUPABASE_URL"]
        # key = os.environ["SUPABASE_KEY"]
        # self.client = create_client(url, key)
        raise NotImplementedError(
            "SupabaseStorage is a stub. Install supabase-py, set SUPABASE_URL "
            "and SUPABASE_KEY, then uncomment the method bodies."
        )

    def list(self, collection: str) -> list[dict]:
        # res = self.client.table(collection).select("*").execute()
        # return res.data or []
        raise NotImplementedError

    def get(self, collection: str, id: str) -> Optional[dict]:
        # res = (
        #     self.client.table(collection)
        #     .select("*")
        #     .eq("id", id)
        #     .maybe_single()
        #     .execute()
        # )
        # return res.data
        raise NotImplementedError

    def create(self, collection: str, data: dict) -> dict:
        # Supabase/Postgres assigns id + created_at via column defaults.
        # res = self.client.table(collection).insert(data).execute()
        # return res.data[0]
        raise NotImplementedError

    def update(self, collection: str, id: str, data: dict) -> Optional[dict]:
        # data = {**data, "updated_at": "now()"}  # or trigger-managed
        # res = (
        #     self.client.table(collection)
        #     .update(data)
        #     .eq("id", id)
        #     .execute()
        # )
        # return res.data[0] if res.data else None
        raise NotImplementedError

    def delete(self, collection: str, id: str) -> bool:
        # res = self.client.table(collection).delete().eq("id", id).execute()
        # return bool(res.data)
        raise NotImplementedError
