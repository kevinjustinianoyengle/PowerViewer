"""Callbacks for the report-only **Break to zero** tool (Trends viewer).

Deliberately isolated from the viewer callbacks: this is report plumbing (a home
for future statistical/report options) and not part of the interactive analysis.
It writes a ``break_value`` onto the chosen series in ``multi-store``; the actual
re-shaping maths lives in :mod:`powerviewer.graphs.report` and is applied by
``series_figure.build``.
"""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate


def _find(series, sid):
    for s in series:
        if s["id"] == sid:
            return s
    return None


def register(app: Dash) -> None:

    # Offer the current Trends lines to break.
    @app.callback(
        Output("break-line", "options"),
        Output("break-line", "value"),
        Input("multi-store", "data"),
        State("break-line", "value"),
    )
    def line_options(store, current):
        series = (store or {}).get("series") or []
        opts = [{"label": s.get("name") or s["id"], "value": s["id"]}
                for s in series]
        ids = [s["id"] for s in series]
        value = current if current in ids else (ids[0] if ids else None)
        return opts, value

    # Apply a break (at a time) to the chosen line.
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Output("break-status", "children", allow_duplicate=True),
        Input("break-apply", "n_clicks"),
        State("break-line", "value"),
        State("break-time", "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def apply_break(_n, sid, when, store):
        if not sid or not when or not str(when).strip():
            raise PreventUpdate
        store = dict(store or {})
        series = [dict(s) for s in (store.get("series") or [])]
        target = _find(series, sid)
        if target is None:
            raise PreventUpdate
        target["break_time"] = str(when).strip()
        store["series"] = series
        return store, f"Break applied to '{target.get('name') or sid}' at "\
                      f"{str(when).strip()}."

    # Clear every break on the graph.
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Output("break-status", "children", allow_duplicate=True),
        Input("break-clear", "n_clicks"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def clear_break(_n, store):
        if not _n:
            raise PreventUpdate
        store = dict(store or {})
        series = []
        for s in (store.get("series") or []):
            s = dict(s)
            s.pop("break_time", None)
            series.append(s)
        store["series"] = series
        return store, "Breaks cleared."
