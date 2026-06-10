"""Ribbon + chip-bar plumbing.

* Open/close the four ribbon popovers (Labels / Axes / Marks / View).
* Track which bottom chip's options popover is open.
* Show only the active viewer's chip section, hide the Adjust-Axes button for
  viewers without a second axis, and relabel the View button per viewer.
"""

from __future__ import annotations

from dash import ALL, Dash, Input, Output, State, ctx, html
from dash.exceptions import PreventUpdate

from ..ui import theme as T

_RIBBON_KEYS = ["labels", "axes", "marks", "view"]
_VIEW_LABEL = {"dispersion": "Distribution", "trend": "Trend",
               "multi_trend": "Add Sum", "regression": "Regression"}


def register(app: Dash) -> None:

    # --- Which ribbon popover is open -------------------------------------- #
    @app.callback(
        Output("ribbon-open", "data"),
        Input("ribbon-btn-labels", "n_clicks"),
        Input("ribbon-btn-axes", "n_clicks"),
        Input("ribbon-btn-marks", "n_clicks"),
        Input("ribbon-btn-view", "n_clicks"),
        Input("active-view", "data"),
        State("ribbon-open", "data"),
        prevent_initial_call=True,
    )
    def toggle_ribbon(_l, _a, _m, _v, _active, current):
        trig = ctx.triggered_id
        if trig == "active-view":     # switching viewer closes any open popover
            return None
        key = str(trig).replace("ribbon-btn-", "")
        return None if current == key else key

    # --- Apply popover + button styles ------------------------------------- #
    @app.callback(
        Output("ribbon-pop-labels", "style"),
        Output("ribbon-pop-axes", "style"),
        Output("ribbon-pop-marks", "style"),
        Output("ribbon-pop-view", "style"),
        Output("ribbon-btn-labels", "style"),
        Output("ribbon-btn-axes", "style"),
        Output("ribbon-btn-marks", "style"),
        Output("ribbon-btn-view", "style"),
        Input("ribbon-open", "data"),
    )
    def apply_ribbon(open_):
        pops = [T.ribbon_popover(open_ == k) for k in _RIBBON_KEYS]
        btns = [T.ribbon_button(open_ == k) for k in _RIBBON_KEYS]
        return (*pops, *btns)

    # --- Which chip's options popover is open ------------------------------ #
    @app.callback(
        Output("chip-open", "data"),
        Input({"type": "tr-chip", "index": ALL}, "n_clicks"),
        Input({"type": "mt-chip", "index": ALL}, "n_clicks"),
        Input({"type": "disp-chip", "index": ALL}, "n_clicks"),
        Input({"type": "reg-chip", "index": ALL}, "n_clicks"),
        Input("active-view", "data"),
        State("chip-open", "data"),
        prevent_initial_call=True,
    )
    def toggle_chip(_tr, _mt, _dn, _rn, _active, current):
        trig = ctx.triggered_id
        if trig == "active-view":       # switching viewer closes any chip popover
            return None
        if not trig or not ctx.triggered or not ctx.triggered[0]["value"]:
            raise PreventUpdate
        sid = trig["index"]
        return None if current == sid else sid

    # --- Active-viewer dependent chrome ------------------------------------ #
    @app.callback(
        Output("dispersion-chips", "style"),
        Output("trend-chips", "style"),
        Output("multi-chips", "style"),
        Output("regression-chips", "style"),
        Output("ribbon-axes-menu", "style"),
        Output("ribbon-btn-view", "children"),
        Input("active-view", "data"),
    )
    def chrome(active):
        def sec(key):
            return {"display": "flex" if key == active else "none",
                    "alignItems": "center", "gap": "10px", "flexWrap": "wrap"}

        axes_menu = {**T.RIBBON_MENU,
                     "display": "inline-flex" if active == "multi_trend"
                     else "none"}
        view_label = [html.Span("⚙"),
                      html.Span(_VIEW_LABEL.get(active, "View"))]
        return (sec("dispersion"), sec("trend"), sec("multi_trend"),
                sec("regression"), axes_menu, view_label)
