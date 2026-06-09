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
        Input("disp-store", "data"),
        Input("disp-distributions", "value"),
        Input("disp-bins", "value"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(disp, distribution, bins, marks, labels, filename, table):
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
        dists = [] if not distribution or distribution == "none" else [distribution]
        return dispersion_1d.build_figure(
            values, col,
            distributions=dists,
            bins=int(bins or 40),
            marks=(marks or {}).get("dispersion"),
            fit_colors=disp.get("fit_colors") or {},
            labels=(labels or {}).get("dispersion"),
            times=times,
        )

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
