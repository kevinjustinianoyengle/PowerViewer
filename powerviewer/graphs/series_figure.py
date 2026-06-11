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

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..config import THEME
from . import transforms
from .base import apply_labels, apply_marks, base_figure, empty_figure

# Equation-box placement -> paper-coordinate anchors (shared with the per-series
# regression overlay; merged in from the former Scatter+Regression viewer).
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


def _equation_text(name, m, b, r2) -> str:
    sign = "+" if b >= 0 else "−"
    r2_txt = "n/a" if np.isnan(r2) else f"{r2:.4f}"
    return f"{name}:  y = {m:.4g}·x {sign} {abs(b):.4g}   R² = {r2_txt}"


def configure_axis_zoom(fig: go.Figure) -> go.Figure:
    """Horizontal drag zooms X, vertical drag zooms Y (Plotly edge-drag)."""
    fig.update_layout(dragmode="zoom")
    for axis in (fig.update_xaxes, fig.update_yaxes):
        axis(fixedrange=False, showspikes=True, spikecolor=THEME["muted"],
             spikethickness=1, spikemode="across", spikedash="dot")
    return fig


def _aligned_ranges(left_ext, right_ext):
    """Return (left_range, right_range) with y=0 at the SAME fraction on both.

    Each axis keeps its own scale (so different magnitudes stay readable) but
    their zero lines line up vertically. Works whether the data is all-positive,
    all-negative or crosses zero.
    """
    def bt(ext):
        lo, hi = ext
        b, t = min(lo, 0.0), max(hi, 0.0)
        if t == b:
            t = b + 1.0
        return b, t

    bl, tl = bt(left_ext)
    br, tr = bt(right_ext)
    p = max((-bl) / (tl - bl), (-br) / (tr - br))  # shared zero fraction
    eps = 1e-9

    def rng(b, t):
        if p <= eps:                       # no negatives -> zero at bottom
            return [0.0, (t * 1.1) or 1.0]
        if p >= 1 - eps:                   # all negative -> zero at top
            return [(b * 1.1) or -1.0, 0.0]
        big = max((-b) / p, t / (1 - p)) * 1.1
        return [-p * big, (1 - p) * big]

    return rng(bl, tl), rng(br, tr)


def _combine(data, srcs, op):
    """Combine the source columns with *op* (+, -, *, /). Defaults to a sum.

    ``+`` sums all sources (backwards-compatible with old sum series); ``-``/``*``/
    ``/`` act on the first two (division guards against /0 -> NaN).
    """
    if len(srcs) < 2 or op == "+":
        return data[srcs].sum(axis=1).to_numpy()
    a = data[srcs[0]].to_numpy(dtype=float)
    b = data[srcs[1]].to_numpy(dtype=float)
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        with np.errstate(divide="ignore", invalid="ignore"):
            out = a / b
        out[~np.isfinite(out)] = np.nan
        return out
    return a + b


def _add_fit(fig, xs, y, color, name, yref, value_range):
    """Overlay a least-squares fit (line + points) for one series; return its
    equation text, or ``None`` if it can't be fitted.

    The fit uses only the samples inside ``value_range`` (the visible X window),
    so it recomputes as the user zooms. Points are drawn on the fit line so the
    predicted value at each sample is readable.
    """
    xs = pd.Series(xs).reset_index(drop=True)
    y = np.asarray(y, dtype=float)
    if value_range is not None and None not in value_range:
        lo, hi = value_range
        if pd.api.types.is_datetime64_any_dtype(xs):
            lo, hi = pd.to_datetime(lo), pd.to_datetime(hi)
        if lo > hi:
            lo, hi = hi, lo
        mask = (xs >= lo) & (xs <= hi)
        xs, y = xs[mask].reset_index(drop=True), y[mask.to_numpy()]
    if len(xs) < 2:
        return None
    xn = transforms._to_numeric_x(xs)
    finite = np.isfinite(xn) & np.isfinite(y)
    xn, y, x_plot = xn[finite], y[finite], xs[finite].to_numpy()
    if len(xn) < 2 or xn.min() == xn.max():
        return None
    m, b, r2 = _least_squares(xn, y)
    order = np.argsort(xn)
    fig.add_trace(go.Scatter(
        x=x_plot[order], y=(m * xn + b)[order], mode="lines+markers",
        line=dict(color=color, width=2, dash="solid"),
        marker=dict(color=color, size=5, symbol="circle-open"),
        name=f"{name} fit", yaxis=yref, showlegend=False,
        hovertemplate=f"{name} fit<br>x=%{{x}}<br>ŷ=%{{y:.4g}}<extra></extra>",
    ))
    return _equation_text(name, m, b, r2)


