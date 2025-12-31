from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from ..config import Settings
from ..data.market_time import NY_TZ
from ..data.supabase_repo import SupabaseRepo
from ..indicators.registry import build_registry

log = logging.getLogger(__name__)


def _parse_indicator_params(indicators, values_by_component_id: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for ind_id, ind in indicators.items():
        params: Dict[str, Any] = {}
        for param in ind.param_schema():
            cid = f"ind__{ind_id}__{param['id']}"
            val = values_by_component_id.get(cid)
            if param.get("type") == "bool":
                params[param["id"]] = bool(val) and (True in val if isinstance(val, list) else bool(val))
            else:
                params[param["id"]] = val
        out[ind_id] = params
    return out


def _build_candlestick(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        fig.update_layout(title=title)
        return fig

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=title,
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Time (New York)",
        yaxis_title="Price",
        template="plotly_dark",
        margin=dict(l=30, r=20, t=40, b=30),
        xaxis=dict(rangeslider=dict(visible=False)),
        paper_bgcolor="#0f0f10",
        plot_bgcolor="#0f0f10",
    )
    return fig


def register_callbacks(settings: Settings, repo: SupabaseRepo) -> None:
    indicators = build_registry()

    # Build dynamic list of Inputs for all indicator params
    indicator_inputs: List[Input] = []
    indicator_state_ids: List[str] = []
    for ind_id, ind in indicators.items():
        for param in ind.param_schema():
            cid = f"ind__{ind_id}__{param['id']}"
            indicator_inputs.append(Input(cid, "value"))
            indicator_state_ids.append(cid)

    @callback(
        Output("candlestick-chart", "figure"),
        Output("last-refresh", "children"),
        Output("timestamp-note", "children"),
        Input("ticker-select", "value"),
        Input("ui-refresh-interval", "n_intervals"),
        Input("candlestick-chart", "relayoutData"),
        *indicator_inputs,
    )
    def update_chart(ticker: str, n: int, relayout: Optional[dict], *indicator_values):
        # Last refresh label
        now = datetime.now(timezone.utc)
        last_refresh = f"Last chart refresh (UTC): {now.replace(microsecond=0).isoformat()}"

        # Determine range (NY time) from relayout
        start_ny: Optional[datetime] = None
        end_ny: Optional[datetime] = None
        if relayout and isinstance(relayout, dict):
            rng0 = relayout.get("xaxis.range[0]")
            rng1 = relayout.get("xaxis.range[1]")
            if rng0 and rng1:
                try:
                    start_ny = pd.to_datetime(rng0).to_pydatetime()
                    end_ny = pd.to_datetime(rng1).to_pydatetime()
                except Exception:
                    start_ny = end_ny = None

        # Default: last 3 months daily
        use_intraday = False
        if start_ny and end_ny and (end_ny - start_ny).days <= 10:
            use_intraday = True

        timestamp_note = "Data timestamps are shown in New York time on the x-axis."

        if use_intraday:
            # Query intraday in UTC window based on requested NY range
            start_utc = start_ny.replace(tzinfo=NY_TZ).astimezone(timezone.utc) if start_ny.tzinfo is None else start_ny.astimezone(timezone.utc)
            end_utc = end_ny.replace(tzinfo=NY_TZ).astimezone(timezone.utc) if end_ny.tzinfo is None else end_ny.astimezone(timezone.utc)

            df = repo.get_intraday_30m(ticker, start_utc=start_utc, end_utc=end_utc)
            if not df.empty:
                # Convert index for display to NY time
                df.index = df.index.tz_convert(NY_TZ)
                # Alignment note
                minutes = sorted({(ts.minute, ts.second) for ts in df.index})
                bad = [m for m in minutes if m[0] not in (0, 30) or m[1] != 0]
                if bad:
                    timestamp_note = (
                        "Retrieved timestamps are not perfectly aligned to 30-minute marks. "
                        f"Observed minute:second values: {bad[:10]} (showing up to 10). "
                        "Chart displays the actual timestamps received."
                    )
            title = f"{ticker} (30-minute candles)"
        else:
            # Daily for last N months (by NY date)
            start_date = (datetime.now(tz=NY_TZ).date() - timedelta(days=int(settings.default_months * 31))).isoformat()
            df = repo.get_daily_1d(ticker, start_date=start_date)
            if not df.empty:
                # Daily x-axis as NY date (no tz)
                df.index = pd.to_datetime(df.index).tz_localize(NY_TZ)
            title = f"{ticker} (Daily candles)"

        fig = _build_candlestick(df, title=title)

        # Apply indicator traces (computed over whatever resolution we're showing)
        values_by_id = {cid: val for cid, val in zip(indicator_state_ids, indicator_values)}
        ind_params = _parse_indicator_params(indicators, values_by_id)

        # For indicators, use a UTC index internally
        df_for_ind = df.copy()
        if not df_for_ind.empty:
            if df_for_ind.index.tz is None:
                df_for_ind.index = df_for_ind.index.tz_localize(NY_TZ)
            df_for_ind.index = df_for_ind.index.tz_convert(timezone.utc)

        for ind_id, ind in indicators.items():
            try:
                traces = ind.compute_traces(df_for_ind, ind_params.get(ind_id, {}))
                for tr in traces:
                    fig.add_trace(tr)
            except Exception:
                log.exception("Indicator compute failed: %s", ind_id)

        return fig, last_refresh, timestamp_note

    @callback(
        Output("last-ingestion", "children"),
        Input("ui-refresh-interval", "n_intervals"),
    )
    def update_ingestion_status(n: int):
        status = repo.get_ingestion_status()
        if status.last_success_utc:
            return f"Last successful ingestion (UTC): {status.last_success_utc.replace(microsecond=0).isoformat()}"
        if status.last_error:
            return f"Last ingestion error: {status.last_error}"
        return "Last successful ingestion: (none yet)"
