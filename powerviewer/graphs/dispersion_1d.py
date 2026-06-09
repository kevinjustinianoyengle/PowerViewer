"""Viewer 1 - 1D Dispersion.

Takes a *single* variable. Its values spread along the X axis while the vertical
axis lifts the 1D cloud into 2D by showing its statistical distribution
(a density histogram). Optional theoretical distributions (uniform / normal /
log-normal / exponential) are fitted to the data on the fly and overlaid only
when selected; their colours are user-editable.

When a distribution is selected the raw samples are scattered *under* that fitted
curve (each point at a random height between 0 and the curve), so the silhouette
of the point cloud mirrors the chosen distribution - a quick visual goodness-of-
fit. With no distribution selected the samples sit as a jittered strip below 0.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go
from scipy import stats

from ..config import THEME
from .base import apply_labels, apply_marks, base_figure, empty_figure, series_name

# Distribution key -> (display label, scipy distribution, positive-only?)
DISTRIBUTIONS = {
    "uniform": ("Uniform", stats.uniform, False),
    "normal": ("Normal", stats.norm, False),
    "lognormal": ("Log-normal", stats.lognorm, True),
    "exponential": ("Exponential", stats.expon, False),
}

# Default fit-curve colours (overridable per distribution via ``fit_colors``).
DEFAULT_FIT_COLORS = {
    "uniform": "#58A6FF",
    "normal": "#3FB950",
    "lognormal": "#BC8CFF",
    "exponential": "#FF7A00",
}


def _fit_params(name: str, values: np.ndarray):
    """Fit *name* to *values*; return scipy params tuple or None."""
    _, dist, positive_only = DISTRIBUTIONS[name]
    data = values[values > 0] if positive_only else values
    if positive_only and data.size < 2:
        return None
    try:
        return dist.fit(data)
    except Exception:  # noqa: BLE001 - fail soft, just skip the overlay
        return None


def build_figure(
    values: Optional[np.ndarray],
    column: Optional[str],
    distributions: Optional[List[str]] = None,
    bins: int = 40,
    marks: Optional[list] = None,
    fit_colors: Optional[Dict[str, str]] = None,
    labels: Optional[dict] = None,
    times: Optional[np.ndarray] = None,
) -> go.Figure:
    """Build the 1D dispersion figure.

    *times* (optional) is the per-row timestamp aligned with *values*; when
    present, hovering a sample shows the **time** of that sample.
    """
    if values is None or column is None:
        return empty_figure("Select ONE variable on the right to view its "
                            "1D dispersion.")

    values = np.asarray(values, dtype=float)
    mask = np.isfinite(values)
    values = values[mask]
    if times is not None:
        times = np.asarray(times)[mask]
    if values.size == 0:
        return empty_figure(f"'{column}' has no numeric values to plot.")

    # Hover for the sample points: show the timestamp when we have one.
    if times is not None:
        sample_hover = ("time=%{customdata|%Y-%m-%d %H:%M:%S}"
                        "<br>value=%{x:.4g}<extra></extra>")
    else:
        sample_hover = "value=%{x}<extra>sample</extra>"

    distributions = distributions or []
    fit_colors = fit_colors or {}

    fig = base_figure(f"1D Dispersion - {column}")

    # Density histogram: the vertical axis = how often values appear.
    fig.add_trace(go.Histogram(
        x=values,
        nbinsx=int(bins),
        histnorm="probability density",
        marker=dict(color=THEME["accent"], opacity=0.45,
                    line=dict(color=THEME["border"], width=1)),
        name=series_name(labels, column, column),
        hovertemplate="value=%{x}<br>density=%{y:.4f}<extra></extra>",
    ))

    rng = np.random.default_rng(0)

    # Fitted distribution overlays.
    x_grid = np.linspace(values.min(), values.max(), 400)
    primary = distributions[0] if distributions else None
    for name in distributions:
        if name not in DISTRIBUTIONS:
            continue
        params = _fit_params(name, values)
        if params is None:
            continue
        _, dist, _ = DISTRIBUTIONS[name]
        pdf = dist.pdf(x_grid, *params)
        color = fit_colors.get(name) or DEFAULT_FIT_COLORS.get(name, THEME["text"])
        fig.add_trace(go.Scatter(
            x=x_grid, y=pdf, mode="lines",
            line=dict(color=color, width=2.5),
            name=f"{DISTRIBUTIONS[name][0]} fit",
            hovertemplate="value=%{x}<br>pdf=%{y:.4f}<extra>"
                          + DISTRIBUTIONS[name][0] + "</extra>",
        ))

    # Samples: scattered UNDER the primary fitted curve, else a strip below 0.
    if primary and _fit_params(primary, values) is not None:
        params = _fit_params(primary, values)
        _, dist, _ = DISTRIBUTIONS[primary]
        pdf_at = dist.pdf(values, *params)
        pdf_at = np.nan_to_num(pdf_at, nan=0.0, posinf=0.0, neginf=0.0)
        # Uniform height in [0, pdf] -> point density fills the area under curve.
        y_pts = rng.uniform(0.0, np.clip(pdf_at, 0, None))
        color = (fit_colors.get(primary)
                 or DEFAULT_FIT_COLORS.get(primary, THEME["accent"]))
        fig.add_trace(go.Scatter(
            x=values, y=y_pts, mode="markers",
            marker=dict(color=color, size=4, opacity=0.45),
            name="samples", customdata=times,
            hovertemplate=sample_hover,
        ))
        fig.update_layout(yaxis2=dict(overlaying="y", visible=False))
    else:
        jitter = rng.uniform(0, 1, size=values.size)
        fig.add_trace(go.Scatter(
            x=values,
            y=-0.06 * np.ones_like(values) - 0.04 * jitter,
            mode="markers",
            marker=dict(color=THEME["muted"], size=5, opacity=0.5),
            name="samples", yaxis="y2", customdata=times,
            hovertemplate=sample_hover,
        ))
        fig.update_layout(yaxis2=dict(overlaying="y", visible=False,
                                      range=[-0.15, 1]))

    fig.update_layout(bargap=0.02, xaxis_title=column,
                      yaxis_title="probability density")
    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
