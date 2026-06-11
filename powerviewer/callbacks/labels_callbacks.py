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

    # --- Populate the label inputs (incl. the header title) ----------------- #
    # Triggered by active-view AND labels-store so the header title and the Edit
    # Labels title stay mirrored (both reflect the stored title).
    @app.callback(
        Output("label-title", "value"),
        Output("label-xaxis", "value"),
        Output("label-yaxis", "value"),
        Output("label-yaxis2", "value"),
        Output("header-title", "value"),
        Input("active-view", "data"),
        Input("labels-store", "data"),
    )
    def populate(active, labels):
        lab = (labels or {}).get(active, {})
        title = lab.get("title", "")
        return (title, lab.get("xaxis", ""), lab.get("yaxis", ""),
                lab.get("yaxis2", ""), title)

    # --- Save title / axis edits back into the store ----------------------- #
    # The graph title can be edited from the header box or the Edit Labels box;
    # the trigger decides which one is authoritative. An equality guard keeps the
    # populate↔save mirror from looping.
    @app.callback(
        Output("labels-store", "data", allow_duplicate=True),
        Input("label-title", "value"),
        Input("header-title", "value"),
        Input("label-xaxis", "value"),
        Input("label-yaxis", "value"),
        Input("label-yaxis2", "value"),
        State("active-view", "data"),
        State("labels-store", "data"),
        prevent_initial_call=True,
    )
    def save_labels(title, header_title, xaxis, yaxis, yaxis2, active, labels):
        labels = dict(labels or {})
        entry = dict(labels.get(active, {"series": {}}))
        new_title = header_title if ctx.triggered_id == "header-title" else title
        entry["title"] = new_title or ""
        entry["xaxis"] = xaxis or ""
        entry["yaxis"] = yaxis or ""
        entry["yaxis2"] = yaxis2 or ""
        entry.setdefault("series", {})
        if entry == labels.get(active):   # no real change -> break mirror loop
            raise PreventUpdate
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
