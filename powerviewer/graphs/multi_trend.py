"""Viewer 3 - Multiple Trend.

ONE X variable and a **list of series** (see
:mod:`powerviewer.graphs.series_figure`). Each Y variable adds a raw series, and
its derivative / cumulative integral can be added as further series - every
series is an independent curve with its own editable name, orange-tone colour,
scale factor and displacement. The Y axis auto-fits to the displayed values and
axis-wise zoom affects all lines.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go

from . import series_figure


def build_figure(
    df: Optional[pd.DataFrame],
    x_col: Optional[str],
    series: Optional[List[dict]],
    marks: Optional[list] = None,
    labels: Optional[dict] = None,
    axis_cfg: Optional[dict] = None,
) -> go.Figure:
    """Build the multi-line trend figure from *series*."""
    from .base import empty_figure
    if df is None or not x_col or not series:
        return empty_figure(
            "Click ONE variable for the X axis, then add any number of Y "
            "variables. Each becomes its own line; add d/dx or ∫ on top."
        )
    return series_figure.build(
        df, x_col, series,
        title=f"Multiple Trend vs {x_col}",
        empty_msg=f"No numeric data to plot against '{x_col}'.",
        marks=marks, labels=labels, axis_cfg=axis_cfg,
    )
