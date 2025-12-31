from __future__ import annotations

from dash import dcc, html

from ..config import Settings
from ..indicators.registry import build_registry
from .indicator_controls import build_indicator_controls


def build_layout(settings: Settings) -> html.Div:
    indicators = build_registry()

    sidebar = html.Div(
        [
            html.Div(settings.app_title, style={"fontSize": "18px", "fontWeight": 700, "marginBottom": "10px"}),
            html.Div("Tickers", style={"fontSize": "13px", "opacity": 0.8, "marginBottom": "6px"}),
            dcc.RadioItems(
                id="ticker-select",
                options=[{"label": t, "value": t} for t in settings.tickers],
                value=settings.default_ticker,
                inputStyle={"marginRight": "8px"},
                style={"display": "flex", "flexDirection": "column", "gap": "8px"},
            ),
            html.Hr(style={"borderColor": "#2a2a2a"}),
            html.Div("Indicators", style={"fontSize": "13px", "opacity": 0.8, "marginBottom": "6px"}),
            build_indicator_controls(indicators),
        ],
        style={
            "width": "16.5%",  # <= 1/6 (16.66%)
            "minWidth": "190px",
            "maxWidth": "260px",
            "padding": "14px",
            "background": "#0b0b0b",
            "borderRight": "1px solid #1f1f1f",
            "height": "100vh",
            "overflowY": "auto",
        },
    )

    main = html.Div(
        [
            html.Div(
                [
                    html.Div(id="last-ingestion", style={"fontSize": "12px", "opacity": 0.85}),
                    html.Div(id="last-refresh", style={"fontSize": "12px", "opacity": 0.85}),
                    html.Div(id="timestamp-note", style={"fontSize": "12px", "opacity": 0.85}),
                ],
                style={"display": "flex", "gap": "20px", "flexWrap": "wrap", "marginBottom": "10px"},
            ),
            dcc.Graph(
                id="candlestick-chart",
                config={"displayModeBar": True, "scrollZoom": True},
                style={"height": "85vh"},
            ),
            dcc.Interval(id="ui-refresh-interval", interval=60_000, n_intervals=0),
            dcc.Store(id="chart-range-store", data=None),
        ],
        style={"flex": 1, "padding": "14px", "background": "#0f0f10"},
    )

    return html.Div(
        [sidebar, main],
        style={
            "display": "flex",
            "flexDirection": "row",
            "background": "#0f0f10",
            "color": "#eaeaea",
            "fontFamily": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
        },
    )
