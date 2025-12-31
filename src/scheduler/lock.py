from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from supabase import Client

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LockResult:
    acquired: bool
    lease_expires_at: Optional[datetime]


class DistributedLock:
    """Supabase-backed distributed lock using Postgres functions (atomic).

    Requires SQL functions created in README:
      - acquire_ingest_lock(lock_name text, owner_id text, lease_seconds int) returns boolean
      - heartbeat_ingest_lock(lock_name text, owner_id text, lease_seconds int) returns boolean
      - release_ingest_lock(lock_name text, owner_id text) returns boolean
    """

    def __init__(self, client: Client, lock_name: str, owner_id: str, lease_seconds: int):
        self.client = client
        self.lock_name = lock_name
        self.owner_id = owner_id
        self.lease_seconds = lease_seconds

    def acquire(self) -> bool:
        resp = self.client.rpc(
            "acquire_ingest_lock",
            {"p_lock_name": self.lock_name, "p_owner_id": self.owner_id, "p_lease_seconds": self.lease_seconds},
        ).execute()
        return bool(getattr(resp, "data", False))

    def heartbeat(self) -> bool:
        resp = self.client.rpc(
            "heartbeat_ingest_lock",
            {"p_lock_name": self.lock_name, "p_owner_id": self.owner_id, "p_lease_seconds": self.lease_seconds},
        ).execute()
        return bool(getattr(resp, "data", False))

    def release(self) -> bool:
        resp = self.client.rpc(
            "release_ingest_lock",
            {"p_lock_name": self.lock_name, "p_owner_id": self.owner_id},
        ).execute()
        return bool(getattr(resp, "data", False))
