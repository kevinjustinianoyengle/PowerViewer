"""Concerns shared by every viewer: theme, marks and screenshot saving.

Keeping these here means a viewer module only has to worry about *what* to draw;
zooming (native Plotly), marks (horizontal / vertical / point) and screenshots
all behave identically across viewers.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, List, Optional

import plotly.graph_objects as go

from ..config import PLOTLY_TEMPLATE, SCREENSHOT_DIR, THEME


def base_figure(title: str = "") -> go.Figure:
    """Return an empty figure with the shared PowerViewer styling applied."""
    fig = go.Figure()
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, x=0.01, xanchor="left",
                   font=dict(color=THEME["text"], size=16)),
        paper_bgcolor=THEME["panel"],
        plot_bgcolor=THEME["bg"],
        font=dict(color=THEME["text"]),
        margin=dict(l=60, r=24, t=48, b=48),
        hovermode="closest",
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=THEME["text"])),
        uirevision="keep",  # preserve user zoom/pan across data-less updates
    )
    fig.update_xaxes(gridcolor=THEME["grid"], zerolinecolor=THEME["border"])
    fig.update_yaxes(gridcolor=THEME["grid"], zerolinecolor=THEME["border"])
    return fig


def empty_figure(message: str) -> go.Figure:
    """A placeholder figure that just shows a centred instructional message."""
    fig = base_figure()
    fig.add_annotation(
        text=message,
        x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False,
        font=dict(color=THEME["muted"], size=15),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


# --------------------------------------------------------------------------- #
# Labels: user overrides for the title, axis titles and legend (series names).
# --------------------------------------------------------------------------- #
# ``labels`` is a small dict stored per viewer:
#   {"title": str, "xaxis": str, "yaxis": str, "series": {key: new_name}}
# Each field is optional; empty strings mean "keep the default".

def series_name(labels: Optional[Dict], key: str, default: str) -> str:
    """Return the user-overridden legend name for *key*, else *default*."""
    if not labels:
        return default
    override = (labels.get("series") or {}).get(key)
    return override if override else default


def apply_labels(fig: go.Figure, labels: Optional[Dict]) -> go.Figure:
    """Apply title / axis-title overrides onto *fig* (legend handled per-trace).

    Targets the **primary** x/y axes only (via ``layout.xaxis``/``layout.yaxis``)
    so a secondary ``yaxis2`` title is not overwritten — ``update_yaxes`` would
    hit every y-axis.
    """
    if not labels:
        return fig
    if labels.get("title"):
        fig.update_layout(title_text=labels["title"])
    if labels.get("xaxis"):
        fig.layout.xaxis.title.text = labels["xaxis"]
    if labels.get("yaxis"):
        fig.layout.yaxis.title.text = labels["yaxis"]
    return fig


# --------------------------------------------------------------------------- #
# Marks: horizontal lines, vertical lines and single highlighted points.
# --------------------------------------------------------------------------- #
# A mark is a small dict so it can be stored in a dcc.Store and survive reloads:
#   {"kind": "h", "value": <y>,           "label": "..."}
#   {"kind": "v", "value": <x>,           "label": "..."}
#   {"kind": "point", "x": <x>, "y": <y>, "label": "..."}

def apply_marks(fig: go.Figure, marks: Optional[List[Dict]]) -> go.Figure:
    """Draw the user-defined marks onto *fig*.

    A mark's position may be numeric *or* a datetime string (for vertical/point
    marks on a time axis); ``_fmt`` formats either kind for the label.
    """
    if not marks:
        return fig

    def _fmt(v):
        return f"{v:g}" if isinstance(v, (int, float)) else str(v)

    for mark in marks:
        kind = mark.get("kind")
        label = mark.get("label", "")
        if kind == "h":
            fig.add_hline(
                y=mark["value"],
                line=dict(color=THEME["accent"], width=1.5, dash="dash"),
                annotation_text=label or f"y = {_fmt(mark['value'])}",
                annotation_position="right",
                annotation_font_color=THEME["accent"],
            )
        elif kind == "v":
            fig.add_vline(
                x=mark["value"],
                line=dict(color=THEME["x_select"], width=1.5, dash="dash"),
                annotation_text=label or f"x = {_fmt(mark['value'])}",
                annotation_position="top",
                annotation_font_color=THEME["x_select"],
            )
        elif kind == "point":
            fig.add_trace(go.Scatter(
                x=[mark["x"]], y=[mark["y"]],
                mode="markers+text",
                marker=dict(color=THEME["accent"], size=12, symbol="x-thin",
                            line=dict(width=2, color=THEME["accent"])),
                text=[label or f"({_fmt(mark['x'])}, {_fmt(mark['y'])})"],
                textposition="top center",
                textfont=dict(color=THEME["accent"]),
                hoverinfo="text",
                showlegend=False,
                name="mark",
            ))
    return fig


# --------------------------------------------------------------------------- #
# Screenshots saved server-side into the repository.
# --------------------------------------------------------------------------- #
def save_screenshot(fig: go.Figure, viewer_key: str,
                    width: int = 1400, height: int = 800,
                    scale: int = 2) -> Path:
    """Render *fig* to a PNG inside the screenshot folder and return its path.

    Uses Plotly's kaleido backend (pure Python install) so the image is written
    on the server and lives in the repo, instead of only downloading in-browser.
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = SCREENSHOT_DIR / f"{viewer_key}_{stamp}.png"
    fig.write_image(str(out_path), width=width, height=height, scale=scale)
    return out_path
