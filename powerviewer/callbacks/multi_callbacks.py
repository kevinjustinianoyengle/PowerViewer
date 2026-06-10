"""Callbacks for the Multiple Trend viewer (series-list model).

Each curve is a series ``{id, source, transform, name, color, scale, displace}``.
Variables add raw series (handled in ``variables.py``); here we render the cards,
apply edits, add derivative/integral series, delete series, and draw the figure.
"""

from __future__ import annotations

import uuid

from dash import ALL, Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from ..config import palette_color, secondary_color
from ..data import load_dataframe
from ..graphs import multi_trend
from ..ui.cards import render_series_cards

PREFIX = "mt"


def _find(series, sid):
    for s in series:
        if s["id"] == sid:
            return s
    return None


def register(app: Dash) -> None:

    # --- Figure ------------------------------------------------------------ #
    @app.callback(
        Output("multi-graph", "figure"),
        Input("multi-store", "data"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(store, marks, labels, filename, table):
        store = store or {}
        series = store.get("series") or []
        df = load_dataframe(filename, table) if filename else None
        fig = multi_trend.build_figure(
            df, store.get("x"), series,
            marks=(marks or {}).get("multi_trend"),
            labels=(labels or {}).get("multi_trend"),
            axis_cfg=store.get("axis_cfg") or {})
        fig.update_layout(uirevision="|".join(s["id"] for s in series) or "empty")
        return fig

    # --- Cards ------------------------------------------------------------- #
    @app.callback(
        Output("multi-line-controls", "children"),
        Input("multi-store", "data"),
    )
    def cards(store):
        return render_series_cards((store or {}).get("series") or [], PREFIX,
                                   allow_axis=True)

    # --- Edit name / colour / scale / displace / axis ---------------------- #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-name", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-color", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-scale", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-displace", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-axis", "index": ALL}, "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def edit(names, colors, scales, displaces, axes, store):
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
            if i < len(axes) and axes[i] in ("left", "right"):
                new_axis = axes[i]
                if new_axis != s.get("axis", "left"):
                    # Recolour from the axis-specific palette so it's obvious
                    # which scale a moved trend belongs to.
                    s["axis"] = new_axis
                    n = sum(1 for ss in series[:i]
                            if ss.get("axis", "left") == new_axis)
                    s["color"] = (secondary_color(n) if new_axis == "right"
                                  else palette_color(n))
        if series == original:  # re-render re-fires inputs; bail if unchanged
            raise PreventUpdate
        store["series"] = series
        return store

    # --- Add derivative / integral of a series' source --------------------- #
    def _add(kind, store):
        trig = ctx.triggered_id
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate
        store = dict(store or {})
        series = list(store.get("series") or [])
        base = _find(series, trig["index"]) or {}
        srcs = base.get("sources") or ([base["source"]] if base.get("source")
                                       else [])
        if not srcs:
            raise PreventUpdate
        label = "d/dx" if kind == "derivative" else "∫"
        inner = " + ".join(srcs)
        new = {"id": uuid.uuid4().hex[:8], "transform": kind,
               "name": f"{label}({inner})", "color": palette_color(len(series)),
               "scale": 1.0, "displace": 0.0}
        # Keep single-source curves on "source" (so the var panel highlights),
        # multi-source (sum) curves on "sources".
        if len(srcs) == 1:
            new["source"] = srcs[0]
        else:
            new["sources"] = srcs
        series.append(new)
        store["series"] = series
        return store

    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-add-d", "index": ALL}, "n_clicks"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def add_derivative(_c, store):
        return _add("derivative", store)

    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-add-i", "index": ALL}, "n_clicks"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def add_integral(_c, store):
        return _add("integral", store)

    # --- Delete a series --------------------------------------------------- #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-del", "index": ALL}, "n_clicks"),
        State("multi-store", "data"),
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

    # --- Sum of two lines -------------------------------------------------- #
    def _source_columns(store):
        """Distinct underlying columns of the current single-source series."""
        seen = []
        for s in (store or {}).get("series") or []:
            src = s.get("source")
            if src and src not in seen:
                seen.append(src)
        return seen

    @app.callback(
        Output("multi-sum-a", "options"),
        Output("multi-sum-b", "options"),
        Input("multi-store", "data"),
    )
    def sum_options(store):
        opts = [{"label": c, "value": c} for c in _source_columns(store)]
        return opts, opts

    # --- Vertical-axis config: shared zero + manual min/max ---------------- #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input("multi-share-zero", "value"),
        Input("multi-lmin", "value"),
        Input("multi-lmax", "value"),
        Input("multi-rmin", "value"),
        Input("multi-rmax", "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def axis_config(share, lmin, lmax, rmin, rmax, store):
        store = dict(store or {})
        store["axis_cfg"] = {"share_zero": bool(share),
                             "lmin": lmin, "lmax": lmax,
                             "rmin": rmin, "rmax": rmax}
        return store

    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input("multi-sum-add", "n_clicks"),
        State("multi-sum-a", "value"),
        State("multi-sum-b", "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def add_sum(_n, col_a, col_b, store):
        if not col_a or not col_b:
            raise PreventUpdate
        store = dict(store or {})
        series = list(store.get("series") or [])
        sources = [col_a, col_b]
        series.append({"id": uuid.uuid4().hex[:8], "sources": sources,
                       "transform": "none", "name": " + ".join(sources),
                       "color": palette_color(len(series)), "scale": 1.0,
                       "displace": 0.0})
        store["series"] = series
        return store
