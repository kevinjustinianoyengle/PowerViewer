"""Shared callbacks for marks: add, list (with per-item + clear-all delete).

Marks are stored per viewer (``{"dispersion": [...], "trend": [...],
"multi_trend": [...]}``) so each graph keeps its own marks.
"""

from __future__ import annotations

import pandas as pd
from dash import ALL, Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from ..config import THEME
from ..ui import theme as T

_VIEW_TO_KEY = {"dispersion": "dispersion", "trend": "trend",
                "multi_trend": "multi_trend"}


def _fmt(v) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def _parse_pos(raw, allow_datetime: bool = True):
    """Parse a mark position: a number, or (for time axes) a datetime string.

    Returns a float, an ISO datetime string, or ``None`` if it can't be parsed.
    """
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        pass
    if allow_datetime:
        ts = pd.to_datetime(raw, dayfirst=True, errors="coerce")
        if pd.notna(ts):
            return ts.isoformat()
    return None


def _describe(mark) -> str:
    """Readable pill text, e.g. ``H: nominal = 100`` or ``P: peak = (3, 5)``."""
    kind = mark.get("kind")
    label = mark.get("label")
    if kind == "h":
        return f"H: {label or 'y'} = {_fmt(mark['value'])}"
    if kind == "v":
        return f"V: {label or 'x'} = {_fmt(mark['value'])}"
    return f"P: {label or 'point'} = ({_fmt(mark['x'])}, {_fmt(mark['y'])})"


def register(app: Dash) -> None:

    # Only show the y input when adding a point mark.
    @app.callback(
        Output("mark-y", "style"),
        Input("mark-kind", "value"),
        State("mark-y", "style"),
    )
    def toggle_y(kind, style):
        style = dict(style or {})
        style["display"] = "inline-block" if kind == "point" else "none"
        return style

    # --- Add a mark to the active viewer ----------------------------------- #
    @app.callback(
        Output("marks-store", "data", allow_duplicate=True),
        Input("add-mark", "n_clicks"),
        State("mark-kind", "value"),
        State("mark-x", "value"),
        State("mark-y", "value"),
        State("mark-label", "value"),
        State("active-view", "data"),
        State("marks-store", "data"),
        prevent_initial_call=True,
    )
    def add_mark(_n, kind, x_val, y_val, label, active, marks):
        marks = marks or {"dispersion": [], "trend": [], "multi_trend": []}
        key = _VIEW_TO_KEY.get(active)
        if key is None:
            raise PreventUpdate
        if kind == "h":
            # Horizontal line sits at a Y value (numeric).
            value = _parse_pos(x_val, allow_datetime=False)
            if value is None:
                raise PreventUpdate
            mark = {"kind": "h", "value": value, "label": label or ""}
        elif kind == "v":
            # Vertical line sits at an X value: number or datetime (time axis).
            value = _parse_pos(x_val, allow_datetime=True)
            if value is None:
                raise PreventUpdate
            mark = {"kind": "v", "value": value, "label": label or ""}
        elif kind == "point":
            x_pos = _parse_pos(x_val, allow_datetime=True)
            y_pos = _parse_pos(y_val, allow_datetime=False)
            if x_pos is None or y_pos is None:
                raise PreventUpdate
            mark = {"kind": "point", "x": x_pos, "y": y_pos, "label": label or ""}
        else:
            raise PreventUpdate
        return {**marks, key: list(marks.get(key, [])) + [mark]}

    # --- Clear all marks on the active viewer ------------------------------ #
    @app.callback(
        Output("marks-store", "data", allow_duplicate=True),
        Input("clear-marks", "n_clicks"),
        State("active-view", "data"),
        State("marks-store", "data"),
        prevent_initial_call=True,
    )
    def clear_marks(_n, active, marks):
        marks = marks or {"dispersion": [], "trend": [], "multi_trend": []}
        key = _VIEW_TO_KEY.get(active)
        if key is None:
            raise PreventUpdate
        return {**marks, key: []}

    # --- Delete a single mark ---------------------------------------------- #
    @app.callback(
        Output("marks-store", "data", allow_duplicate=True),
        Input({"type": "mark-del", "index": ALL}, "n_clicks"),
        State("active-view", "data"),
        State("marks-store", "data"),
        prevent_initial_call=True,
    )
    def delete_mark(_clicks, active, marks):
        trig = ctx.triggered_id
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate
        key = _VIEW_TO_KEY.get(active)
        if key is None:
            raise PreventUpdate
        idx = trig["index"]
        current = list((marks or {}).get(key, []))
        if 0 <= idx < len(current):
            current.pop(idx)
        return {**(marks or {}), key: current}

    # --- Render the list of marks for the active viewer -------------------- #
    @app.callback(
        Output("marks-list", "children"),
        Input("marks-store", "data"),
        Input("active-view", "data"),
    )
    def render_marks(marks, active):
        key = _VIEW_TO_KEY.get(active)
        items = (marks or {}).get(key, []) if key else []
        if not items:
            return html.Span("No marks yet.",
                             style={"color": THEME["muted"], "fontSize": "12px"})
        chips = []
        for i, mark in enumerate(items):
            chips.append(html.Span([
                html.Span(_describe(mark), style=T.MARK_CHIP_TEXT),
                html.Button("✕", id={"type": "mark-del", "index": i},
                            n_clicks=0, title="Delete", style=T.MARK_DELETE),
            ], style=T.MARK_CHIP))
        return chips
