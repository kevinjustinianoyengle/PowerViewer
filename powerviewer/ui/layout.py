"""Assemble the PowerViewer page.

Layout:

    +------------------------------------------------------------+
    | header   ☰ | title | file chooser | ............| 📷 right |
    +------------------------------------------------------------+
    | ribbon   ✎ Edit Labels · ⇄ Adjust Axes · ⚐ Marks · ⚙ View |
    +----------------------------------------+-------------------+
    | graph (active viewer)                  | vars (slim, right)|
    +----------------------------------------+-------------------+
    | chips   ● series-a   ● series-b   …  (click → options pop) |
    +------------------------------------------------------------+

Two full-width zones frame the graph:

* the **top ribbon** holds *view-wide* options — each button raises a floating
  popover beneath it: **Edit Labels** (titles), **Adjust Axes** (Multiple-Trend
  dual-axis ranges), **Marks** (horizontal / vertical / point), and **View**
  (the active viewer's own controls: distribution / trend swap / line↔scatter +
  sum). Per-curve regression lives on the Multiple-Trend chips, not here;
* the **bottom chip bar** lists the *series drawn in the graph*. Each chip shows
  the series colour + name (+ L/R axis badge for Multiple Trend) and, when
  clicked, raises a popover *above it* with that series' options.

A left **sidebar drawer** (the ☰ burger) is still the graph chooser. Every viewer
has its own ``dcc.Graph``; only the active one is shown. State lives in stores.
"""

from __future__ import annotations

from dash import dcc, html

from ..config import DEFAULT_VIEWER, THEME, VIEWERS
from ..data import list_data_files
from . import theme as T

GRAPH_CONFIG = {
    "displayModeBar": True,
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
    "toImageButtonOptions": {"format": "png", "scale": 2,
                             "filename": "powerviewer"},
}

# A popover input that fills its field width.
_FULL_INPUT = {**T.SMALL_INPUT, "width": "100%", "boxSizing": "border-box"}
_HALF_INPUT = {**T.SMALL_INPUT, "width": "100px"}


def _header() -> html.Div:
    files = list_data_files()
    options = [{"label": f, "value": f} for f in files]
    return html.Div([
        html.Button("☰", id="burger", n_clicks=0, style=T.BURGER,
                    title="Choose graph"),
        html.P("⚡ PowerViewer", style=T.TITLE),
        html.Span("Data file:", style=T.SECTION_LABEL),
        dcc.Dropdown(
            id="file-dropdown", options=options,
            value=files[0] if files else None,
            placeholder="Drop a .csv / .xlsx / .db into '1. Data' …",
            clearable=False, style=T.DROPDOWN,
        ),
        html.Div(
            dcc.Dropdown(id="table-dropdown", placeholder="Table…",
                         clearable=False, style=T.DROPDOWN),
            id="table-wrap", style={"display": "none"},
        ),
        html.Button("⟳ Refresh", id="refresh-files", n_clicks=0, style=T.BUTTON),
        html.Span(id="data-status", style=T.STATUS),
        # Names the saved PNG (blank -> <viewer>_<timestamp>); see shell_callbacks.
        dcc.Input(id="screenshot-name", type="text", debounce=True,
                  placeholder="Screenshot name…",
                  style={**T.SMALL_INPUT, "width": "170px",
                         "marginLeft": "12px"}),
        html.Button("📷 Screenshot", id="save-screenshot", n_clicks=0,
                    style={**T.BUTTON_ACCENT, "marginLeft": "8px"}),
    ], style=T.HEADER)


def _sidebar() -> html.Div:
    """Left drawer: choose the graph to view + the active graph's description."""
    viewer_buttons = [
        html.Button(
            [html.Span(v["icon"], style={"fontSize": "16px"}),
             html.Span(v["label"])],
            id={"type": "viewer-btn", "index": v["key"]},
            n_clicks=0,
            style=T.sidebar_viewer_button(v["key"] == DEFAULT_VIEWER),
        )
        for v in VIEWERS
    ]
    return html.Div([
        html.Div(id="overlay", style={"display": "none"}),
        html.Div([
            html.P("Graphs", style=T.SIDEBAR_TITLE),
            html.Div(viewer_buttons),
            html.Button("Close", id="sidebar-close", n_clicks=0,
                        style={**T.BUTTON, "marginTop": "10px"}),
            html.Div(style={"flex": "1"}),
            html.Hr(style={"borderColor": THEME["border"], "width": "100%"}),
            html.Div([
                html.P(id="caption-title", style=T.CAPTION_TITLE),
                html.P(id="caption-desc", style=T.CAPTION_DESC),
            ]),
        ], id="sidebar", style=T.sidebar(False)),
    ], style={"display": "contents"})


