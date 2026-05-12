"""
api/config.py

Public configuration endpoint. Exposes the values the frontend needs to
initialise the Supabase client (project URL + anon key). These values are
public by design — Supabase's row-level security policies are what actually
protect data, not key secrecy. The JWT secret stays on the server.

    GET /api/config  ->  { "supabase_url": "...", "supabase_anon_key": "..." }
"""
import os

from django.http import JsonResponse
from django.views import View


class ConfigHandler(View):
    http_method_names = ["get"]

    def get(self, request) -> JsonResponse:
        return JsonResponse({
            "supabase_url":      os.environ.get("SUPABASE_URL", ""),
            "supabase_anon_key": os.environ.get("SUPABASE_ANON_KEY", ""),
        })
