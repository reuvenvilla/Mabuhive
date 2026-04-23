"""
api/__init__.py

Shared helpers for the CRUD endpoints. Every handler under /api takes a
`?path=...` query string referring to a location under <project_root>/mnt/.

This module centralises:
  * MNT_ROOT      — the on-disk root all paths resolve under
  * resolve_path  — turn a user-supplied ?path= into a safe absolute path
                    (rejects path traversal, returns the realpath)
  * json_error    — small helper for consistent error responses
"""
import os
from pathlib import Path

from django.http import JsonResponse

# <project_root>/mnt
MNT_ROOT = str(Path(__file__).resolve().parent.parent / "mnt")


def resolve_path(rel_path: str) -> str:
    """
    Resolve a user-supplied path under MNT_ROOT.

    Returns the absolute realpath. Raises ValueError if:
      * the path is empty
      * the path escapes MNT_ROOT (traversal)
    """
    if not rel_path:
        raise ValueError("missing required ?path= query parameter")

    mnt_root = os.path.realpath(MNT_ROOT)
    # strip leading slashes so "/foo/bar" and "foo/bar" behave the same
    rel = rel_path.lstrip("/\\")
    full = os.path.realpath(os.path.join(mnt_root, rel))

    if full != mnt_root and not full.startswith(mnt_root + os.sep):
        raise ValueError("path traversal blocked")

    return full


def json_error(message: str, status: int = 400) -> JsonResponse:
    """Consistent error envelope: {\"error\": \"...\"} with given HTTP status."""
    return JsonResponse({"error": message}, status=status)
