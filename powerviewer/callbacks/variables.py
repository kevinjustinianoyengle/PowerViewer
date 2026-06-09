"""The right-hand variable panel: rendering and per-viewer click selection.

Selection rules (matching the spec):

* **Dispersion** - exactly one variable; selecting one *blocks* the others
  (they render disabled) until it is deselected.
* **Trend** - first click sets X, second sets Y; only one of each. With both
  set, the remaining variables are blocked until one is freed.
* **Multiple Trend** - first click sets the single X; every further click toggles
  a Y line (with a default orange tone and scale 1.0).
"""

from __future__ import annotations

import uuid

from dash import ALL, Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from ..config import THEME, palette_color
from ..graphs.trend import raw_series as trend_raw_series
from ..ui import theme as T


def _state_for(col, active, disp, trend, multi):
    """Return the visual state of *col* for the active viewer."""
    if active == "dispersion":
        sel = disp.get("col")
        if col == sel:
            return "y"
        return "disabled" if sel else "idle"
    if active == "trend":
        if col == trend.get("x"):
            return "x"
        if col == trend.get("y"):
            return "y"
        both = trend.get("x") and trend.get("y")
        return "disabled" if both else "idle"
    if active == "multi_trend":
        if col == multi.get("x"):
            return "x"
        if any(s.get("source") == col for s in (multi.get("series") or [])):
            return "y"
        return "idle"
    return "idle"


def register(app: Dash) -> None:

    # --- Render the variable buttons (slim) -------------------------------- #
    @app.callback(
        Output("vars-list", "children"),
        Input("columns-store", "data"),
        Input("active-view", "data"),
        Input("disp-store", "data"),
        Input("trend-store", "data"),
        Input("multi-store", "data"),
    )
    def render_vars(columns, active, disp, trend, multi):
        if not columns:
            return html.Span("Load a data file.",
                             style={"color": THEME["muted"], "fontSize": "11px"})
        disp = disp or {}
        trend = trend or {}
        multi = multi or {}
        buttons = []
        for col in columns:
            state = _state_for(col, active, disp, trend, multi)
            buttons.append(html.Button(
                col,
                id={"type": "var-btn", "index": col},
                n_clicks=0,
                disabled=(state == "disabled"),
                title=col,
                style=T.var_button_slim(state),
            ))
        return buttons

    # --- Handle clicks on variable buttons --------------------------------- #
    @app.callback(
        Output("disp-store", "data"),
        Output("trend-store", "data"),
        Output("multi-store", "data"),
        Input({"type": "var-btn", "index": ALL}, "n_clicks"),
        State("active-view", "data"),
        State("disp-store", "data"),
        State("trend-store", "data"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def select(_clicks, active, disp, trend, multi):
        # Ignore the spurious fire when buttons are (re)mounted with n_clicks=0.
        trig = ctx.triggered_id
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate

        col = trig["index"]
        disp = dict(disp or {})
        trend = {**{"x": None, "y": None, "series": []}, **(trend or {})}
        multi = {**{"x": None, "series": []}, **(multi or {})}

        if active == "dispersion":
            disp["col"] = None if disp.get("col") == col else col
            return disp, no_update, no_update

        if active == "trend":
            x, y = trend.get("x"), trend.get("y")
            if col == x:
                trend["x"] = None
            elif col == y:
                trend["y"] = None
                trend["series"] = []
            elif x is None:
                trend["x"] = col
            elif y is None:
                trend["y"] = col
                trend["series"] = [trend_raw_series(col)]
            # both already set & a different col -> blocked (handled in render)
            return no_update, trend, no_update

        if active == "multi_trend":
            series = list(multi.get("series") or [])

            def _uses(s):
                return s.get("source") == col or col in (s.get("sources") or [])

            selected = any(_uses(s) for s in series)
            if col == multi.get("x"):
                multi["x"] = None
            elif multi.get("x") is None and not selected:
                multi["x"] = col
            elif selected:
                # Deselecting a variable removes every curve that uses it
                # (raw, its derivative/integral, and any sum it feeds).
                multi["series"] = [s for s in series if not _uses(s)]
            else:
                n_raw = len([s for s in series if s.get("transform") == "none"])
                series.append({
                    "id": uuid.uuid4().hex[:8], "source": col,
                    "transform": "none", "name": col,
                    "color": palette_color(n_raw), "scale": 1.0,
                    "displace": 0.0})
                multi["series"] = series
            return no_update, no_update, multi

        raise PreventUpdate
