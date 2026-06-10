"""Callbacks for the data-file chooser, viewer switching and panel visibility."""

from __future__ import annotations

from dash import ALL, Dash, Input, Output, ctx, no_update

from ..config import VIEWERS
from ..data import (
    list_data_files,
    list_db_tables,
    load_dataframe,
    plottable_columns,
)
from ..ui import theme as T

_DB_EXT = (".db", ".sqlite", ".sqlite3")


def register(app: Dash) -> None:

    # --- File list refresh ------------------------------------------------- #
    @app.callback(
        Output("file-dropdown", "options"),
        Input("refresh-files", "n_clicks"),
        prevent_initial_call=True,
    )
    def refresh_files(_n):
        return [{"label": f, "value": f} for f in list_data_files()]

    # --- Show / populate the table chooser for SQLite files ---------------- #
    @app.callback(
        Output("table-wrap", "style"),
        Output("table-dropdown", "options"),
        Output("table-dropdown", "value"),
        Input("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_table_chooser(filename):
        if filename and filename.lower().endswith(_DB_EXT):
            tables = list_db_tables(filename)
            opts = [{"label": t, "value": t} for t in tables]
            value = tables[0] if tables else None
            return {"display": "block"}, opts, value
        return {"display": "none"}, [], None

    # --- Resolve the active file/table -> columns + reset selections ------- #
    @app.callback(
        Output("current-file", "data"),
        Output("current-table", "data"),
        Output("columns-store", "data"),
        Output("data-status", "children"),
        Output("disp-store", "data", allow_duplicate=True),
        Output("trend-store", "data", allow_duplicate=True),
        Output("multi-store", "data", allow_duplicate=True),
        Output("regression-store", "data", allow_duplicate=True),
        Output("marks-store", "data", allow_duplicate=True),
        Input("file-dropdown", "value"),
        Input("table-dropdown", "value"),
        prevent_initial_call="initial_duplicate",
    )
    def load_file(filename, table):
        empty_marks = {"dispersion": [], "trend": [], "multi_trend": [],
                       "regression": []}
        reset_disp = {"col": None, "color": None, "fit_colors": {}}
        reset_trend = {"x": None, "y": None, "series": []}
        reset_multi = {"x": None, "series": [], "axis_cfg": {"share_zero": True}}
        reset_reg = {"x": None, "y": None, "color": None, "scale": 1.0,
                     "displace": 0.0}

        if not filename:
            return (None, None, [],
                    "No data loaded — drop a file into '1. Data' and Refresh.",
                    reset_disp, reset_trend, reset_multi, reset_reg, empty_marks)

        is_db = filename.lower().endswith(_DB_EXT)
        if is_db:
            # Guard against a stale table value left over from another file.
            tables = list_db_tables(filename)
            if table not in tables:
                table = tables[0] if tables else None
        else:
            table = None

        try:
            df = load_dataframe(filename, table)
            cols = plottable_columns(filename, table)
        except Exception as exc:  # noqa: BLE001
            return (None, None, [], f"⚠ Could not read '{filename}': {exc}",
                    reset_disp, reset_trend, reset_multi, reset_reg, empty_marks)

        rows = len(df)
        total_cols = len(df.columns)
        status = (f"Loaded '{filename}'"
                  + (f" · table '{table}'" if table else "")
                  + f" — {rows:,} rows · {total_cols} fields "
                  f"· {len(cols)} plottable")
        return (filename, table, cols, status,
                reset_disp, reset_trend, reset_multi, reset_reg, empty_marks)

    # --- Viewer carousel: set the active view + button highlighting -------- #
    @app.callback(
        Output("active-view", "data"),
        Input({"type": "viewer-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def switch_viewer(_clicks):
        trig = ctx.triggered_id
        if not trig:
            return no_update
        return trig["index"]

    @app.callback(
        Output({"type": "viewer-btn", "index": ALL}, "style"),
        Input("active-view", "data"),
    )
    def style_carousel(active):
        return [T.sidebar_viewer_button(v["key"] == active) for v in VIEWERS]

    # --- Toggle which graph + which options panel are visible -------------- #
    @app.callback(
        Output("dispersion-graph-wrap", "style"),
        Output("trend-graph-wrap", "style"),
        Output("multi-graph-wrap", "style"),
        Output("regression-graph-wrap", "style"),
        Output("dispersion-options", "style"),
        Output("trend-options", "style"),
        Output("multi-options", "style"),
        Output("regression-options", "style"),
        Input("active-view", "data"),
    )
    def toggle_visibility(active):
        def vis(key):
            return {"flex": "1", "minHeight": "0",
                    "display": "block" if key == active else "none"}

        def opt(key):
            return {"display": "block" if key == active else "none"}

        return (vis("dispersion"), vis("trend"), vis("multi_trend"),
                vis("regression"),
                opt("dispersion"), opt("trend"), opt("multi_trend"),
                opt("regression"))
