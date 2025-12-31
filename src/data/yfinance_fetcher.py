from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from .market_time import NY_TZ, MarketSession

log = logging.getLogger(__name__)


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Expected DatetimeIndex from yfinance")
    if df.index.tz is None:
        # Guard: localize as UTC if tz missing
        df.index = df.index.tz_localize("UTC")
    return df


def fetch_intraday_30m(ticker: str, start: Optional[datetime] = None) -> pd.DataFrame:
    """Fetch 30-minute OHLC for a ticker from Yahoo Finance via yfinance.

    Yahoo limits intraday data (interval < 1d) to roughly the last 60 days, so
    we fetch a rolling window (default: 7 days) and upsert into Supabase. citeturn0search12
    """
    kwargs = dict(interval="30m", auto_adjust=False, prepost=False, progress=False)
    if start is None:
        df = yf.download(ticker, period="7d", **kwargs)
    else:
        df = yf.download(ticker, start=start, **kwargs)

    df = _ensure_datetime_index(df)
    if df.empty:
        return df

    df = df.rename(columns=str.title)
    keep = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    return df[keep].copy()


def fetch_daily_1d(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch 1-day OHLC for a ticker via yfinance."""
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=False, progress=False)
    df = _ensure_datetime_index(df)
    if df.empty:
        return df
    df = df.rename(columns=str.title)
    keep = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    return df[keep].copy()


def filter_to_regular_session(df: pd.DataFrame) -> pd.DataFrame:
    """Filter a tz-aware OHLC dataframe to NYSE regular session 09:30-16:00 NY time."""
    if df.empty:
        return df
    session = MarketSession()
    idx_ny = df.index.tz_convert(NY_TZ)

    mask = []
    for ts in idx_ny:
        dtny = ts.to_pydatetime()
        if not session.is_weekday(dtny):
            mask.append(False)
            continue
        t = dtny.time()
        mask.append(session.open_time <= t <= session.close_time)

    return df.loc[pd.Index(mask, dtype=bool)].copy()
