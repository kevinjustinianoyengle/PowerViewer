"""Shared figure builder for the trend-style viewers.

Both Trend and Multiple Trend draw a **list of series**. A series is a small
dict describing one curve:

    {"id", "source": column, "transform": none|derivative|integral,
     "name": str, "color": hex, "scale": float, "displace": float}

So a derivative or integral is just another series over the same source column
with its own editable name / colour / scale / displacement, and Raw + d/dx + ∫
can all appear at the same time. Applied per series in order
*transform → scale → displacement*; the Y axis auto-fits to the displayed values.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go

from ..config import THEME
from . import transforms
from .base import apply_labels, apply_marks, base_figure, empty_figure


def configure_axis_zoom(fig: go.Figure) -> go.Figure:
    """Horizontal drag zooms X, vertical drag zooms Y (Plotly edge-drag)."""
    fig.update_layout(dragmode="zoom")
    for axis in (fig.update_xaxes, fig.update_yaxes):
        axis(fixedrange=False, showspikes=True, spikecolor=THEME["muted"],
             spikethickness=1, spikemode="across", spikedash="dot")
    return fig


def build(
    df: Optional[pd.DataFrame],
    x_col: Optional[str],
    series: Optional[List[dict]],
    title: str,
    empty_msg: str,
    marks: Optional[list] = None,
    labels: Optional[dict] = None,
) -> go.Figure:
    """Draw *series* against *x_col*."""
    if df is None or not x_col or not series:
        return empty_figure(empty_msg)

    fig = base_figure(title)
    # Track extents per axis ("left" -> primary y, "right" -> secondary y2).
    extents = {"left": [None, None], "right": [None, None]}
    plotted = False

    for s in series:
        # A series draws one column, or the row-wise SUM of several columns
        # (``sources``) — e.g. the sum of two trend lines.
        srcs = s.get("sources") or ([s["source"]] if s.get("source") else [])
        srcs = [c for c in srcs if c in df.columns]
        if not srcs:
            continue
        data = df[[x_col, *srcs]].copy()
        for c in srcs:
            data[c] = pd.to_numeric(data[c], errors="coerce")
        data = data.dropna(subset=[*srcs, x_col]).sort_values(x_col)
        if data.empty:
            continue
        combined = data[srcs].sum(axis=1).to_numpy()

        kind = s.get("transform", transforms.NONE)
        y_t, total = transforms.apply_transform(data[x_col], combined, kind)
        scale = float(s.get("scale", 1.0) or 1.0)
        shift = float(s.get("displace", 0.0) or 0.0)
        y = y_t * scale + shift

        name = s.get("name") or " + ".join(srcs)
        if kind == transforms.INTEGRAL and total is not None:
            # The integral's total value is its curve endpoint; surface it.
            name = f"{name} [∫={total:.3g}]"

        axis = "right" if s.get("axis") == "right" else "left"
        ext = extents[axis]
        col_min, col_max = float(y.min()), float(y.max())
        ext[0] = col_min if ext[0] is None else min(ext[0], col_min)
        ext[1] = col_max if ext[1] is None else max(ext[1], col_max)
        plotted = True

        fig.add_trace(go.Scatter(
            x=data[x_col], y=y, mode="lines",
            line=dict(color=s.get("color") or THEME["accent"], width=2),
            name=name,
            yaxis="y2" if axis == "right" else "y",
            hovertemplate=f"{x_col}=%{{x}}<br>{name}=%{{y}}<extra></extra>",
        ))

    if not plotted:
        return empty_figure(f"No numeric data to plot against '{x_col}'.")

    def _range(ext):
        lo, hi = ext
        if lo is None or hi is None:
            return None
        span = hi - lo
        pad = span * 0.05 if span else (abs(hi) * 0.05 or 1.0)
        return [lo - pad, hi + pad]

    left_range = _range(extents["left"])
    if left_range:
        fig.update_yaxes(range=left_range)

    # Add a secondary (right) Y axis only when a series is assigned to it.
    right_range = _range(extents["right"])
    if right_range is not None:
        fig.update_layout(yaxis2=dict(
            overlaying="y", side="right", range=right_range,
            title=dict(text="value (right)"),
            showgrid=False, zeroline=False))

    fig.update_layout(xaxis_title=x_col, yaxis_title="value")
    configure_axis_zoom(fig)
    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
