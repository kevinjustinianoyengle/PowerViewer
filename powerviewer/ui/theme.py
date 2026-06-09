"""Style dictionaries built from the shared THEME tokens in config.

Centralising styles here keeps the layout module readable and means the look of
the whole app can be retuned from one place.
"""

from __future__ import annotations

from ..config import THEME

FONT_STACK = "'Segoe UI', system-ui, -apple-system, sans-serif"

# --------------------------------------------------------------------------- #
# Page-level grid: header / carousel on top, graph + variables in the middle,
# options at the bottom.
# --------------------------------------------------------------------------- #
PAGE = {
    "display": "grid",
    # Variables panel reduced by 15% (260px -> 221px). Graphs are now chosen
    # from the burger sidebar, so the top carousel row is gone.
    "gridTemplateColumns": "1fr 221px",
    "gridTemplateRows": "auto 1fr auto",
    "gridTemplateAreas": "'header header' 'graph vars' 'options options'",
    "height": "100vh",
    "width": "100vw",
    "margin": "0",
    "backgroundColor": THEME["bg"],
    "color": THEME["text"],
    "fontFamily": FONT_STACK,
    "overflow": "hidden",
    "boxSizing": "border-box",
}

HEADER = {
    "gridArea": "header",
    "display": "flex",
    "alignItems": "center",
    "gap": "16px",
    "padding": "10px 18px",
    "backgroundColor": THEME["panel"],
    "borderBottom": f"1px solid {THEME['border']}",
}

TITLE = {
    "fontSize": "20px",
    "fontWeight": "700",
    "letterSpacing": "0.5px",
    "color": THEME["accent"],
    "margin": "0",
    "whiteSpace": "nowrap",
}

CAROUSEL = {
    "gridArea": "carousel",
    "display": "flex",
    "gap": "10px",
    "overflowX": "auto",
    "padding": "10px 18px",
    "backgroundColor": THEME["panel_alt"],
    "borderBottom": f"1px solid {THEME['border']}",
}


def carousel_button(active: bool) -> dict:
    return {
        "flex": "0 0 auto",
        "minWidth": "150px",
        "padding": "10px 16px",
        "borderRadius": "10px",
        "border": f"1px solid {THEME['accent'] if active else THEME['border']}",
        "backgroundColor": THEME["accent_soft"] if active else THEME["panel"],
        "color": THEME["accent"] if active else THEME["text"],
        "cursor": "pointer",
        "fontSize": "14px",
        "fontWeight": "600",
        "textAlign": "left",
        "transition": "all .15s ease",
    }


GRAPH_AREA = {
    "gridArea": "graph",
    "padding": "12px",
    "minHeight": "0",
    "minWidth": "0",
    "backgroundColor": THEME["bg"],
}

GRAPH = {"height": "100%", "width": "100%"}

VARS_PANEL = {
    "gridArea": "vars",
    "backgroundColor": THEME["panel"],
    "borderLeft": f"1px solid {THEME['border']}",
    "padding": "12px",
    "overflowY": "auto",
    "display": "flex",
    "flexDirection": "column",
    "gap": "6px",
}

VARS_TITLE = {
    "fontSize": "12px",
    "textTransform": "uppercase",
    "letterSpacing": "1px",
    "color": THEME["muted"],
    "margin": "0 0 6px 0",
}


