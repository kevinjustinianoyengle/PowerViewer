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


def _finite_subset(values, value_range=None) -> np.ndarray:
    """Finite values, optionally restricted to a ``(lo, hi)`` window."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if value_range is not None and None not in value_range:
        lo, hi = sorted(value_range)
        v = v[(v >= lo) & (v <= hi)]
    return v


def fit_moments(name: str, values, value_range=None):
    """Return the fitted distribution's key moments as ``[(label, text), ...]``.

    These are the meaningful parameters per distribution (e.g. mean & std for
    normal, the spread for uniform). Filtering matches :func:`build_figure`
    (finite + optional zoom window) so the numbers describe what is on screen.
    Returns ``[]`` when nothing can be fitted.
    """
    if name not in DISTRIBUTIONS:
        return []
    v = _finite_subset(values, value_range)
    if v.size == 0:
        return []
    params = _fit_params(name, v)
    if params is None:
        return []

    def f(x):
        return f"{x:.4g}"

    out = [("n", str(v.size))]
    if name == "normal":
        loc, scale = params
        out += [("Mean μ", f(loc)), ("Std σ", f(scale))]
    elif name == "uniform":
        loc, scale = params
        out += [("Min a", f(loc)), ("Max b", f(loc + scale)),
                ("Spread b−a", f(scale))]
    elif name == "lognormal":
        shape, loc, scale = params  # shape = σ of log; scale = exp(μ)
        mean = loc + scale * np.exp(shape ** 2 / 2)
        var = (scale ** 2) * (np.exp(shape ** 2) - 1) * np.exp(shape ** 2)
        out += [("Median", f(loc + scale)), ("Mean", f(mean)),
                ("Std", f(np.sqrt(var))), ("σ(log)", f(shape))]
    elif name == "exponential":
        loc, scale = params
        out += [("Mean", f(loc + scale)),
                ("Rate λ", f(1.0 / scale) if scale else "—"),
                ("Std", f(scale))]
    return out


def build_figure(
    values: Optional[np.ndarray],
    column: Optional[str],
    distributions: Optional[List[str]] = None,
    bins: int = 40,
    marks: Optional[list] = None,
    fit_colors: Optional[Dict[str, str]] = None,
    labels: Optional[dict] = None,
    times: Optional[np.ndarray] = None,
    value_range: Optional[tuple] = None,
) -> go.Figure:
    """Build the 1D dispersion figure.

    *times* (optional) is the per-row timestamp aligned with *values*; when
    present, hovering a sample shows the **time** of that sample.

    *value_range* ``(lo, hi)`` (optional) restricts the analysis to that X window
    — the histogram is re-binned into ``bins`` bars across it and the
    distribution is re-fitted to just those samples, so zooming "recomputes" the
    dispersion for the visible section.
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

    # Restrict to the zoomed window: re-bin and re-fit on this subset only.
    if value_range is not None:
        lo, hi = value_range
        if lo is not None and hi is not None:
            if hi < lo:
                lo, hi = hi, lo
            sub = (values >= lo) & (values <= hi)
            values = values[sub]
            if times is not None:
                times = times[sub]
            if values.size == 0:
                return empty_figure(f"No '{column}' samples in the zoomed "
                                    f"range [{lo:g}, {hi:g}].")

    # Hover for the sample points: show the timestamp when we have one.
    if times is not None:
        sample_hover = ("time=%{customdata|%Y-%m-%d %H:%M:%S}"
                        "<br>value=%{x:.4g}<extra></extra>")
    else:
        sample_hover = "value=%{x}<extra>sample</extra>"

    distributions = distributions or []
    fit_colors = fit_colors or {}

    fig = base_figure(f"1D Dispersion - {column}")

    # Binning window: the zoomed range if given, else the data span. Using
    # explicit xbins spreads exactly ``bins`` bars across the window, so a zoom
    # rearranges the same number of bars over the visible section.
    win_lo, win_hi = float(values.min()), float(values.max())
    if value_range is not None and None not in value_range:
        win_lo, win_hi = sorted(value_range)
    span = win_hi - win_lo
    xbins = (dict(start=win_lo, end=win_hi, size=span / int(bins))
             if span > 0 else None)

    # Density histogram: the vertical axis = how often values appear.
    fig.add_trace(go.Histogram(
        x=values,
        xbins=xbins,
        nbinsx=None if xbins else int(bins),
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
    # Keep the view pinned to the zoomed window (Y auto-fits to the re-binned
    # density). Without this the freshly-built figure would reset to full range.
    if value_range is not None and None not in value_range:
        fig.update_xaxes(range=[win_lo, win_hi], autorange=False)

    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
