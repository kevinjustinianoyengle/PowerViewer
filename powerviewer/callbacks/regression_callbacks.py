"""Callbacks for the Scatter + Regression viewer.

Renders the scatter, fits a least-squares line over the *visible* points (so the
fit recomputes on zoom), toggles the fit, and positions the equation/R² box.
"""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from ..config import THEME
from ..data import load_dataframe
from ..graphs import regression
from ..graphs.base import series_name
from ..ui import theme as T
from ..ui.cards import color_options, field


def _zoom_ranges(relayout):
    """Return (x_range, y_range) from relayoutData, or (None, None)."""
    if not relayout:
        return None, None

    def axis(ax):
        if relayout.get(f"{ax}.autorange"):
            return None
        r0, r1 = relayout.get(f"{ax}.range[0]"), relayout.get(f"{ax}.range[1]")
        if r0 is not None and r1 is not None:
            return (r0, r1)
        rng = relayout.get(f"{ax}.range")
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            return (rng[0], rng[1])
        return None

    return axis("xaxis"), axis("yaxis")


def register(app: Dash) -> None:

    # Swap X / Y.
    @app.callback(
        Output("regression-store", "data", allow_duplicate=True),
        Input("reg-swap", "n_clicks"),
        State("regression-store", "data"),
        prevent_initial_call=True,
    )
    def swap(_n, store):
        store = dict(store or {})
        if not store.get("x") and not store.get("y"):
            raise PreventUpdate
        store["x"], store["y"] = store.get("y"), store.get("x")
        return store

    @app.callback(
        Output("regression-graph", "figure"),
        Output("reg-axes-label", "children"),
        Input("regression-store", "data"),
        Input("reg-show-fit", "value"),
        Input("reg-annot-pos", "value"),
        Input("marks-store", "data"),
        Input("labels-store", "data"),
        Input("regression-graph", "relayoutData"),
        State("current-file", "data"),
        State("current-table", "data"),
    )
    def render(store, show_fit, annot_pos, marks, labels, relayout,
               filename, table):
        store = store or {}
        x_col, y_col = store.get("x"), store.get("y")
        df = load_dataframe(filename, table) if filename else None
        x_range, y_range = _zoom_ranges(relayout)
        fig = regression.build_figure(
            df, x_col, y_col,
            show_fit=bool(show_fit),
            annot_pos=annot_pos or "tl",
            marks=(marks or {}).get("regression"),
            labels=(labels or {}).get("regression"),
            value_range=x_range, y_range=y_range,
            color=store.get("color"),
            scale=store.get("scale", 1.0),
            displace=store.get("displace", 0.0),
        )
        return fig, f"X: {x_col or '—'}   |   Y: {y_col or '—'}"

    # --- Bottom chip for the single Y series ------------------------------- #
    @app.callback(
        Output("regression-chips", "children"),
        Input("regression-store", "data"),
        Input("labels-store", "data"),
        Input("chip-open", "data"),
    )
    def chip(store, labels, open_id):
        store = store or {}
        y_col = store.get("y")
        if not y_col:
            return html.Span("Pick X then Y on the right.", style=T.CHIP_HINT)
        color = store.get("color") or THEME["accent"]
        name = series_name((labels or {}).get("regression"), y_col, y_col)
        full = {**T.SMALL_INPUT, "width": "100%", "boxSizing": "border-box"}
        is_open = open_id == y_col
        menu = [
            html.P("Series options", style=T.POPOVER_TITLE),
            field("Colour", dcc.Dropdown(
                id="reg-color", options=color_options(color), value=color,
                clearable=False, searchable=False,
                style={"color": "#111", "fontSize": "11px"})),
            field("Rename", dcc.Input(
                id={"type": "series-name", "index": y_col}, type="text",
                value=series_name((labels or {}).get("regression"), y_col, "")
                or "", debounce=True, placeholder=y_col, style=full)),
            field("Scale (×)", dcc.Input(
                id="reg-scale", type="number", value=store.get("scale", 1.0),
                step="any", style=full)),
            field("Displacement (+)", dcc.Input(
                id="reg-displace", type="number",
                value=store.get("displace", 0.0), step="any", style=full)),
            html.Button("Remove series", id="reg-remove", n_clicks=0,
                        style=T.CHIP_REMOVE),
        ]
        return html.Div([
            html.Button([html.Span(style=T.chip_dot(color)),
                         html.Span(name, style=T.CHIP_NAME)],
                        id={"type": "reg-chip", "index": y_col}, n_clicks=0,
                        style=T.chip(is_open)),
            html.Div(menu, style=T.chip_popover(is_open)),
        ], style=T.CHIP_WRAP)

    # --- Apply colour / scale / displacement edits ------------------------- #
    @app.callback(
        Output("regression-store", "data", allow_duplicate=True),
        Input("reg-color", "value"),
        Input("reg-scale", "value"),
        Input("reg-displace", "value"),
        State("regression-store", "data"),
        prevent_initial_call=True,
    )
    def edit(color, scale, displace, store):
        store = dict(store or {})
        if color:
            store["color"] = color
        store["scale"] = (float(scale) if scale not in (None, "")
                          else store.get("scale", 1.0))
        store["displace"] = (float(displace) if displace not in (None, "")
                             else store.get("displace", 0.0))
        return store

    # --- Remove the Y series ----------------------------------------------- #
    @app.callback(
        Output("regression-store", "data", allow_duplicate=True),
        Input("reg-remove", "n_clicks"),
        State("regression-store", "data"),
        prevent_initial_call=True,
    )
    def remove(_n, store):
        if not _n:
            raise PreventUpdate
        store = dict(store or {})
        store["y"] = None
        return store
