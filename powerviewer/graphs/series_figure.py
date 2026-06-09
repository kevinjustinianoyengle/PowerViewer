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
    y_min = y_max = None
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

        col_min, col_max = float(y.min()), float(y.max())
        y_min = col_min if y_min is None else min(y_min, col_min)
        y_max = col_max if y_max is None else max(y_max, col_max)
        plotted = True

        fig.add_trace(go.Scatter(
            x=data[x_col], y=y, mode="lines",
            line=dict(color=s.get("color") or THEME["accent"], width=2),
            name=name,
            hovertemplate=f"{x_col}=%{{x}}<br>{name}=%{{y}}<extra></extra>",
        ))

    if not plotted:
        return empty_figure(f"No numeric data to plot against '{x_col}'.")

    if y_min is not None and y_max is not None:
        span = y_max - y_min
        pad = span * 0.05 if span else (abs(y_max) * 0.05 or 1.0)
        fig.update_yaxes(range=[y_min - pad, y_max + pad])

    fig.update_layout(xaxis_title=x_col, yaxis_title="value")
    configure_axis_zoom(fig)
    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