# --------------------------------------------------------------------------- #
# Top ribbon — one button per popover.
# --------------------------------------------------------------------------- #
def _menu(key: str, label, content, wrap_id: str | None = None) -> html.Div:
    children = [
        html.Button(label, id=f"ribbon-btn-{key}", n_clicks=0,
                    style=T.ribbon_button(False)),
        html.Div(content, id=f"ribbon-pop-{key}", style=T.ribbon_popover(False)),
    ]
    kwargs = {"style": T.RIBBON_MENU}
    if wrap_id is not None:
        kwargs["id"] = wrap_id
    return html.Div(children, **kwargs)


def _labels_popover() -> html.Div:
    return html.Div([
        html.P("Labels", style=T.POPOVER_TITLE),
        html.Div([
            dcc.Input(id="label-title", type="text", debounce=True,
                      placeholder="Title", style=_FULL_INPUT),
        ], style=T.POPOVER_FIELD),
        html.Div([
            dcc.Input(id="label-xaxis", type="text", debounce=True,
                      placeholder="X-axis title", style=_FULL_INPUT),
        ], style=T.POPOVER_FIELD),
        html.Div([
            dcc.Input(id="label-yaxis", type="text", debounce=True,
                      placeholder="Y-axis title", style=_FULL_INPUT),
        ], style=T.POPOVER_FIELD),
        # Right (secondary) axis title — only meaningful in Multiple Trend.
        html.Div(
            dcc.Input(id="label-yaxis2", type="text", debounce=True,
                      placeholder="Y-right title", style=_FULL_INPUT),
            id="label-yaxis2-wrap", style={"display": "none"}),
        html.Span("Legend box", style=T.POPOVER_TITLE),
        dcc.Dropdown(
            id="label-legend-pos",
            options=[{"label": "Top-left", "value": "tl"},
                     {"label": "Top-right", "value": "tr"},
                     {"label": "Bottom-left", "value": "bl"},
                     {"label": "Bottom-right", "value": "br"},
                     {"label": "Outside (right)", "value": "out"}],
            value="tr", clearable=False, searchable=False,
            style={"color": "#111", "fontSize": "12px"}),
    ], style={"minWidth": "240px"})


def _axes_popover() -> html.Div:
    """Multiple-Trend dual-axis controls (shared zero + manual ranges)."""
    return html.Div([
        html.P("Axes", style=T.POPOVER_TITLE),
        dcc.Checklist(
            id="multi-share-zero",
            options=[{"label": " Align both axes' zero", "value": "on"}],
            value=["on"], style={"marginBottom": "10px"}),
        html.Div([
            html.Span("Left axis range", style=T.POPOVER_TITLE),
            html.Div([
                dcc.Input(id="multi-lmin", type="number", placeholder="min",
                          style=_HALF_INPUT),
                dcc.Input(id="multi-lmax", type="number", placeholder="max",
                          style=_HALF_INPUT),
            ], style=T.POPOVER_FIELD_ROW),
        ], style=T.POPOVER_FIELD),
        html.Div([
            html.Span("Right axis range", style=T.POPOVER_TITLE),
            html.Div([
                dcc.Input(id="multi-rmin", type="number", placeholder="min",
                          style=_HALF_INPUT),
                dcc.Input(id="multi-rmax", type="number", placeholder="max",
                          style=_HALF_INPUT),
            ], style=T.POPOVER_FIELD_ROW),
        ], style=T.POPOVER_FIELD),
    ], style={"minWidth": "240px"})


def _marks_popover() -> html.Div:
    return html.Div([
        html.P("Marks", style=T.POPOVER_TITLE),
        html.Div([
            dcc.Dropdown(
                id="mark-kind",
                options=[{"label": "Horizontal", "value": "h"},
                         {"label": "Vertical", "value": "v"},
                         {"label": "Point", "value": "point"}],
                value="h", clearable=False,
                style={"width": "130px", "color": "#111"}),
            # Text so a datetime can be typed for a time axis; numbers work too.
            dcc.Input(id="mark-x", type="text", placeholder="value / x / date",
                      style=T.SMALL_INPUT),
            dcc.Input(id="mark-y", type="number", placeholder="y",
                      style={**T.SMALL_INPUT, "display": "none"}),
            dcc.Input(id="mark-label", type="text", placeholder="label",
                      style=T.SMALL_INPUT),
            html.Button("+", id="add-mark", n_clicks=0,
                        style={**T.BUTTON_ACCENT, "padding": "6px 12px",
                               "fontSize": "16px"}),
            html.Button("Clear all", id="clear-marks", n_clicks=0,
                        style=T.BUTTON),
        ], style={**T.POPOVER_FIELD_ROW, "marginBottom": "10px"}),
        html.Div(id="marks-list",
                 style={"display": "flex", "flexWrap": "wrap", "gap": "6px"}),
    ], style={"minWidth": "420px"})


