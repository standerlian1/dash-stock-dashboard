from __future__ import annotations

from typing import Dict, List

from .base import Indicator
from .sma import SMAIndicator
from .ema import EMAIndicator


def build_registry() -> Dict[str, Indicator]:
    indicators: List[Indicator] = [
        SMAIndicator(),
        EMAIndicator(),
    ]
    return {i.id: i for i in indicators}
