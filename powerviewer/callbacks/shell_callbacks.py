"""App-shell callbacks: the burger sidebar, the under-graph caption and the
single top-right screenshot button (which captures the active viewer)."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, no_update

from ..config import VIEWERS
from ..graphs.base import save_screenshot
from ..ui import theme as T

_META = {v["key"]: v for v in VIEWERS}
# active-view key -> (graph id holding the figure, screenshot file prefix)
_GRAPH_OF = {
    "dispersion": ("dispersion-graph", "dispersion"),
    "trend": ("trend-graph", "trend"),
    "multi_trend": ("multi-graph", "multi_trend"),
}


def register(app: Dash) -> None:

    # --- Open / close the sidebar drawer ----------------------------------- #
    @app.callback(
        Output("sidebar-open", "data"),
        Input("burger", "n_clicks"),
        Input("sidebar-close", "n_clicks"),
        Input("overlay", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_sidebar(_b, _c, _o):
        return ctx.triggered_id == "burger"

    @app.callback(
        Output("sidebar", "style"),
        Output("overlay", "style"),
        Input("sidebar-open", "data"),
    )
    def apply_sidebar(open_):
        overlay = T.OVERLAY if open_ else {"display": "none"}
        return T.sidebar(bool(open_)), overlay

    # --- Caption under the graph (viewer title + short description) --------- #
    @app.callback(
        Output("caption-title", "children"),
        Output("caption-desc", "children"),
        Input("active-view", "data"),
    )
    def caption(active):
        meta = _META.get(active, {})
        return meta.get("label", ""), meta.get("help", "")

    # --- Screenshot of the active viewer ----------------------------------- #
    @app.callback(
        Output("data-status", "children", allow_duplicate=True),
        Input("save-screenshot", "n_clicks"),
        State("active-view", "data"),
        State("dispersion-graph", "figure"),
        State("trend-graph", "figure"),
        State("multi-graph", "figure"),
        prevent_initial_call=True,
    )
    def screenshot(_n, active, disp_fig, trend_fig, multi_fig):
        figs = {"dispersion": disp_fig, "trend": trend_fig,
                "multi_trend": multi_fig}
        fig_dict = figs.get(active)
        if not fig_dict:
            return "Nothing to capture yet."
        _, prefix = _GRAPH_OF[active]
        path = save_screenshot(go.Figure(fig_dict), prefix)
        return f"📷 Saved screenshot → {path.name}"
