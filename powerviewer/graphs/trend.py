"""Viewer 2 - Trend.

A value-versus-domain plot (e.g. voltage vs time) for a single chosen Y against
a single X. On top of the raw Y you can overlay its **derivative** and/or
**cumulative integral** simultaneously - each is just another *series* (see
:mod:`powerviewer.graphs.series_figure`) with its own editable name, colour,
scale and displacement.

Axis-wise zoom: dragging horizontally zooms X, vertically zooms Y.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go

from ..config import THEME
from . import series_figure
from .base import empty_figure

# Re-exported for callers that configured zoom directly.
configure_axis_zoom = series_figure.configure_axis_zoom


def raw_series(y_col: str) -> dict:
    """A default raw series for *y_col*."""
    return {"id": "raw", "source": y_col, "transform": "none",
            "name": y_col, "color": THEME["accent"], "scale": 1.0,
            "displace": 0.0}


def build_figure(
    df: Optional[pd.DataFrame],
    x_col: Optional[str],
    y_col: Optional[str],
    series: Optional[List[dict]] = None,
    marks: Optional[list] = None,
    labels: Optional[dict] = None,
) -> go.Figure:
    """Build the trend figure for *x_col* vs *y_col* (+ any overlay series)."""
    if df is None or x_col is None or y_col is None:
        return empty_figure(
            "Click ONE variable for the X axis, then ONE for the Y axis.\n"
            "First click = X, second click = Y."
        )
    if not series:
        series = [raw_series(y_col)]
    return series_figure.build(
        df, x_col, series,
        title=f"Trend - {y_col} vs {x_col}",
        empty_msg=f"No numeric data for '{y_col}' vs '{x_col}'.",
        marks=marks, labels=labels,
    )