def var_button(state: str) -> dict:
    """Style a variable button. *state* is one of: idle, x, y, disabled."""
    base = {
        "display": "block",
        "width": "100%",
        "textAlign": "left",
        "padding": "8px 10px",
        "borderRadius": "8px",
        "fontSize": "13px",
        "cursor": "pointer",
        "border": f"1px solid {THEME['border']}",
        "backgroundColor": THEME["panel_alt"],
        "color": THEME["text"],
        "transition": "all .12s ease",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    if state == "x":
        base.update(border=f"1px solid {THEME['x_select']}",
                    backgroundColor="#16291B", color=THEME["x_select"],
                    fontWeight="700")
    elif state == "y":
        base.update(border=f"1px solid {THEME['y_select']}",
                    backgroundColor=THEME["accent_soft"], color=THEME["accent"],
                    fontWeight="700")
    elif state == "disabled":
        base.update(opacity="0.35", cursor="not-allowed")
    return base


OPTIONS_PANEL = {
    "gridArea": "options",
    "backgroundColor": THEME["panel"],
    "borderTop": f"1px solid {THEME['border']}",
    "padding": "10px 18px",
    # Fixed height (not max-height): the panel never grows with its content, so
    # the graph section above keeps a constant height. Content scrolls inside.
    "height": "250px",
    "boxSizing": "border-box",
    "overflowY": "auto",
}

OPTIONS_ROW = {
    "display": "flex",
    "flexWrap": "wrap",
    "alignItems": "center",
    "gap": "14px",
}

SECTION_LABEL = {
    "fontSize": "11px",
    "textTransform": "uppercase",
    "letterSpacing": "1px",
    "color": THEME["muted"],
    "marginRight": "6px",
}

BUTTON = {
    "padding": "8px 14px",
    "borderRadius": "8px",
    "border": f"1px solid {THEME['border']}",
    "backgroundColor": THEME["panel_alt"],
    "color": THEME["text"],
    "cursor": "pointer",
    "fontSize": "13px",
    "fontWeight": "600",
}

BUTTON_ACCENT = {
    **BUTTON,
    "border": f"1px solid {THEME['accent']}",
    "backgroundColor": THEME["accent_soft"],
    "color": THEME["accent"],
}

INPUT = {
    "padding": "7px 10px",
    "borderRadius": "8px",
    "border": f"1px solid {THEME['border']}",
    "backgroundColor": THEME["bg"],
    "color": THEME["text"],
    "fontSize": "13px",
}

DROPDOWN = {"minWidth": "200px", "color": "#111"}

STATUS = {"fontSize": "12px", "color": THEME["muted"], "marginLeft": "auto"}

HELP_TEXT = {"fontSize": "12px", "color": THEME["muted"], "margin": "2px 0 10px 0"}

# --------------------------------------------------------------------------- #
# Burger button + left sidebar drawer (overlays the UI with the top z-index).
# --------------------------------------------------------------------------- #
BURGER = {
    "fontSize": "20px",
    "lineHeight": "1",
    "padding": "6px 12px",
    "borderRadius": "8px",
    "border": f"1px solid {THEME['border']}",
    "backgroundColor": THEME["panel_alt"],
    "color": THEME["accent"],
    "cursor": "pointer",
}

# Full-screen dimmer behind the open drawer.
OVERLAY = {
    "position": "fixed",
    "inset": "0",
    "backgroundColor": "rgba(0,0,0,0.45)",
    "zIndex": "998",
}


def sidebar(open_: bool) -> dict:
    return {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "height": "100vh",
        "width": "330px",
        "backgroundColor": THEME["panel"],
        "borderRight": f"1px solid {THEME['border']}",
        "boxShadow": "2px 0 18px rgba(0,0,0,0.5)",
        "zIndex": "999",
        "padding": "16px",
        "overflowY": "auto",
        "transform": "translateX(0)" if open_ else "translateX(-110%)",
        "transition": "transform .2s ease",
        "display": "flex",
        "flexDirection": "column",
        "gap": "12px",
    }


def sidebar_viewer_button(active: bool) -> dict:
    """Full-width graph-chooser button inside the sidebar."""
    s = carousel_button(active)
    s.update(width="100%", minWidth="0", marginBottom="6px",
             display="flex", alignItems="center", gap="8px")
    return s


SIDEBAR_TITLE = {
    "fontSize": "16px", "fontWeight": "700", "color": THEME["accent"],
    "margin": "0 0 4px 0",
}

FIELD_LABEL = {"fontSize": "11px", "textTransform": "uppercase",
               "letterSpacing": "1px", "color": THEME["muted"],
               "margin": "8px 0 2px 0", "display": "block"}

FIELD_INPUT = {**{
    "padding": "7px 10px", "borderRadius": "8px",
    "border": f"1px solid {THEME['border']}", "backgroundColor": THEME["bg"],
    "color": THEME["text"], "fontSize": "13px"}, "width": "100%",
    "boxSizing": "border-box"}

# --------------------------------------------------------------------------- #
# Caption under the graph (viewer title + short description).
# --------------------------------------------------------------------------- #
CAPTION = {
    "padding": "6px 4px 0 4px",
}
CAPTION_TITLE = {"fontSize": "15px", "fontWeight": "700",
                 "color": THEME["text"], "margin": "0"}
CAPTION_DESC = {"fontSize": "12px", "color": THEME["muted"],
                "margin": "2px 0 0 0"}

# --------------------------------------------------------------------------- #
# Slimmer variable list (smaller font, tighter spacing).
# --------------------------------------------------------------------------- #
VARS_PANEL_SLIM = {**VARS_PANEL, "padding": "10px 8px", "gap": "3px"}


def var_button_slim(state: str) -> dict:
    s = var_button(state)
    s.update(padding="5px 8px", fontSize="12px", borderRadius="6px")
    return s


# --------------------------------------------------------------------------- #
# Marks: added-mark list chips with delete buttons.
# --------------------------------------------------------------------------- #
MARK_CHIP = {
    "display": "inline-flex", "alignItems": "center", "gap": "10px",
    "padding": "6px 14px", "borderRadius": "16px",
    "border": f"1px solid {THEME['border']}",
    "backgroundColor": THEME["panel_alt"], "fontSize": "12.5px",
    "color": THEME["text"], "margin": "2px",
}
MARK_CHIP_TEXT = {"letterSpacing": "0.3px", "whiteSpace": "nowrap"}
MARK_DELETE = {
    "border": "none", "background": "none", "color": THEME["muted"],
    "cursor": "pointer", "fontSize": "13px", "lineHeight": "1", "padding": "0",
}
SMALL_INPUT = {
    "padding": "6px 8px", "borderRadius": "8px",
    "border": f"1px solid {THEME['border']}", "backgroundColor": THEME["bg"],
    "color": THEME["text"], "fontSize": "12px", "width": "110px",
}
