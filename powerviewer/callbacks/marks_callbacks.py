"""Shared callbacks for marks: add, list (with per-item + clear-all delete).

Marks are stored per viewer (``{"dispersion": [...], "trend": [...],
"multi_trend": [...]}``) so each graph keeps its own marks.
"""

from __future__ import annotations

from dash import ALL, Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from ..config import THEME
from ..ui import theme as T

_VIEW_TO_KEY = {"dispersion": "dispersion", "trend": "trend",
                "multi_trend": "multi_trend"}


def _describe(mark) -> str:
    """Readable pill text, e.g. ``H: nominal = 100`` or ``P: peak = (3, 5)``."""
    kind = mark.get("kind")
    label = mark.get("label")
    if kind == "h":
        name = label or "y"
        return f"H: {name} = {mark['value']:g}"
    if kind == "v":
        name = label or "x"
        return f"V: {name} = {mark['value']:g}"
    name = label or "point"
    return f"P: {name} = ({mark['x']:g}, {mark['y']:g})"


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
        if kind in ("h", "v"):
            if x_val is None:
                raise PreventUpdate
            mark = {"kind": kind, "value": float(x_val), "label": label or ""}
        elif kind == "point":
            if x_val is None or y_val is None:
                raise PreventUpdate
            mark = {"kind": "point", "x": float(x_val), "y": float(y_val),
                    "label": label or ""}
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
