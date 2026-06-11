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
# Combined-series operator badges (sum / difference / product / quotient).
_OP_BADGE = {"+": "Σ", "-": "−", "*": "×", "/": "÷"}
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


def field(label: str, control, grow: bool = True) -> html.Div:
    """A labelled, vertically-stacked field; flexes to share a horizontal row."""
    return html.Div([
        html.Span(label, style=T.POPOVER_TITLE),
        control,
    ], style={**T.POPOVER_FIELD, "marginBottom": "0",
              "flex": "1 1 0" if grow else "0 0 auto", "minWidth": "0"})


_ROW = {"display": "flex", "gap": "10px", "alignItems": "flex-end",
        "marginBottom": "12px", "flexWrap": "wrap"}
_POS_OPTS = [{"label": "Top-left", "value": "tl"},
             {"label": "Top-right", "value": "tr"},
             {"label": "Bottom-left", "value": "bl"},
             {"label": "Bottom-right", "value": "br"}]


def _regression_row(s: dict, prefix: str, scatter: bool):
    """Per-curve regression controls (Multiple Trend) — toggle + colour + corner.

    Greyed (and disabled) until the graph is in Scatter mode.
    """
    sid = s["id"]
    fit_color = s.get("fit_color") or s.get("color") or THEME["accent"]
    head = [html.Span("Regression", style=T.POPOVER_TITLE)]
    if not scatter:
        head.append(html.Span("— switch to Scatter (⚙ Display)",
                              style={**T.CHIP_HINT, "marginLeft": "6px"}))
    return html.Div([
        html.Div(head, style={"marginBottom": "6px"}),
        html.Div([
            html.Div(dcc.Checklist(
                id={"type": f"{prefix}-fit", "index": sid},
                options=[{"label": " Line", "value": "on",
                          "disabled": not scatter}],
                value=["on"] if s.get("fit") else []),
                style={"flex": "0 0 auto"}),
            field("Colour", dcc.Dropdown(
                id={"type": f"{prefix}-fit-color", "index": sid},
                options=color_options(fit_color), value=fit_color,
                clearable=False, searchable=False, disabled=not scatter,
                style={"color": "#111", "fontSize": "11px"})),
            field("Box", dcc.Dropdown(
                id={"type": f"{prefix}-fit-pos", "index": sid},
                options=_POS_OPTS, value=s.get("fit_pos", "tl"),
                clearable=False, searchable=False, disabled=not scatter,
                style={"color": "#111", "fontSize": "11px"})),
        ], style={"display": "flex", "gap": "10px", "alignItems": "flex-end"}),
    ], style={"opacity": "1" if scatter else "0.5",
              "borderTop": f"1px solid {THEME['border']}",
              "paddingTop": "10px", "marginBottom": "12px"})


def _series_menu(s: dict, prefix: str, allow_axis: bool, allow_transforms: bool,
                 scatter: bool = False):
    """Popover body for one series, laid out in compact horizontal rows."""
    sid = s["id"]
    current = s.get("color") or THEME["accent"]
    kind = s.get("transform", "none")
    is_sum = len(s.get("sources") or []) > 1
    badge = (_OP_BADGE.get(s.get("op", "+"), "Σ") if (is_sum and kind == "none")
             else _BADGE.get(kind, "raw"))

    body = []
    # Row 1: name (rename) on its own line — no field label.
    body.append(html.Div([
        html.Span(badge, style={**T.CHIP_BADGE, "flex": "0 0 auto"}),
        dcc.Input(id={"type": f"{prefix}-name", "index": sid}, type="text",
                  value=s.get("name", ""), debounce=True, placeholder="name",
                  style={**_NUM, "flex": "1 1 0"}),
    ], style={"display": "flex", "gap": "8px", "alignItems": "center",
              "marginBottom": "12px"}))

    # Row 2: colour + axis (axis only on Multiple Trend).
    row2 = [field("Colour", dcc.Dropdown(
        id={"type": f"{prefix}-color", "index": sid},
        options=color_options(current), value=current,
        clearable=False, searchable=False,
        style={"color": "#111", "fontSize": "11px"}))]
    if allow_axis:
        row2.append(field("Axis", dcc.Dropdown(
            id={"type": f"{prefix}-axis", "index": sid},
            options=[{"label": "Y ◀ left", "value": "left"},
                     {"label": "Y ▶ right", "value": "right"}],
            value=s.get("axis", "left"), clearable=False, searchable=False,
            style={"color": "#111", "fontSize": "11px"})))
    body.append(html.Div(row2, style=_ROW))

    # Row 3: scale + displacement + d/dx + ∫ (one line).
    if allow_transforms:
        body.append(html.Div([
            field("Scale (×)", dcc.Input(
                id={"type": f"{prefix}-scale", "index": sid}, type="number",
                value=s.get("scale", 1.0), step="any", style=_NUM)),
            field("Displace (+)", dcc.Input(
                id={"type": f"{prefix}-displace", "index": sid}, type="number",
                value=s.get("displace", 0.0), step="any", style=_NUM)),
            html.Button("+ d/dx", id={"type": f"{prefix}-add-d", "index": sid},
                        n_clicks=0, title="Add derivative",
                        style={**T.CHIP_ACTION, "flex": "0 0 auto"}),
            html.Button("+ ∫", id={"type": f"{prefix}-add-i", "index": sid},
                        n_clicks=0, title="Add integral",
                        style={**T.CHIP_ACTION, "flex": "0 0 auto"}),
        ], style=_ROW))

    # Row 4: per-curve regression (Multiple Trend only).
    if allow_axis:
        body.append(_regression_row(s, prefix, scatter))

    # Row 5: remove (bottom).
    body.append(html.Button("Remove series",
                            id={"type": f"{prefix}-del", "index": sid},
                            n_clicks=0, style=T.CHIP_REMOVE))
    return body


def series_chip(s: dict, prefix: str, allow_axis: bool,
                allow_transforms: bool, open_id: Optional[str],
                scatter: bool = False) -> html.Div:
    sid = s["id"]
    color = s.get("color") or THEME["accent"]
    label = [html.Span(style=T.chip_dot(color)),
             html.Span(s.get("name") or "series", style=T.CHIP_NAME)]
    if allow_axis:
        side = "R" if s.get("axis") == "right" else "L"
        label.append(html.Span(side, style=T.CHIP_AXIS_BADGE))
        if scatter and s.get("fit"):
            label.append(html.Span("R²", style=T.CHIP_BADGE))
    is_open = sid == open_id
    return html.Div([
        html.Button(label, id={"type": f"{prefix}-chip", "index": sid},
                    n_clicks=0, style=T.chip(is_open)),
        html.Div(_series_menu(s, prefix, allow_axis, allow_transforms, scatter),
                 style=T.chip_popover(is_open, wide=True)),
    ], style=T.CHIP_WRAP)


def render_series_chips(series: List[dict], prefix: str,
                        allow_axis: bool = False,
                        allow_transforms: bool = True,
                        open_id: Optional[str] = None,
                        scatter: bool = False):
    """Return the chip-bar children for *series* (a hint when empty)."""
    if not series:
        return html.Span("No series yet — pick variables on the right.",
                         style=T.CHIP_HINT)
    return [series_chip(s, prefix, allow_axis, allow_transforms, open_id, scatter)
            for s in series]
