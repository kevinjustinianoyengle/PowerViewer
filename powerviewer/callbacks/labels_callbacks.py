"""Sidebar label editing: title / axis titles / legend names per active viewer.

Overrides live in ``labels-store`` keyed by viewer:
``{viewer: {"title", "xaxis", "yaxis", "series": {column: name}}}``.
"""

from __future__ import annotations

from dash import ALL, Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate

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

    # --- Save legend renames (chip "Rename" inputs use the same ids) ------- #
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
