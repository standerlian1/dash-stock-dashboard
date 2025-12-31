from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from supabase import Client

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionStatus:
    last_success_utc: Optional[datetime]
    last_error: Optional[str]


class SupabaseRepo:
    def __init__(self, client: Client):
        self.client = client

    # ---------- Write ----------
    def upsert_intraday_30m(self, ticker: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        rows = []
        for ts, r in df.iterrows():
            ts_utc = ts.tz_convert("UTC").to_pydatetime()
            ts_ny = ts.tz_convert("America/New_York").to_pydatetime()
            rows.append(
                {
                    "ticker": ticker,
                    "ts_utc": ts_utc.isoformat(),
                    "ny_date": ts_ny.date().isoformat(),
                    "ny_time": ts_ny.time().replace(microsecond=0).isoformat(timespec="seconds"),
                    "open": float(r["Open"]),
                    "high": float(r["High"]),
                    "low": float(r["Low"]),
                    "close": float(r["Close"]),
                }
            )

        resp = (
            self.client.table("price_bars_30m")
            .upsert(rows, on_conflict="ticker,ts_utc")
            .execute()
        )
        # supabase-py response has data list; fallback to len(rows) if no data returned
        return len(resp.data) if getattr(resp, "data", None) is not None else len(rows)

    def upsert_daily_1d(self, ticker: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        rows = []
        for ts, r in df.iterrows():
            # Daily index is typically midnight; treat as NY date
            ts_ny = ts.tz_convert("America/New_York").to_pydatetime()
            rows.append(
                {
                    "ticker": ticker,
                    "ny_date": ts_ny.date().isoformat(),
                    "open": float(r["Open"]),
                    "high": float(r["High"]),
                    "low": float(r["Low"]),
                    "close": float(r["Close"]),
                }
            )

        resp = (
            self.client.table("price_bars_1d")
            .upsert(rows, on_conflict="ticker,ny_date")
            .execute()
        )
        return len(resp.data) if getattr(resp, "data", None) is not None else len(rows)

    def set_ingestion_status(self, last_success_utc: Optional[datetime], last_error: Optional[str]) -> None:
        payload = {
            "key": "last_ingestion",
            "last_success_utc": last_success_utc.isoformat() if last_success_utc else None,
            "last_error": last_error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.table("app_state").upsert(payload, on_conflict="key").execute()

    # ---------- Read ----------
    def get_ingestion_status(self) -> IngestionStatus:
        resp = self.client.table("app_state").select("*").eq("key", "last_ingestion").limit(1).execute()
        if not getattr(resp, "data", None):
            return IngestionStatus(last_success_utc=None, last_error=None)
        row = resp.data[0]
        last_success = row.get("last_success_utc")
        return IngestionStatus(
            last_success_utc=datetime.fromisoformat(last_success) if last_success else None,
            last_error=row.get("last_error"),
        )

    def get_intraday_30m(self, ticker: str, start_utc: datetime, end_utc: Optional[datetime] = None) -> pd.DataFrame:
        q = (
            self.client.table("price_bars_30m")
            .select("ts_utc,open,high,low,close,ny_date,ny_time")
            .eq("ticker", ticker)
            .gte("ts_utc", start_utc.isoformat())
        )
        if end_utc:
            q = q.lte("ts_utc", end_utc.isoformat())
        resp = q.order("ts_utc", desc=False).execute()
        data = getattr(resp, "data", None) or []
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
        df = df.set_index("ts_utc").sort_index()
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
        return df[["Open", "High", "Low", "Close", "ny_date", "ny_time"]]

    def get_daily_1d(self, ticker: str, start_date: str) -> pd.DataFrame:
        resp = (
            self.client.table("price_bars_1d")
            .select("ny_date,open,high,low,close")
            .eq("ticker", ticker)
            .gte("ny_date", start_date)
            .order("ny_date", desc=False)
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["ny_date"] = pd.to_datetime(df["ny_date"])
        df = df.set_index("ny_date").sort_index()
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
        return df[["Open", "High", "Low", "Close"]]

    def get_latest_intraday_ts(self, ticker: str) -> Optional[datetime]:
        resp = (
            self.client.table("price_bars_30m")
            .select("ts_utc")
            .eq("ticker", ticker)
            .order("ts_utc", desc=True)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            return None
        return datetime.fromisoformat(data[0]["ts_utc"].replace("Z", "+00:00"))
