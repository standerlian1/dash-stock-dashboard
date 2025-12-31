from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict

import pandas as pd
import plotly.graph_objects as go


ParamType = Literal["int", "float", "bool", "select"]


class IndicatorParam(TypedDict, total=False):
    id: str
    label: str
    type: ParamType
    default: Any
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    options: Optional[List[dict]]  # for select


class Indicator(ABC):
    """Base interface for all indicators.

    Indicators:
      - expose a parameter schema for auto-generated UI
      - compute traces (and/or computed columns) from price dataframe
      - contain NO Dash UI logic
    """

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def param_schema(self) -> List[IndicatorParam]: ...

    @abstractmethod
    def compute_traces(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[go.Scatter]:
        """Return Plotly traces. df index must be tz-aware timestamps (UTC)."""
        ...
