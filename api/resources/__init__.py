"""
api/resources/

Resource-CRUD handlers. Each module defines a *Collection (list/create) and
*Item (read/update) handler for one collection.

To add a new resource:
  1. Create api/resources/<name>.py following the pattern in hives.py.
  2. Add two `path()` entries in server/router.py.

No other changes needed — storage is resolved via api.storage.get_storage().
"""
