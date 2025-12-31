from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Settings:
    # App
    app_title: str = "Stock Dashboard"
    tickers: List[str] = ("TSM", "AAPL", "NVDA", "^GSPC")
    default_ticker: str = "AAPL"

    # Supabase
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    supabase_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    supabase_schema: str = os.environ.get("SUPABASE_SCHEMA", "public")

    # Scheduler / Lock
    instance_id: str = os.environ.get("INSTANCE_ID", "")  # optional override
    lock_name: str = os.environ.get("INGEST_LOCK_NAME", "global_ingestion_lock")
    lease_seconds: int = int(os.environ.get("INGEST_LOCK_LEASE_SECONDS", "120"))
    enable_scheduler: bool = os.environ.get("ENABLE_SCHEDULER", "true").lower() in ("1", "true", "yes", "y")

    # Logging
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

    # Market / Timezone
    market_tz: str = "America/New_York"

    # Chart
    default_months: int = int(os.environ.get("DEFAULT_MONTHS", "3"))


def get_settings() -> Settings:
    return Settings()