def _dispersion_options() -> html.Div:
    return html.Div([
        html.Span("Distribution", style=T.SECTION_LABEL),
        dcc.RadioItems(
            id="disp-distributions",
            options=[{"label": " None", "value": "none"},
                     {"label": " Uniform", "value": "uniform"},
                     {"label": " Normal", "value": "normal"},
                     {"label": " Log-normal", "value": "lognormal"},
                     {"label": " Exponential", "value": "exponential"}],
            value="none", labelStyle={"display": "block", "marginBottom": "3px"}),
        html.Hr(style={"borderColor": THEME["border"], "margin": "10px 0"}),
        html.Span("Bins", style=T.SECTION_LABEL),
        dcc.Slider(id="disp-bins", min=10, max=120, step=5, value=40,
                   marks=None, tooltip={"placement": "bottom"}),
        html.Span("Fit colour", style={**T.SECTION_LABEL,
                                        "display": "block", "marginTop": "8px"}),
        html.Div(id="disp-fit-colors",
                 children=html.Span("pick a distribution", style=T.CHIP_HINT),
                 style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
        html.Hr(style={"borderColor": THEME["border"], "margin": "10px 0"}),
        html.Span("Moments", style=T.SECTION_LABEL),
        html.Div(id="disp-stats",
                 style={"display": "flex", "gap": "8px", "flexWrap": "wrap",
                        "marginTop": "4px"}),
    ], style={"minWidth": "260px"})


def _multi_options() -> html.Div:
    """Multiple-Trend **Display** popover (the per-graph ⚙ View button)."""
    return html.Div([
        html.Span("Display", style=T.SECTION_LABEL),
        dcc.RadioItems(
            id="multi-style",
            options=[{"label": " Lines (connected)", "value": "lines"},
                     {"label": " Scatter (points)", "value": "scatter"}],
            value="lines", labelStyle={"display": "block", "marginBottom": "3px"}),
        html.P("Scatter mode unlocks a per-curve regression line in each chip "
               "(bottom).", style={**T.CHIP_HINT, "margin": "4px 0 0 0"}),
    ], style={"minWidth": "240px"})


def _combine_popover() -> html.Div:
    """Multiple-Trend **Combine** popover: a OP b → a new derived line."""
    return html.Div([
        html.P("Combine two lines", style=T.POPOVER_TITLE),
        html.Div([
            dcc.Dropdown(id="multi-sum-a", placeholder="line A",
                         style={"width": "170px", "color": "#111",
                                "fontSize": "12px"}),
            dcc.Dropdown(
                id="multi-op",
                options=[{"label": "+  add", "value": "+"},
                         {"label": "−  subtract", "value": "-"},
                         {"label": "×  multiply", "value": "*"},
                         {"label": "÷  divide", "value": "/"}],
                value="+", clearable=False, searchable=False,
                style={"width": "120px", "color": "#111", "fontSize": "12px"}),
            dcc.Dropdown(id="multi-sum-b", placeholder="line B",
                         style={"width": "170px", "color": "#111",
                                "fontSize": "12px"}),
        ], style={**T.POPOVER_FIELD_ROW, "margin": "8px 0"}),
        html.Button("+ Add combined line", id="multi-sum-add", n_clicks=0,
                    style=T.BUTTON_ACCENT),
    ], style={"minWidth": "300px"})


def _break_popover() -> html.Div:
    """Report **Break to zero** (Trends only): pick a line + a Y break value and
    re-shape its discharge half to deplete to zero. Wired in report_callbacks."""
    return html.Div([
        html.P("Break to zero (energy report)", style=T.POPOVER_TITLE),
        html.Span("Line", style=T.POPOVER_TITLE),
        dcc.Dropdown(id="break-line", placeholder="choose a line…",
                     clearable=False, searchable=False,
                     style={"color": "#111", "fontSize": "12px",
                            "marginBottom": "10px"}),
        html.Span("Break time (X)", style=T.POPOVER_TITLE),
        dcc.Input(id="break-time", type="text",
                  placeholder="YYYY-MM-DD HH:MM", style=_FULL_INPUT),
        html.Div([
            html.Button("Apply break", id="break-apply", n_clicks=0,
                        style=T.BUTTON_ACCENT),
            html.Button("Clear", id="break-clear", n_clicks=0, style=T.BUTTON),
        ], style={**T.POPOVER_FIELD_ROW, "marginTop": "10px"}),
        html.Div(id="break-status",
                 style={**T.CHIP_HINT, "marginTop": "8px"}),
    ], style={"minWidth": "280px"})


def _view_popover() -> html.Div:
    """The active viewer's own controls (only the active one is shown)."""
    return html.Div([
        html.Div(_dispersion_options(), id="dispersion-options",
                 style={"display": "block"}),
        html.Div(_multi_options(), id="multi-options", style={"display": "none"}),
    ])


def _ribbon() -> html.Div:
    return html.Div([
        _menu("labels", [html.Span("✎"), html.Span("Edit Labels")],
              _labels_popover()),
        _menu("axes", [html.Span("⇄"), html.Span("Adjust Axes")],
              _axes_popover(), wrap_id="ribbon-axes-menu"),
        # Combine + Break (Trends only) — shown/hidden by ribbon_callbacks.chrome.
        _menu("combine", [html.Span("Σ"), html.Span("Combine")],
              _combine_popover(), wrap_id="ribbon-combine-menu"),
        _menu("break", [html.Span("⌁"), html.Span("Break")],
              _break_popover(), wrap_id="ribbon-break-menu"),
        html.Div(style=T.RIBBON_DIVIDER),
        _menu("marks", [html.Span("⚐"), html.Span("Marks")], _marks_popover()),
        _menu("view", [html.Span("⚙"), html.Span("View")], _view_popover()),
    ], style=T.RIBBON)


def _graph_area() -> html.Div:
    graphs = [
        html.Div(dcc.Graph(id="dispersion-graph", style=T.GRAPH,
                           config=GRAPH_CONFIG),
                 id="dispersion-graph-wrap",
                 style={"flex": "1", "minHeight": "0", "display": "block"}),
        html.Div(dcc.Graph(id="multi-graph", style=T.GRAPH, config=GRAPH_CONFIG),
                 id="multi-graph-wrap",
                 style={"flex": "1", "minHeight": "0", "display": "none"}),
    ]
    return html.Div(graphs,
                    style={**T.GRAPH_AREA, "display": "flex",
                           "flexDirection": "column"})


def _vars_panel() -> html.Div:
    return html.Div([
        html.P("Variables", style=T.VARS_TITLE),
        html.Div(id="vars-list",
                 children=html.Span("Load a data file.",
                                    style={"color": THEME["muted"],
                                           "fontSize": "11px"})),
    ], style=T.VARS_PANEL_SLIM)


def _chip_bar() -> html.Div:
    """Bottom bar: the series drawn in the active graph (each opens a popover)."""
    hidden = {"display": "none", "alignItems": "center", "gap": "10px",
              "flexWrap": "wrap"}
    return html.Div([
        html.Div(id="dispersion-chips", style=hidden),
        html.Div(id="multi-chips", style=hidden),
    ], style=T.CHIP_BAR)


def _stores() -> list:
    return [
        dcc.Store(id="active-view", data=DEFAULT_VIEWER),
        dcc.Store(id="sidebar-open", data=False),
        # Which ribbon popover is open (key) and which chip popover is open (id).
        dcc.Store(id="ribbon-open", data=None),
        dcc.Store(id="chip-open", data=None),
        dcc.Store(id="current-file"),
        dcc.Store(id="current-table"),
        dcc.Store(id="columns-store", data=[]),
        dcc.Store(id="disp-store",
                  data={"col": None, "color": None, "fit_colors": {}}),
        dcc.Store(id="multi-store",
                  data={"x": None, "series": [], "style": "lines",
                        "axis_cfg": {"share_zero": True}}),
        dcc.Store(id="marks-store",
                  data={"dispersion": [], "multi_trend": []}),
        dcc.Store(id="labels-store",
                  data={k["key"]: {"title": "", "xaxis": "", "yaxis": "",
                                   "legend_pos": "tr", "series": {}}
                        for k in VIEWERS}),
    ]


def build_layout() -> html.Div:
    return html.Div(
        _stores() + [
            _sidebar(),
            _header(),
            _ribbon(),
            _graph_area(),
            _vars_panel(),
            _chip_bar(),
        ],
        style=T.PAGE,
    )
