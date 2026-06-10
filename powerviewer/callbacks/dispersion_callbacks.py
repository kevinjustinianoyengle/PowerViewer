"""Callbacks for the 1D Dispersion viewer (render + editable fit colours)."""

from __future__ import annotations

import pandas as pd
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from ..config import THEME
from ..data import load_dataframe
from ..graphs import dispersion_1d
from ..graphs.dispersion_1d import DEFAULT_FIT_COLORS, DISTRIBUTIONS

# Colour choices reused for the per-fit swatch dropdowns.
_CHOICES = ["#58A6FF", "#3FB950", "#BC8CFF", "#FF7A00", "#FF3B30", "#FFD60A",
            "#E6EDF3", "#FF9A3D"]

# Pill style for a single fitted-moment value below the graph.
_STAT_CHIP = {
    "display": "inline-flex", "gap": "4px", "padding": "4px 10px",
    "borderRadius": "14px", "border": f"1px solid {THEME['border']}",
    "backgroundColor": THEME["panel_alt"], "fontSize": "12.5px",
    "color": THEME["text"],
}


def _zoom_xrange(relayout):
    """Extract the current X zoom window from a graph's relayoutData.

    Returns ``(lo, hi)`` for an explicit zoom, or ``None`` for full range /
    autorange reset (so the dispersion is computed over all the data).
    """
    if not relayout or relayout.get("xaxis.autorange"):
        return None
    r0, r1 = relayout.get("xaxis.range[0]"), relayout.get("xaxis.range[1]")
    if r0 is not None and r1 is not None:
        return (r0, r1)
    rng = relayout.get("xaxis.range")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        return (rng[0], rng[1])
    return None


def _swatch(c):
    return {"label": html.Div([
        html.Span(style={"display": "inline-block", "width": "12px",
                         "height": "12px", "borderRadius": "3px",
                         "backgroundColor": c, "marginRight": "6px",
                         "border": f"1px solid {THEME['border']}"}),
        html.Span(c, style={"fontSize": "11px"})],
        style={"display": "flex", "alignItems": "center"}), "value": c}


def register(app: Dash) -> None:

    @app.callback(
        Output("dispersion-graph", "figure"),
        Output("disp-stats", "children"),
        Input("disp-store", "data"),
        Input("disp-distributions", "value"),
        Input("disp-bins", "value"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        # Zoom on the X axis re-bins/re-fits the dispersion to the visible window.
        Input("dispersion-graph", "relayoutData"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(disp, distribution, bins, marks, labels, relayout, filename, table):
        disp = disp or {}
        col = disp.get("col")
        values = None
        times = None
        if filename and col:
            df = load_dataframe(filename, table)
            if col in df.columns:
                values = df[col].to_numpy()
                # Pair each sample with its timestamp (first datetime column),
                # so the dispersion hover can show the time of each point.
                tcols = [c for c in df.columns
                         if pd.api.types.is_datetime64_any_dtype(df[c])]
                if tcols:
                    times = df[tcols[0]].to_numpy()
        # Single-choice radio -> 0-or-1 element list for the builder.
        dist = None if not distribution or distribution == "none" else distribution
        value_range = _zoom_xrange(relayout)
        fig = dispersion_1d.build_figure(
            values, col,
            distributions=[dist] if dist else [],
            bins=int(bins or 40),
            marks=(marks or {}).get("dispersion"),
            fit_colors=disp.get("fit_colors") or {},
            labels=(labels or {}).get("dispersion"),
            times=times,
            value_range=value_range,
        )

        # Fitted-distribution moments, shown outside the plot.
        moments = (dispersion_1d.fit_moments(dist, values, value_range)
                   if (dist and values is not None) else [])
        if not moments:
            stats = html.Span("select a distribution to see its moments",
                              style={"color": THEME["muted"], "fontSize": "12px"})
        else:
            label = dispersion_1d.DISTRIBUTIONS[dist][0]
            stats = ([html.Span(label, style={"fontSize": "12px",
                                              "fontWeight": "700",
                                              "color": THEME["accent"]})]
                     + [html.Span([html.Span(f"{k}: ",
                                             style={"color": THEME["muted"]}),
                                   html.Span(v, style={"fontWeight": "600"})],
                                  style=_STAT_CHIP)
                        for k, v in moments])
        return fig, stats

    # --- A colour dropdown per selected distribution ----------------------- #
    @app.callback(
        Output("disp-fit-colors", "children"),
        Input("disp-distributions", "value"),
        State("disp-store", "data"),
    )
    def fit_color_controls(distribution, disp):
        distributions = ([] if not distribution or distribution == "none"
                         else [distribution])
        if not distributions:
            return html.Span("pick a distribution",
                             style={"color": THEME["muted"], "fontSize": "12px"})
        chosen = (disp or {}).get("fit_colors") or {}
        rows = []
        for name in distributions:
            current = chosen.get(name) or DEFAULT_FIT_COLORS.get(name, "#FF7A00")
            opts = _CHOICES if current in _CHOICES else [current] + _CHOICES
            rows.append(html.Div([
                html.Span(DISTRIBUTIONS[name][0],
                          style={"fontSize": "11px", "color": THEME["muted"]}),
                dcc.Dropdown(id={"type": "fit-color", "index": name},
                             options=[_swatch(c) for c in opts], value=current,
                             clearable=False, searchable=False,
                             style={"width": "120px", "color": "#111",
                                    "fontSize": "11px"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "4px"}))
        return rows

    # --- Apply fit-colour edits into the store ----------------------------- #
    @app.callback(
        Output("disp-store", "data", allow_duplicate=True),
        Input({"type": "fit-color", "index": ALL}, "value"),
        State("disp-store", "data"),
        prevent_initial_call=True,
    )
    def apply_fit_colors(values, disp):
        if not ctx.triggered:
            raise PreventUpdate
        disp = dict(disp or {})
        fit_colors = dict(disp.get("fit_colors") or {})
        for item, val in zip(ctx.inputs_list[0], values):
            if val:
                fit_colors[item["id"]["index"]] = val
        disp["fit_colors"] = fit_colors
        return disp
