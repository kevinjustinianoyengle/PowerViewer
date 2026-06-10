"""Callbacks for the Trend viewer (series-list model + axis swap).

Raw + derivative + integral of the single chosen Y can all be shown at once,
each as a series card with editable name / colour / scale / displacement.
"""

from __future__ import annotations

import uuid

from dash import ALL, Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from ..config import palette_color
from ..data import load_dataframe
from ..graphs import trend
from ..ui.cards import render_series_chips

PREFIX = "tr"


def _find(series, sid):
    for s in series:
        if s["id"] == sid:
            return s
    return None


def register(app: Dash) -> None:

    # Swap X / Y (reset overlay series to the new Y's raw curve).
    @app.callback(
        Output("trend-store", "data", allow_duplicate=True),
        Input("trend-swap", "n_clicks"),
        State("trend-store", "data"),
        prevent_initial_call=True,
    )
    def swap(_n, store):
        store = dict(store or {})
        x, y = store.get("x"), store.get("y")
        if not x and not y:
            raise PreventUpdate
        store["x"], store["y"] = y, x
        store["series"] = [trend.raw_series(x)] if x else []
        return store

    # --- Figure ------------------------------------------------------------ #
    @app.callback(
        Output("trend-graph", "figure"),
        Output("trend-axes-label", "children"),
        Input("trend-store", "data"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(store, marks, labels, filename, table):
        store = store or {}
        x_col, y_col = store.get("x"), store.get("y")
        df = load_dataframe(filename, table) if filename else None
        fig = trend.build_figure(
            df, x_col, y_col, series=store.get("series") or [],
            marks=(marks or {}).get("trend"),
            labels=(labels or {}).get("trend"))
        return fig, f"X: {x_col or '—'}   |   Y: {y_col or '—'}"

    # --- Chips (bottom bar; each opens a per-series options popover) -------- #
    @app.callback(
        Output("trend-chips", "children"),
        Input("trend-store", "data"),
        Input("chip-open", "data"),
    )
    def chips(store, open_id):
        return render_series_chips((store or {}).get("series") or [], PREFIX,
                                   open_id=open_id)

    # --- Edit name / colour / scale / displace ----------------------------- #
    @app.callback(
        Output("trend-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-name", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-color", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-scale", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-displace", "index": ALL}, "value"),
        State("trend-store", "data"),
        prevent_initial_call=True,
    )
    def edit(names, colors, scales, displaces, store):
        if not ctx.triggered:
            raise PreventUpdate
        store = dict(store or {})
        original = store.get("series") or []
        series = [dict(s) for s in original]
        for i, s in enumerate(series):
            if i < len(names):
                s["name"] = names[i] or ""
            if i < len(colors) and colors[i]:
                s["color"] = colors[i]
            if i < len(scales):
                s["scale"] = float(scales[i]) if scales[i] not in (None, "") \
                    else s.get("scale", 1.0)
            if i < len(displaces):
                s["displace"] = float(displaces[i]) if displaces[i] not in (None, "") \
                    else s.get("displace", 0.0)
        if series == original:
            raise PreventUpdate
        store["series"] = series
        return store

    # --- Add derivative / integral ----------------------------------------- #
    def _add(kind, store):
        trig = ctx.triggered_id
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate
        store = dict(store or {})
        series = list(store.get("series") or [])
        src = (_find(series, trig["index"]) or {}).get("source")
        if not src:
            raise PreventUpdate
        label = "d/dx" if kind == "derivative" else "∫"
        series.append({"id": uuid.uuid4().hex[:8], "source": src,
                       "transform": kind, "name": f"{label}({src})",
                       "color": palette_color(len(series)), "scale": 1.0,
                       "displace": 0.0})
        store["series"] = series
        return store

    @app.callback(
        Output("trend-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-add-d", "index": ALL}, "n_clicks"),
        State("trend-store", "data"),
        prevent_initial_call=True,
    )
    def add_derivative(_c, store):
        return _add("derivative", store)

    @app.callback(
        Output("trend-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-add-i", "index": ALL}, "n_clicks"),
        State("trend-store", "data"),
        prevent_initial_call=True,
    )
    def add_integral(_c, store):
        return _add("integral", store)

    # --- Delete a series --------------------------------------------------- #
    @app.callback(
        Output("trend-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-del", "index": ALL}, "n_clicks"),
        State("trend-store", "data"),
        prevent_initial_call=True,
    )
    def delete(_c, store):
        trig = ctx.triggered_id
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate
        store = dict(store or {})
        store["series"] = [s for s in (store.get("series") or [])
                           if s["id"] != trig["index"]]
        return store
