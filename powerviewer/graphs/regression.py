"""Viewer 4 - Scatter + Linear Regression.

Like the single Trend but the points are **scattered, not connected**. An
optional **least-squares** best-fit line is drawn, with its **equation** and
**R²** shown as a box *on the graph* (not in the legend) whose corner is
user-selectable. The fit is **zoom-aware**: it is recomputed from only the points
inside the visible window. Derivative/integral do not apply here; marks and
labels behave like every other viewer.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..config import THEME
from . import transforms
from .base import apply_labels, apply_marks, base_figure, empty_figure, series_name

# Equation-box placement -> paper-coordinate anchors.
ANNOT_POS = {
    "tl": dict(x=0.02, y=0.98, xanchor="left", yanchor="top"),
    "tr": dict(x=0.98, y=0.98, xanchor="right", yanchor="top"),
    "bl": dict(x=0.02, y=0.04, xanchor="left", yanchor="bottom"),
    "br": dict(x=0.98, y=0.04, xanchor="right", yanchor="bottom"),
}


def _least_squares(xn: np.ndarray, y: np.ndarray):
    """Return (slope, intercept, r2) for the best line minimising squared error."""
    m, b = np.polyfit(xn, y, 1)
    y_hat = m * xn + b
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return m, b, r2


def _equation_text(m, b, r2) -> str:
    sign = "+" if b >= 0 else "−"
    r2_txt = "n/a" if np.isnan(r2) else f"{r2:.4f}"
    return f"y = {m:.4g}·x {sign} {abs(b):.4g}<br>R² = {r2_txt}"


def build_figure(
    df: Optional[pd.DataFrame],
    x_col: Optional[str],
    y_col: Optional[str],
    show_fit: bool = True,
    annot_pos: str = "tl",
    marks: Optional[list] = None,
    labels: Optional[dict] = None,
    value_range: Optional[tuple] = None,
    y_range: Optional[tuple] = None,
    color: Optional[str] = None,
    scale: float = 1.0,
    displace: float = 0.0,
) -> go.Figure:
    """Build the scatter + regression figure for *y_col* vs *x_col*.

    The Y values are transformed as ``y · scale + displace`` (matching the trend
    viewers' per-series scaling), so the fitted equation reflects what is drawn.
    """
    if df is None or x_col is None or y_col is None:
        return empty_figure(
            "Click ONE variable for the X axis, then ONE for the Y axis.\n"
            "Points are scattered; toggle a linear regression on top."
        )

    data = df[[x_col, y_col]].copy()
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col, x_col])
    if data.empty:
        return empty_figure(f"No numeric data for '{y_col}' vs '{x_col}'.")

    # Per-series scale / displacement (identity defaults).
    scale = 1.0 if scale in (None, "") else float(scale)
    displace = 0.0 if displace in (None, "") else float(displace)
    data[y_col] = data[y_col] * scale + displace
    point_color = color or THEME["accent"]

    # Restrict to the zoomed window so the regression uses only visible points.
    xs = data[x_col]
    if value_range is not None and None not in value_range:
        lo, hi = value_range
        if pd.api.types.is_datetime64_any_dtype(xs):
            lo, hi = pd.to_datetime(lo), pd.to_datetime(hi)
        if lo > hi:
            lo, hi = hi, lo
        data = data[(xs >= lo) & (xs <= hi)]
    if y_range is not None and None not in y_range:
        ylo, yhi = sorted(y_range)
        data = data[(data[y_col] >= ylo) & (data[y_col] <= yhi)]
    if data.empty:
        return empty_figure("No points in the zoomed window to fit.")

    fig = base_figure(f"Regression - {y_col} vs {x_col}")
    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col], mode="markers",
        marker=dict(color=point_color, size=6, opacity=0.65),
        name=series_name(labels, y_col, y_col),
        hovertemplate=f"{x_col}=%{{x}}<br>{y_col}=%{{y}}<extra></extra>",
    ))

    # Least-squares best-fit line + on-graph equation/R² box (not in legend).
    if show_fit and len(data) >= 2:
        xn = transforms._to_numeric_x(data[x_col])
        y = data[y_col].to_numpy(dtype=float)
        order = np.argsort(xn)
        xn_s = xn[order]
        x_orig = data[x_col].to_numpy()[order]
        if xn_s[0] != xn_s[-1]:  # need spread in X to fit a line
            m, b, r2 = _least_squares(xn, y)
            fig.add_trace(go.Scatter(
                x=[x_orig[0], x_orig[-1]],
                y=[m * xn_s[0] + b, m * xn_s[-1] + b],
                mode="lines",
                line=dict(color=THEME["x_select"], width=2.5),
                name="fit", showlegend=False, hoverinfo="skip",
            ))
            fig.add_annotation(
                text=_equation_text(m, b, r2),
                showarrow=False, align="left",
                xref="paper", yref="paper",
                font=dict(color=THEME["text"], size=13),
                bgcolor="rgba(246,248,250,0.9)",
                bordercolor=THEME["x_select"], borderwidth=1, borderpad=6,
                **ANNOT_POS.get(annot_pos, ANNOT_POS["tl"]),
            )

    fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)
    # Keep the view pinned to the zoom so refit + view stay in sync.
    if value_range is not None and None not in value_range:
        fig.update_xaxes(range=list(value_range), autorange=False)
    if y_range is not None and None not in y_range:
        fig.update_yaxes(range=list(y_range), autorange=False)

    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
