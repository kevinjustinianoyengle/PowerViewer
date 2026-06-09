"""Shared renderer for series cards (used by both trend viewers).

Each card exposes the same options for one curve: an **editable name**, a
**colour**, a **scale**, a **displacement**, buttons to **add a derivative or
integral** of that series' source column (as a brand-new series), and a
**delete**. Pattern-matching component IDs are namespaced by ``prefix`` so the
Trend ("tr") and Multiple Trend ("mt") viewers keep independent callbacks.
"""

from __future__ import annotations

from typing import List

from dash import dcc, html

from ..config import ORANGE_PALETTE, THEME

COLOR_CHOICES = ORANGE_PALETTE + ["#FF3B30", "#FFD60A", "#E6EDF3", "#58A6FF",
                                  "#3FB950", "#BC8CFF"]

_BADGE = {"none": "raw", "derivative": "d/dx", "integral": "∫"}
_NUM = {"width": "60px", "padding": "5px", "borderRadius": "6px",
        "border": f"1px solid {THEME['border']}", "backgroundColor": THEME["bg"],
        "color": THEME["text"], "fontSize": "12px"}
_MINI = {"border": f"1px solid {THEME['border']}", "borderRadius": "6px",
         "backgroundColor": THEME["panel"], "color": THEME["accent"],
         "cursor": "pointer", "fontSize": "11px", "padding": "3px 6px",
         "fontWeight": "700"}


def _swatch_option(c: str) -> dict:
    return {"label": html.Div([
        html.Span(style={"display": "inline-block", "width": "12px",
                         "height": "12px", "borderRadius": "3px",
                         "backgroundColor": c, "marginRight": "6px",
                         "border": f"1px solid {THEME['border']}"}),
        html.Span(c, style={"fontSize": "11px"})],
        style={"display": "flex", "alignItems": "center"}), "value": c}


def render_series_cards(series: List[dict], prefix: str):
    """Return a list of card Divs for *series* with ``prefix``-namespaced ids."""
    if not series:
        return html.Span("Select Y variables to configure their curves.",
                         style={"color": THEME["muted"], "fontSize": "12px"})
    cards = []
    for s in series:
        sid = s["id"]
        current = s.get("color") or THEME["accent"]
        choices = (COLOR_CHOICES if current in COLOR_CHOICES
                   else [current] + COLOR_CHOICES)
        kind = s.get("transform", "none")
        is_sum = len(s.get("sources") or []) > 1
        badge = "Σ" if (is_sum and kind == "none") else _BADGE.get(kind, "raw")
        cards.append(html.Div([
            html.Span(badge,
                      style={"fontSize": "10px", "fontWeight": "700",
                             "color": THEME["accent"],
                             "backgroundColor": THEME["accent_soft"],
                             "padding": "2px 6px", "borderRadius": "6px"}),
            dcc.Input(id={"type": f"{prefix}-name", "index": sid}, type="text",
                      value=s.get("name", ""), debounce=True, placeholder="name",
                      style={"width": "92px", "padding": "5px",
                             "borderRadius": "6px",
                             "border": f"1px solid {THEME['border']}",
                             "backgroundColor": THEME["bg"],
                             "color": THEME["text"], "fontSize": "12px"}),
            dcc.Dropdown(id={"type": f"{prefix}-color", "index": sid},
                         options=[_swatch_option(c) for c in choices],
                         value=current, clearable=False, searchable=False,
                         style={"width": "108px", "color": "#111",
                                "fontSize": "11px"}),
            html.Span("×", style={"color": THEME["muted"]}),
            dcc.Input(id={"type": f"{prefix}-scale", "index": sid},
                      type="number", value=s.get("scale", 1.0), step="any",
                      style=_NUM),
            html.Span("+", style={"color": THEME["muted"]}),
            dcc.Input(id={"type": f"{prefix}-displace", "index": sid},
                      type="number", value=s.get("displace", 0.0), step="any",
                      style=_NUM),
            html.Button("+d/dx", id={"type": f"{prefix}-add-d", "index": sid},
                        n_clicks=0, title="Add derivative", style=_MINI),
            html.Button("+∫", id={"type": f"{prefix}-add-i", "index": sid},
                        n_clicks=0, title="Add integral", style=_MINI),
            html.Button("✕", id={"type": f"{prefix}-del", "index": sid},
                        n_clicks=0, title="Delete series",
                        style={**_MINI, "color": THEME["muted"]}),
        ], style={"display": "flex", "alignItems": "center", "gap": "5px",
                  "padding": "5px 8px", "borderRadius": "8px",
                  "backgroundColor": THEME["panel_alt"],
                  "border": f"1px solid {THEME['border']}"}))
    return cards
