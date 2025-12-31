from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go

from .base import Indicator, IndicatorParam


class EMAIndicator(Indicator):
    @property
    def id(self) -> str:
        return "ema"

    @property
    def name(self) -> str:
        return "Exponential Moving Average"

    def param_schema(self) -> List[IndicatorParam]:
        return [
            {"id": "enabled", "label": "Enable EMA", "type": "bool", "default": False},
            {"id": "span", "label": "Span", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1},
        ]

    def compute_traces(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[go.Scatter]:
        if df.empty or not params.get("enabled", False):
            return []
        span = int(params.get("span", 20))
        ema = df["Close"].astype(float).ewm(span=span, adjust=False).mean()
        return [
            go.Scatter(
                x=df.index,
                y=ema,
                mode="lines",
                name=f"EMA({span})",
            )
        ]
