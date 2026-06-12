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
from ..ui.cards import render_series_chips

PREFIX = "mt"
# Operator -> display symbol for combined-line names/badges.
_OP_SYM = {"+": "+", "-": "−", "*": "×", "/": "÷"}


def _find(series, sid):
    for s in series:
        if s["id"] == sid:
            return s
    return None


def _zoom_xrange(relayout):
    """Current X zoom window from relayoutData, or None (full range / reset)."""
    if not relayout or relayout.get("xaxis.autorange"):
        return None
    r0, r1 = relayout.get("xaxis.range[0]"), relayout.get("xaxis.range[1]")
    if r0 is not None and r1 is not None:
        return (r0, r1)
    rng = relayout.get("xaxis.range")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        return (rng[0], rng[1])
    return None


def register(app: Dash) -> None:

    # --- Figure ------------------------------------------------------------ #
    @app.callback(
        Output("multi-graph", "figure"),
        Input("multi-store", "data"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        # In scatter mode the per-curve regression refits to the zoomed window,
        # so we read the graph's relayoutData (the X range) as an input.
        Input("multi-graph", "relayoutData"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(store, marks, labels, relayout, filename, table):
        store = store or {}
        series = store.get("series") or []
        cfg = store.get("axis_cfg") or {}
        style = store.get("style", "lines")
        df = load_dataframe(filename, table) if filename else None
        value_range = _zoom_xrange(relayout) if style == "scatter" else None
        fig = multi_trend.build_figure(
            df, store.get("x"), series,
            marks=(marks or {}).get("multi_trend"),
            labels=(labels or {}).get("multi_trend"),
            axis_cfg=cfg, style=style, value_range=value_range)
        # uirevision keys the preserved view. Include axis_cfg + style so toggling
        # shared-zero / line↔scatter actually re-applies the figure (otherwise
        # Plotly keeps the previous view and ignores the new ranges/markers).
        rev = "|".join(s["id"] for s in series) or "empty"
        rev += "::" + style + "::" + repr(sorted((k, str(v))
                                                  for k, v in cfg.items()))
        rev += "::" + repr([s.get("break_time") for s in series])
        fig.update_layout(uirevision=rev)
        return fig

    # --- Chips (bottom bar; each opens a per-series options popover) -------- #
    @app.callback(
        Output("multi-chips", "children"),
        Input("multi-store", "data"),
        Input("chip-open", "data"),
    )
    def chips(store, open_id):
        store = store or {}
        return render_series_chips(store.get("series") or [], PREFIX,
                                   allow_axis=True, open_id=open_id,
                                   scatter=store.get("style") == "scatter")

    # --- Line ↔ scatter display mode --------------------------------------- #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input("multi-style", "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def set_style(style, store):
        store = dict(store or {})
        if store.get("style") == style:
            raise PreventUpdate
        store["style"] = style if style in ("lines", "scatter") else "lines"
        return store

    # --- Per-curve regression: toggle + colour + equation-box corner -------- #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-fit", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-fit-color", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-fit-pos", "index": ALL}, "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def edit_fit(fits, colors, positions, store):
        if not ctx.triggered:
            raise PreventUpdate
        store = dict(store or {})
        original = store.get("series") or []
        series = [dict(s) for s in original]
        for i, s in enumerate(series):
            if i < len(fits):
                s["fit"] = bool(fits[i])
            if i < len(colors) and colors[i]:
                s["fit_color"] = colors[i]
            if i < len(positions) and positions[i]:
                s["fit_pos"] = positions[i]
        if series == original:   # re-render re-fires inputs; bail if unchanged
            raise PreventUpdate
        store["series"] = series
        return store

    # --- Edit name / colour / scale / displace / axis / integral-rule ------ #
    @app.callback(
        Output("multi-store", "data", allow_duplicate=True),
        Input({"type": f"{PREFIX}-name", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-color", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-scale", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-displace", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-axis", "index": ALL}, "value"),
        Input({"type": f"{PREFIX}-int-method", "index": ALL}, "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def edit(names, colors, scales, displaces, axes, methods, store):
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
            # Integral rule only matters for an integral series.
            if (i < len(methods) and methods[i]
                    and s.get("transform") == "integral"):
                s["integral_method"] = methods[i]
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
    def _add(kind, store, method="trapezoid"):
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
        op = base.get("op", "+")
        label = "d/dx" if kind == "derivative" else "∫"
        inner = f" {_OP_SYM[op]} ".join(srcs)
        new = {"id": uuid.uuid4().hex[:8], "transform": kind,
               "name": f"{label}({inner})", "color": palette_color(len(series)),
               "scale": 1.0, "displace": 0.0}
        if kind == "integral":
            new["integral_method"] = method
        # Keep single-source curves on "source" (so the var panel highlights),
        # multi-source (combined) curves on "sources" + their operator.
        if len(srcs) == 1:
            new["source"] = srcs[0]
        else:
            new["sources"] = srcs
            new["op"] = op
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
        State({"type": f"{PREFIX}-int-method", "index": ALL}, "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def add_integral(_c, _methods, store):
        # Use the integration rule chosen on the *clicked* series' chip.
        trig = ctx.triggered_id
        method = "trapezoid"
        if trig and ctx.states_list:
            for st in ctx.states_list[0]:
                if st.get("id", {}).get("index") == trig.get("index"):
                    method = st.get("value") or "trapezoid"
                    break
        return _add("integral", store, method)

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
        State("multi-op", "value"),
        State("multi-sum-b", "value"),
        State("multi-store", "data"),
        prevent_initial_call=True,
    )
    def add_sum(_n, col_a, op, col_b, store):
        if not col_a or not col_b:
            raise PreventUpdate
        op = op if op in ("+", "-", "*", "/") else "+"
        store = dict(store or {})
        series = list(store.get("series") or [])
        sources = [col_a, col_b]
        series.append({"id": uuid.uuid4().hex[:8], "sources": sources,
                       "op": op, "transform": "none",
                       "name": f"{col_a} {_OP_SYM[op]} {col_b}",
                       "color": palette_color(len(series)), "scale": 1.0,
                       "displace": 0.0})
        store["series"] = series
        return store
