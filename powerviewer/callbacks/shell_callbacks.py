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
    "regression": ("regression-graph", "regression"),
}

# Axes whose zoom we mirror into the figure before exporting.
_AXES = ("xaxis", "yaxis")


def _has_zoom(relayout) -> bool:
    """True if relayoutData carries an explicit (non-auto) axis range."""
    if not relayout:
        return False
    return any(f"{ax}.range[0]" in relayout or f"{ax}.range" in relayout
               for ax in _AXES)


def _apply_view(fig: go.Figure, relayout) -> go.Figure:
    """Mirror the user's current zoom/pan (from relayoutData) onto *fig*.

    Plotly keeps interactive zoom in the graph's ``relayoutData`` (e.g.
    ``{"xaxis.range[0]": .., "xaxis.range[1]": ..}``), not in the ``figure``
    prop. We copy those ranges into the figure so the saved PNG matches what the
    user sees instead of the full auto-ranged plot. Works for numeric and
    datetime axes (relayout values are passed through as-is).
    """
    if not relayout:
        return fig
    for ax in _AXES:
        if relayout.get(f"{ax}.autorange"):
            fig.layout[ax].update(autorange=True, range=None)
            continue
        r0, r1 = relayout.get(f"{ax}.range[0]"), relayout.get(f"{ax}.range[1]")
        rng = relayout.get(f"{ax}.range")
        if r0 is not None and r1 is not None:
            fig.layout[ax].update(range=[r0, r1], autorange=False)
        elif isinstance(rng, (list, tuple)) and len(rng) == 2:
            fig.layout[ax].update(range=list(rng), autorange=False)
    return fig


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
        State("regression-graph", "figure"),
        # User zoom/pan lives in relayoutData, NOT in the figure prop, so we must
        # read it to capture the current (zoomed) view rather than the full plot.
        State("dispersion-graph", "relayoutData"),
        State("trend-graph", "relayoutData"),
        State("multi-graph", "relayoutData"),
        State("regression-graph", "relayoutData"),
        prevent_initial_call=True,
    )
    def screenshot(_n, active, disp_fig, trend_fig, multi_fig, reg_fig,
                   disp_rl, trend_rl, multi_rl, reg_rl):
        figs = {"dispersion": (disp_fig, disp_rl), "trend": (trend_fig, trend_rl),
                "multi_trend": (multi_fig, multi_rl),
                "regression": (reg_fig, reg_rl)}
        fig_dict, relayout = figs.get(active, (None, None))
        if not fig_dict:
            return "Nothing to capture yet."
        _, prefix = _GRAPH_OF[active]
        fig = _apply_view(go.Figure(fig_dict), relayout)
        path = save_screenshot(fig, prefix)
        zoomed = " (zoomed view)" if _has_zoom(relayout) else ""
        return f"📷 Saved screenshot{zoomed} → {path.name}"
