from __future__ import annotations

import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

from ..config import Settings
from ..data.market_time import MarketSession, now_ny
from ..data.supabase_repo import SupabaseRepo
from ..data.yfinance_fetcher import fetch_daily_1d, fetch_intraday_30m, filter_to_regular_session
from .lock import DistributedLock

log = logging.getLogger(__name__)


def build_owner_id(settings: Settings) -> str:
    if settings.instance_id:
        return settings.instance_id
    # Render sets RENDER_INSTANCE_ID or similar; fallback to hostname+pid+uuid
    rid = os.environ.get("RENDER_INSTANCE_ID") or os.environ.get("RENDER_SERVICE_ID")
    host = socket.gethostname()
    return f"{rid or host}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class Ingestor:
    def __init__(self, settings: Settings, repo: SupabaseRepo, lock: DistributedLock):
        self.settings = settings
        self.repo = repo
        self.lock = lock
        self.session = MarketSession()

    def ingest_intraday_if_market_open(self) -> None:
        dt_ny = now_ny()
        if not self.session.is_in_session(dt_ny):
            log.info("Skipping intraday ingestion (outside NY session): %s", dt_ny.isoformat())
            return

        self._run_ingestion(intraday=True, daily=False)

    def ingest_daily_after_close(self) -> None:
        dt_ny = now_ny()
        # Run a small buffer after close (weekdays only)
        if not self.session.is_weekday(dt_ny):
            return
        if not self.session.is_after_close(dt_ny):
            return
        # Only between 16:05 and 18:00 NY
        if dt_ny.hour == 16 and dt_ny.minute < 5:
            return
        if dt_ny.hour > 18:
            return

        self._run_ingestion(intraday=False, daily=True)

    def _run_ingestion(self, intraday: bool, daily: bool) -> None:
        acquired = False
        try:
            acquired = self.lock.acquire()
            if not acquired:
                log.info("Another instance holds ingestion lock; skipping.")
                return

            started = datetime.now(timezone.utc)
            total_rows = 0

            for ticker in self.settings.tickers:
                try:
                    if intraday:
                        last_ts = self.repo.get_latest_intraday_ts(ticker)
                        start = None
                        if last_ts:
                            # fetch a small window overlapping the last bar to be safe
                            start = (last_ts - timedelta(days=2))
                        df_30m = fetch_intraday_30m(ticker, start=start)
                        df_30m = filter_to_regular_session(df_30m)
                        rows = self.repo.upsert_intraday_30m(ticker, df_30m)
                        total_rows += rows
                        log.info("Upserted %s intraday rows for %s", rows, ticker)

                    if daily:
                        df_1d = fetch_daily_1d(ticker, period="12mo")
                        rows = self.repo.upsert_daily_1d(ticker, df_1d)
                        total_rows += rows
                        log.info("Upserted %s daily rows for %s", rows, ticker)

                except Exception as e:
                    log.exception("Ingestion error for %s", ticker)
                    self.repo.set_ingestion_status(last_success_utc=None, last_error=f"{ticker}: {e}")
                    # continue other tickers

            finished = datetime.now(timezone.utc)
            self.repo.set_ingestion_status(last_success_utc=finished, last_error=None)
            log.info(
                "Ingestion run complete intraday=%s daily=%s rows=%s duration=%.2fs",
                intraday,
                daily,
                total_rows,
                (finished - started).total_seconds(),
            )
        except Exception as e:
            log.exception("Ingestion run failed")
            self.repo.set_ingestion_status(last_success_utc=None, last_error=str(e))
        finally:
            if acquired:
                try:
                    self.lock.release()
                except Exception:
                    log.exception("Failed to release ingestion lock")
