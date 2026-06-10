"""Sidebar label editing: title / axis titles / legend names per active viewer.

Overrides live in ``labels-store`` keyed by viewer:
``{viewer: {"title", "xaxis", "yaxis", "series": {column: name}}}``.
"""

from __future__ import annotations

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from ..config import THEME
from ..ui import theme as T


def _series_cols(active, disp, trend, multi):
    """Columns whose legend entry can be renamed for the active viewer.

    Trend / Multiple Trend rename their series directly on the cards, so only
    the dispersion histogram needs a legend-rename field here.
    """
    if active == "dispersion":
        c = (disp or {}).get("col")
        return [c] if c else []
    return []


def register(app: Dash) -> None:

    # The right-axis title only applies to Multiple Trend (two Y axes).
    @app.callback(
        Output("label-yaxis2-wrap", "style"),
        Input("active-view", "data"),
    )
    def toggle_yaxis2(active):
        return {"display": "block" if active == "multi_trend" else "none"}

    # --- Populate the label inputs when the active viewer changes ----------- #
    @app.callback(
        Output("label-title", "value"),
        Output("label-xaxis", "value"),
        Output("label-yaxis", "value"),
        Output("label-yaxis2", "value"),
        Input("active-view", "data"),
        State("labels-store", "data"),
    )
    def populate(active, labels):
        lab = (labels or {}).get(active, {})
        return (lab.get("title", ""), lab.get("xaxis", ""),
                lab.get("yaxis", ""), lab.get("yaxis2", ""))

    # --- Save title / axis edits back into the store ----------------------- #
    @app.callback(
        Output("labels-store", "data", allow_duplicate=True),
        Input("label-title", "value"),
        Input("label-xaxis", "value"),
        Input("label-yaxis", "value"),
        Input("label-yaxis2", "value"),
        State("active-view", "data"),
        State("labels-store", "data"),
        prevent_initial_call=True,
    )
    def save_labels(title, xaxis, yaxis, yaxis2, active, labels):
        labels = dict(labels or {})
        entry = dict(labels.get(active, {"series": {}}))
        entry["title"] = title or ""
        entry["xaxis"] = xaxis or ""
        entry["yaxis"] = yaxis or ""
        entry["yaxis2"] = yaxis2 or ""
        entry.setdefault("series", {})
        labels[active] = entry
        return labels

    # --- Render per-series rename inputs ----------------------------------- #
    @app.callback(
        Output("legend-editor", "children"),
        Input("active-view", "data"),
        Input("disp-store", "data"),
        Input("trend-store", "data"),
        Input("multi-store", "data"),
        State("labels-store", "data"),
    )
    def legend_editor(active, disp, trend, multi, labels):
        cols = _series_cols(active, disp, trend, multi)
        if not cols:
            return html.Span("Select variables to rename their legend entries.",
                             style=T.CAPTION_DESC)
        series = ((labels or {}).get(active, {}) or {}).get("series", {})
        rows = []
        for col in cols:
            rows.append(html.Div([
                html.Span(col, style={"fontSize": "11px",
                                      "color": THEME["muted"]}),
                dcc.Input(
                    id={"type": "series-name", "index": col},
                    type="text", debounce=True,
                    value=series.get(col, ""), placeholder=col,
                    style={**T.SMALL_INPUT, "width": "120px"},
                ),
            ], style={"display": "flex", "alignItems": "center", "gap": "4px"}))
        return rows

    # --- Save legend renames ---------------------------------------------- #
    @app.callback(
        Output("labels-store", "data", allow_duplicate=True),
        Input({"type": "series-name", "index": ALL}, "value"),
        State("active-view", "data"),
        State("labels-store", "data"),
        prevent_initial_call=True,
    )
    def save_legend(values, active, labels):
        if not ctx.triggered:
            raise PreventUpdate
        labels = dict(labels or {})
        entry = dict(labels.get(active, {"title": "", "xaxis": "", "yaxis": ""}))
        series = dict(entry.get("series", {}))
        for item, val in zip(ctx.inputs_list[0], values):
            col = item["id"]["index"]
            if val:
                series[col] = val
            else:
                series.pop(col, None)
        entry["series"] = series
        labels[active] = entry
        return labels
