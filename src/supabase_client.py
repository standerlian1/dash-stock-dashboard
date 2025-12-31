from __future__ import annotations

from typing import Optional

from supabase import Client, create_client
from supabase.client import ClientOptions


def make_supabase_client(url: str, key: str, schema: str = "public", timeout_seconds: int = 20) -> Client:
    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY). "
            "Set environment variables before starting the app."
        )

    options = ClientOptions(
        schema=schema,
        postgrest_client_timeout=timeout_seconds,
        storage_client_timeout=timeout_seconds,
    )
    return create_client(url, key, options=options)
