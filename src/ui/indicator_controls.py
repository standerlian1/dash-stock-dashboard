from __future__ import annotations

from typing import Any, Dict, List, Tuple

from dash import dcc, html

from ..indicators.base import Indicator, IndicatorParam


def default_params_from_schema(schema: List[IndicatorParam]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for p in schema:
        params[p["id"]] = p.get("default")
    return params


def build_indicator_controls(indicators: Dict[str, Indicator]) -> html.Div:
    """Generate a UI block for indicators based on each indicator's schema."""
    blocks: List[html.Div] = []

    for ind_id, ind in indicators.items():
        schema = ind.param_schema()
        controls: List[Any] = []
        for param in schema:
            pid = f"ind__{ind_id}__{param['id']}"
            label = html.Div(param.get("label", param["id"]), style={"marginBottom": "4px"})

            ptype = param.get("type")
            if ptype == "bool":
                control = dcc.Checklist(
                    id=pid,
                    options=[{"label": "", "value": True}],
                    value=[True] if param.get("default") else [],
                    style={"marginBottom": "8px"},
                )
            elif ptype in ("int", "float"):
                control = dcc.Input(
                    id=pid,
                    type="number",
                    value=param.get("default"),
                    min=param.get("min"),
                    max=param.get("max"),
                    step=param.get("step"),
                    style={"width": "100%", "marginBottom": "8px"},
                )
            elif ptype == "select":
                control = dcc.Dropdown(
                    id=pid,
                    options=param.get("options") or [],
                    value=param.get("default"),
                    clearable=False,
                    style={"marginBottom": "8px"},
                )
            else:
                # Fallback to text input
                control = dcc.Input(id=pid, type="text", value=param.get("default"), style={"width": "100%"})

            controls.append(html.Div([label, control]))

        blocks.append(
            html.Div(
                [
                    html.Div(ind.name, style={"fontWeight": 600, "marginBottom": "6px"}),
                    *controls,
                ],
                style={
                    "padding": "10px",
                    "border": "1px solid #2a2a2a",
                    "borderRadius": "10px",
                    "marginBottom": "10px",
                    "background": "#121212",
                },
            )
        )

    return html.Div(blocks)
