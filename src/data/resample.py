from __future__ import annotations

import pandas as pd


def ohlc_resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample an OHLC dataframe.

    Expected columns include Open/High/Low/Close (any case). Index must be tz-aware.
    """
    if df.empty:
        return df

    cols = {c.lower(): c for c in df.columns}
    required = ["open", "high", "low", "close"]
    if any(r not in cols for r in required):
        raise ValueError(f"Missing OHLC columns; found {list(df.columns)}")

    o, h, l, c = (cols["open"], cols["high"], cols["low"], cols["close"])
    agg = {o: "first", h: "max", l: "min", c: "last"}
    out = df.resample(rule).agg(agg).dropna()
    return out.rename(columns={o: "Open", h: "High", l: "Low", c: "Close"})
