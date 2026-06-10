"""Bottom chip-bar renderer for the series drawn in a graph.

Each series is shown as a **chip** (colour dot + name, plus an L/R axis badge for
Multiple Trend). Clicking a chip raises a **popover above it** holding that one
series' options — colour, rename, scale, displacement, an axis selector
(Multiple Trend only) and buttons to add a derivative / integral or remove it.

The popover inputs keep the same pattern-matching IDs the old cards used
(``{prefix}-name`` / ``-color`` / ``-scale`` / ``-displace`` / ``-axis`` /
``-add-d`` / ``-add-i`` / ``-del``), so the Trend ("tr") and Multiple Trend
("mt") callbacks keep working unchanged. Every series' inputs are rendered (only
the open chip's popover is *visible*), so the ALL-pattern callbacks still see the
full, in-order series list.
"""

from __future__ import annotations

from typing import List, Optional

from dash import dcc, html

from ..config import ORANGE_PALETTE, THEME
from . import theme as T

COLOR_CHOICES = ORANGE_PALETTE + ["#FF3B30", "#FFD60A", "#E6EDF3", "#58A6FF",
                                  "#3FB950", "#BC8CFF"]

_BADGE = {"none": "raw", "derivative": "d/dx", "integral": "∫"}
_NUM = {"width": "100%", "padding": "6px 8px", "borderRadius": "7px",
        "border": f"1px solid {THEME['border']}", "backgroundColor": THEME["bg"],
        "color": THEME["text"], "fontSize": "12px", "boxSizing": "border-box"}


def swatch_option(c: str) -> dict:
    """A colour-swatch option for a ``dcc.Dropdown`` (swatch + hex label)."""
    return {"label": html.Div([
        html.Span(style={"display": "inline-block", "width": "12px",
                         "height": "12px", "borderRadius": "3px",
                         "backgroundColor": c, "marginRight": "6px",
                         "border": f"1px solid {THEME['border']}"}),
        html.Span(c, style={"fontSize": "11px"})],
        style={"display": "flex", "alignItems": "center"}), "value": c}


def color_options(current: str) -> list:
    """Swatch options, ensuring *current* is selectable even if non-standard."""
    choices = (COLOR_CHOICES if current in COLOR_CHOICES
               else [current] + COLOR_CHOICES)
    return [swatch_option(c) for c in choices]


def field(label: str, control) -> html.Div:
    """A labelled, vertically-stacked field inside a popover menu."""
    return html.Div([
        html.Span(label, style=T.POPOVER_TITLE),
        control,
    ], style=T.POPOVER_FIELD)


def _series_menu(s: dict, prefix: str, allow_axis: bool, allow_transforms: bool):
    """The popover body for a single series (colour / rename / scale / …)."""
    sid = s["id"]
    current = s.get("color") or THEME["accent"]
    kind = s.get("transform", "none")
    is_sum = len(s.get("sources") or []) > 1
    badge = "Σ" if (is_sum and kind == "none") else _BADGE.get(kind, "raw")

    body = [
        html.Div([html.Span(badge, style=T.CHIP_BADGE),
                  html.Span("Series options", style=T.POPOVER_TITLE)],
                 style={"display": "flex", "alignItems": "center", "gap": "8px",
                        "marginBottom": "10px"}),
        field("Colour", dcc.Dropdown(
            id={"type": f"{prefix}-color", "index": sid},
            options=color_options(current), value=current,
            clearable=False, searchable=False,
            style={"color": "#111", "fontSize": "11px"})),
    ]
    if allow_axis:
        body.append(field("Axis", dcc.Dropdown(
            id={"type": f"{prefix}-axis", "index": sid},
            options=[{"label": "Y ◀ left", "value": "left"},
                     {"label": "Y ▶ right", "value": "right"}],
            value=s.get("axis", "left"), clearable=False, searchable=False,
            style={"color": "#111", "fontSize": "11px"})))
    body.append(field("Rename", dcc.Input(
        id={"type": f"{prefix}-name", "index": sid}, type="text",
        value=s.get("name", ""), debounce=True, placeholder="name", style=_NUM)))
    body.append(field("Scale (×)", dcc.Input(
        id={"type": f"{prefix}-scale", "index": sid}, type="number",
        value=s.get("scale", 1.0), step="any", style=_NUM)))
    body.append(field("Displacement (+)", dcc.Input(
        id={"type": f"{prefix}-displace", "index": sid}, type="number",
        value=s.get("displace", 0.0), step="any", style=_NUM)))
    if allow_transforms:
        body.append(html.Div([
            html.Button("+ d/dx", id={"type": f"{prefix}-add-d", "index": sid},
                        n_clicks=0, title="Add derivative", style=T.CHIP_ACTION),
            html.Button("+ ∫", id={"type": f"{prefix}-add-i", "index": sid},
                        n_clicks=0, title="Add integral", style=T.CHIP_ACTION),
        ], style={"display": "flex", "gap": "8px", "marginBottom": "10px"}))
    body.append(html.Button("Remove series",
                            id={"type": f"{prefix}-del", "index": sid},
                            n_clicks=0, style=T.CHIP_REMOVE))
    return body


def series_chip(s: dict, prefix: str, allow_axis: bool,
                allow_transforms: bool, open_id: Optional[str]) -> html.Div:
    sid = s["id"]
    color = s.get("color") or THEME["accent"]
    label = [html.Span(style=T.chip_dot(color)),
             html.Span(s.get("name") or "series", style=T.CHIP_NAME)]
    if allow_axis:
        side = "R" if s.get("axis") == "right" else "L"
        label.append(html.Span(side, style=T.CHIP_AXIS_BADGE))
    is_open = sid == open_id
    return html.Div([
        html.Button(label, id={"type": f"{prefix}-chip", "index": sid},
                    n_clicks=0, style=T.chip(is_open)),
        html.Div(_series_menu(s, prefix, allow_axis, allow_transforms),
                 style=T.chip_popover(is_open)),
    ], style=T.CHIP_WRAP)


def render_series_chips(series: List[dict], prefix: str,
                        allow_axis: bool = False,
                        allow_transforms: bool = True,
                        open_id: Optional[str] = None):
    """Return the chip-bar children for *series* (a hint when empty)."""
    if not series:
        return html.Span("No series yet — pick variables on the right.",
                         style=T.CHIP_HINT)
    return [series_chip(s, prefix, allow_axis, allow_transforms, open_id)
            for s in series]
