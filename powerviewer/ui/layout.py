"""Assemble the PowerViewer page.

Layout:

    +------------------------------------------------------------+
    | header  ☰ | title | file chooser | ...........| 📷 (right) |
    +------------------------------------------------------------+
    | carousel  (viewer selector)                                |
    +----------------------------------------+-------------------+
    | graph (active viewer)                  | vars (slim, right)|
    | caption: <viewer title + description>  |                   |
    +----------------------------------------+-------------------+
    | options  (per-viewer functional options + marks, bottom)   |
    +------------------------------------------------------------+

A left **sidebar drawer** (toggled by the ☰ burger, overlaying everything with
the top z-index) hosts the graph-appearance options: editable title, axis titles
and legend names for the active viewer.

Every viewer has its own ``dcc.Graph`` so rendering stays fully decoupled; only
the active one is shown. Selection/option state lives in ``dcc.Store`` objects.
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


def _header() -> html.Div:
    files = list_data_files()
    options = [{"label": f, "value": f} for f in files]
    return html.Div([
        html.Button("☰", id="burger", n_clicks=0, style=T.BURGER,
                    title="Graph options"),
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
        # Screenshot lives top-right and captures the active viewer.
        html.Button("📷 Screenshot", id="save-screenshot", n_clicks=0,
                    style={**T.BUTTON_ACCENT, "marginLeft": "12px"}),
    ], style=T.HEADER)


def _sidebar() -> html.Div:
    """Left drawer: choose the graph to view + the active graph's description.

    ``display:contents`` keeps this wrapper out of the page grid; its children
    are position:fixed and overlay everything with the top z-index.
    """
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
            # Spacer pushes the selected-graph caption to the bottom.
            html.Div(style={"flex": "1"}),
            html.Hr(style={"borderColor": THEME["border"], "width": "100%"}),
            html.Div([
                html.P(id="caption-title", style=T.CAPTION_TITLE),
                html.P(id="caption-desc", style=T.CAPTION_DESC),
            ]),
        ], id="sidebar", style=T.sidebar(False)),
    ], style={"display": "contents"})


def _graph_area() -> html.Div:
    graphs = [
        html.Div(dcc.Graph(id="dispersion-graph", style=T.GRAPH,
                           config=GRAPH_CONFIG),
                 id="dispersion-graph-wrap",
                 style={"flex": "1", "minHeight": "0", "display": "block"}),
        html.Div(dcc.Graph(id="trend-graph", style=T.GRAPH, config=GRAPH_CONFIG),
                 id="trend-graph-wrap",
                 style={"flex": "1", "minHeight": "0", "display": "none"}),
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


def _marks_controls() -> html.Div:
    """Horizontal marks row: type → value → (y for point) → label → [+], list."""
    return html.Div([
        html.Div([
            html.Span("Marks", style=T.SECTION_LABEL),
            dcc.Dropdown(
                id="mark-kind",
                options=[
                    {"label": "Horizontal", "value": "h"},
                    {"label": "Vertical", "value": "v"},
                    {"label": "Point", "value": "point"},
                ],
                value="h", clearable=False,
                style={"width": "130px", "color": "#111"},
            ),
            # Text (not number) so a datetime can be typed for a vertical/point
            # mark on a time axis, e.g. "2026-06-06 16:00". Plain numbers work too.
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
        ], style={**T.OPTIONS_ROW, "gap": "8px"}),
        html.Div(id="marks-list",
                 style={"display": "flex", "flexWrap": "wrap", "gap": "6px",
                        "marginTop": "8px"}),
    ])


def _dispersion_options() -> html.Div:
    return html.Div([
        html.Span("Distribution", style=T.SECTION_LABEL),
        # Single-choice: only one distribution can be selected at a time.
        dcc.RadioItems(
            id="disp-distributions",
            options=[
                {"label": " None", "value": "none"},
                {"label": " Uniform", "value": "uniform"},
                {"label": " Normal", "value": "normal"},
                {"label": " Log-normal", "value": "lognormal"},
                {"label": " Exponential", "value": "exponential"},
            ],
            value="none", inline=True, labelStyle={"marginRight": "14px"},
            style={"display": "inline-flex"},
        ),
        html.Span("Bins", style={**T.SECTION_LABEL, "marginLeft": "10px"}),
        html.Div(
            dcc.Slider(id="disp-bins", min=10, max=120, step=5, value=40,
                       marks=None, tooltip={"placement": "bottom"}),
            style={"width": "200px"}),
        html.Span("Fit colours:", style={**T.SECTION_LABEL, "marginLeft": "10px"}),
        html.Div(id="disp-fit-colors",
                 children=html.Span("tick a distribution",
                                    style={"color": THEME["muted"],
                                           "fontSize": "12px"}),
                 style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
        # Fitted-distribution moments (shown outside the plot, not in the legend).
        html.Div([
            html.Span("Moments", style=T.SECTION_LABEL),
            html.Div(id="disp-stats",
                     style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
        ], style={**T.OPTIONS_ROW, "gap": "8px", "width": "100%",
                  "marginTop": "8px"}),
    ], style={**T.OPTIONS_ROW, "gap": "10px"})


def _trend_options() -> html.Div:
    return html.Div([
        html.Div([
            html.Button("⇄ Swap X / Y", id="trend-swap", n_clicks=0,
                        style=T.BUTTON_ACCENT),
            html.Span(id="trend-axes-label", style=T.STATUS),
        ], style=T.OPTIONS_ROW),
        # Each series (raw / derivative / integral) is a card with full options.
        html.Div(id="trend-line-controls",
                 children=html.Span("Pick X then Y to add the first curve.",
                                    style={"color": THEME["muted"],
                                           "fontSize": "12px"}),
                 style={"display": "flex", "flexWrap": "wrap", "gap": "8px",
                        "marginTop": "8px"}),
    ])


def _multi_options() -> html.Div:
    return html.Div([
        html.Span("Series", style=T.SECTION_LABEL),
        html.Div(id="multi-line-controls",
                 children=html.Span("Add Y variables to configure them.",
                                    style={"color": THEME["muted"],
                                           "fontSize": "12px"}),
                 style={"display": "flex", "flexDirection": "column",
                        "gap": "6px"}),
        # Build a new series that is the sum of two existing lines.
        html.Div([
            html.Span("Sum two lines:", style=T.SECTION_LABEL),
            dcc.Dropdown(id="multi-sum-a", placeholder="line A",
                         style={"width": "180px", "color": "#111",
                                "fontSize": "12px"}),
            html.Span("+", style={"color": THEME["muted"]}),
            dcc.Dropdown(id="multi-sum-b", placeholder="line B",
                         style={"width": "180px", "color": "#111",
                                "fontSize": "12px"}),
            html.Button("+ Add sum", id="multi-sum-add", n_clicks=0,
                        style=T.BUTTON_ACCENT),
        ], style={**T.OPTIONS_ROW, "gap": "8px", "marginTop": "8px"}),
        # Vertical-axis scale: shared zero + manual min/max for each axis.
        html.Div([
            html.Span("Axes", style=T.SECTION_LABEL),
            dcc.Checklist(
                id="multi-share-zero",
                options=[{"label": " Shared 0", "value": "on"}],
                value=["on"], style={"display": "inline-flex"}),
            html.Span("Left", style=T.SECTION_LABEL),
            dcc.Input(id="multi-lmin", type="number", placeholder="min",
                      style={**T.SMALL_INPUT, "width": "80px"}),
            dcc.Input(id="multi-lmax", type="number", placeholder="max",
                      style={**T.SMALL_INPUT, "width": "80px"}),
            html.Span("Right", style=T.SECTION_LABEL),
            dcc.Input(id="multi-rmin", type="number", placeholder="min",
                      style={**T.SMALL_INPUT, "width": "80px"}),
            dcc.Input(id="multi-rmax", type="number", placeholder="max",
                      style={**T.SMALL_INPUT, "width": "80px"}),
        ], style={**T.OPTIONS_ROW, "gap": "8px", "marginTop": "8px"}),
    ], style={**T.OPTIONS_ROW, "alignItems": "flex-start"})


def _label_options() -> html.Div:
    """Title / axis-title / legend editing (now lives in the bottom panel)."""
    return html.Div([
        html.Span("Labels", style=T.SECTION_LABEL),
        dcc.Input(id="label-title", type="text", debounce=True,
                  placeholder="Title", style=T.SMALL_INPUT),
        dcc.Input(id="label-xaxis", type="text", debounce=True,
                  placeholder="X-axis title", style=T.SMALL_INPUT),
        dcc.Input(id="label-yaxis", type="text", debounce=True,
                  placeholder="Y-axis title", style=T.SMALL_INPUT),
        # Right (secondary) axis title — only meaningful in Multiple Trend.
        html.Div(
            dcc.Input(id="label-yaxis2", type="text", debounce=True,
                      placeholder="Y-right title", style=T.SMALL_INPUT),
            id="label-yaxis2-wrap", style={"display": "none"}),
        html.Span("Legend:", style=T.SECTION_LABEL),
        html.Div(id="legend-editor",
                 children=html.Span("select variables",
                                    style={"color": THEME["muted"],
                                           "fontSize": "12px"}),
                 style={"display": "flex", "flexWrap": "wrap", "gap": "8px",
                        "alignItems": "center"}),
    ], style={**T.OPTIONS_ROW, "gap": "8px"})


def _options_panel() -> html.Div:
    return html.Div([
        html.Div(_dispersion_options(), id="dispersion-options",
                 style={"display": "block"}),
        html.Div(_trend_options(), id="trend-options", style={"display": "none"}),
        html.Div(_multi_options(), id="multi-options", style={"display": "none"}),
        html.Hr(style={"borderColor": THEME["border"], "margin": "8px 0"}),
        _label_options(),
        html.Hr(style={"borderColor": THEME["border"], "margin": "8px 0"}),
        _marks_controls(),
    ], style=T.OPTIONS_PANEL)


def _stores() -> list:
    return [
        dcc.Store(id="active-view", data=DEFAULT_VIEWER),
        dcc.Store(id="sidebar-open", data=False),
        dcc.Store(id="current-file"),
        dcc.Store(id="current-table"),
        dcc.Store(id="columns-store", data=[]),
        dcc.Store(id="disp-store", data={"col": None, "fit_colors": {}}),
        # Series-list model: each curve has source/transform/name/color/scale/
        # displace, so raw + derivative + integral can coexist as separate cards.
        dcc.Store(id="trend-store", data={"x": None, "y": None, "series": []}),
        dcc.Store(id="multi-store",
                  data={"x": None, "series": [],
                        "axis_cfg": {"share_zero": True}}),
        dcc.Store(id="marks-store",
                  data={"dispersion": [], "trend": [], "multi_trend": []}),
        # Per-viewer label overrides for title / axes / legend.
        dcc.Store(id="labels-store",
                  data={k["key"]: {"title": "", "xaxis": "", "yaxis": "",
                                   "series": {}} for k in VIEWERS}),
    ]


def build_layout() -> html.Div:
    return html.Div(
        _stores() + [
            _sidebar(),
            _header(),
            _graph_area(),
            _vars_panel(),
            _options_panel(),
        ],
        style=T.PAGE,
    )
