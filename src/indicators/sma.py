from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go

from .base import Indicator, IndicatorParam


class SMAIndicator(Indicator):
    @property
    def id(self) -> str:
        return "sma"

    @property
    def name(self) -> str:
        return "Simple Moving Average"

    def param_schema(self) -> List[IndicatorParam]:
        return [
            {"id": "enabled", "label": "Enable SMA", "type": "bool", "default": False},
            {"id": "window", "label": "Window", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1},
        ]

    def compute_traces(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[go.Scatter]:
        if df.empty or not params.get("enabled", False):
            return []
        window = int(params.get("window", 20))
        close = df["Close"].astype(float)
        sma = close.rolling(window=window).mean()
        return [
            go.Scatter(
                x=df.index,
                y=sma,
                mode="lines",
                name=f"SMA({window})",
            )
        ]