def build(
    df: Optional[pd.DataFrame],
    x_col: Optional[str],
    series: Optional[List[dict]],
    title: str,
    empty_msg: str,
    marks: Optional[list] = None,
    labels: Optional[dict] = None,
    axis_cfg: Optional[dict] = None,
    style: str = "lines",
    value_range: Optional[tuple] = None,
) -> go.Figure:
    """Draw *series* against *x_col*.

    ``axis_cfg`` (Multiple Trend) may carry ``share_zero`` plus manual
    ``lmin/lmax/rmin/rmax`` range overrides for the left/right Y axes.

    ``style`` is ``"lines"`` (connected) or ``"scatter"`` (unconnected markers).
    In **scatter** mode a series may carry ``fit=True`` to overlay its own
    least-squares regression line (with points) on its axis; ``fit_pos`` picks
    the corner of its equation/R² box. ``value_range`` ``(lo, hi)`` restricts the
    *fit* to the visible X window, so the regression recomputes as you zoom.
    """
    if df is None or not x_col or not series:
        return empty_figure(empty_msg)

    scatter = style == "scatter"
    fig = base_figure(title)
    # Track extents per axis ("left" -> primary y, "right" -> secondary y2).
    extents = {"left": [None, None], "right": [None, None]}
    plotted = False
    fits = []  # (fit_pos, equation_text, color) for on-graph boxes

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
        combined = _combine(data, srcs, s.get("op", "+"))

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
        yref = "y2" if axis == "right" else "y"
        color = s.get("color") or THEME["accent"]
        ext = extents[axis]
        col_min, col_max = float(y.min()), float(y.max())
        ext[0] = col_min if ext[0] is None else min(ext[0], col_min)
        ext[1] = col_max if ext[1] is None else max(ext[1], col_max)
        plotted = True

        fig.add_trace(go.Scatter(
            x=data[x_col], y=y,
            mode="markers" if scatter else "lines",
            marker=dict(color=color, size=6, opacity=0.7),
            line=dict(color=color, width=2),
            name=name, yaxis=yref,
            hovertemplate=f"{x_col}=%{{x}}<br>{name}=%{{y}}<extra></extra>",
        ))

        # Per-series least-squares regression (scatter mode only).
        if scatter and s.get("fit"):
            fit_color = s.get("fit_color") or color
            annot = _add_fit(fig, data[x_col], y, fit_color, name, yref,
                             value_range)
            if annot is not None:
                fits.append((s.get("fit_pos", "tl"), annot, fit_color))

    if not plotted:
        return empty_figure(f"No numeric data to plot against '{x_col}'.")

    def _autofit(ext):
        lo, hi = ext
        if lo is None or hi is None:
            return None
        span = hi - lo
        pad = span * 0.05 if span else (abs(hi) * 0.05 or 1.0)
        return [lo - pad, hi + pad]

    cfg = axis_cfg or {}
    has_left = extents["left"][0] is not None
    has_right = extents["right"][0] is not None

    left_range = _autofit(extents["left"])
    right_range = _autofit(extents["right"])

    # Shared zero: align the two axes' zero lines (only when both exist).
    if cfg.get("share_zero") and has_left and has_right:
        left_range, right_range = _aligned_ranges(extents["left"],
                                                  extents["right"])

    # Manual scale overrides (per provided bound) take precedence.
    def _override(rng, ext, lo_key, hi_key):
        if rng is None and ext[0] is None:
            return None
        base = rng or _autofit(ext) or [0.0, 1.0]
        lo = cfg.get(lo_key)
        hi = cfg.get(hi_key)
        return [lo if lo is not None else base[0],
                hi if hi is not None else base[1]]

    left_range = _override(left_range, extents["left"], "lmin", "lmax")
    right_range = _override(right_range, extents["right"], "rmin", "rmax")

    if left_range:
        fig.update_yaxes(range=left_range)

    # Add a secondary (right) Y axis only when a series is assigned to it.
    if has_right and right_range is not None:
        right_title = (labels or {}).get("yaxis2") or "value (right)"
        fig.update_layout(yaxis2=dict(
            overlaying="y", side="right", range=right_range,
            title=dict(text=right_title), showgrid=False, zeroline=False))

    fig.update_layout(xaxis_title=x_col, yaxis_title="value")
    configure_axis_zoom(fig)

    # On-graph equation/R² boxes (not in the legend). Multiple fits sharing a
    # corner are stacked so they don't overlap.
    per_corner: dict = {}
    for pos, text, color in fits:
        n = per_corner.get(pos, 0)
        per_corner[pos] = n + 1
        anchor = ANNOT_POS.get(pos, ANNOT_POS["tl"])
        down = anchor["yanchor"] == "top"
        fig.add_annotation(
            text=text, showarrow=False, align="left",
            xref="paper", yref="paper",
            font=dict(color=color, size=12),
            bgcolor="rgba(246,248,250,0.92)",
            bordercolor=color, borderwidth=1, borderpad=5,
            yshift=(-34 * n) if down else (34 * n),
            **anchor,
        )

    apply_labels(fig, labels)
    apply_marks(fig, marks)
    return fig
