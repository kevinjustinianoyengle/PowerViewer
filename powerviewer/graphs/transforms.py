"""Numerical transforms shared by the Trend viewers: derivative and integral.

Kept separate so both Trend and Multiple Trend apply identical maths. The
integral is the *cumulative* integral plotted as a curve (not a shaded area);
its total value is returned so callers can surface it in the legend/label.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

# Transform keys used across the UI and stores.
NONE = "none"
DERIVATIVE = "derivative"
INTEGRAL = "integral"

LABELS = {NONE: "Raw", DERIVATIVE: "d/dx", INTEGRAL: "∫ dx"}

# Cumulative-integral rules (Riemann sums against real time).
INTEGRAL_METHODS = ("trapezoid", "front", "back")


# For a datetime X axis the transforms use elapsed time in HOURS, so that on
# time-series data the integral of e.g. power (kW) is energy (kW·h) and the
# derivative is a per-hour rate. (Change _NS_PER_UNIT to 1e9 for seconds.)
_NS_PER_UNIT = 3.6e12  # nanoseconds in one hour


def _to_numeric_x(x: pd.Series) -> np.ndarray:
    """Return X as a float array suitable for differentiation/integration.

    Datetime axes are converted to **elapsed hours from the first sample**
    (NaT-safe: missing timestamps become NaN, not a huge sentinel). Non-numeric,
    non-datetime axes fall back to the row index so a transform is still possible.
    The actual (possibly non-uniform) spacing between timestamps is preserved, so
    np.gradient / cumulative_trapezoid integrate against real time.
    """
    xs = x if isinstance(x, pd.Series) else pd.Series(x)
    if pd.api.types.is_datetime64_any_dtype(xs):
        # datetime64 -> float ns turns NaT into NaN (astype to int would give a
        # huge sentinel and corrupt the maths).
        ns = xs.to_numpy().astype("datetime64[ns]").astype("float64")
        if np.isnan(ns).all():
            return np.arange(len(xs), dtype=float)
        return (ns - np.nanmin(ns)) / _NS_PER_UNIT
    num = pd.to_numeric(xs, errors="coerce")
    if num.isna().all():
        return np.arange(len(xs), dtype=float)
    return num.to_numpy(dtype=float)


def apply_transform(
    x: pd.Series, y: np.ndarray, kind: str, method: str = "trapezoid"
) -> Tuple[np.ndarray, Optional[float]]:
    """Apply *kind* to (x, y).

    Returns ``(y_transformed, total)`` where ``total`` is the integral's total
    value for ``INTEGRAL`` (and ``None`` otherwise). ``y`` is returned unchanged
    for ``NONE`` or unknown kinds.

    The cumulative integral integrates against **elapsed hours** (see
    ``_to_numeric_x``), so for minute-resolution data each step contributes
    ``y · (1/60)`` — i.e. power → energy. *method* selects the rule:
    ``"trapezoid"`` (default), ``"front"`` (left/forward rectangles, value at the
    start of each interval) or ``"back"`` (right/backward rectangles).
    """
    if kind == DERIVATIVE:
        xv = _to_numeric_x(x)
        y = np.asarray(y, dtype=float)
        if xv.size < 2:
            return y, None
        return np.gradient(y, xv), None

    if kind == INTEGRAL:
        xv = _to_numeric_x(x)
        y = np.asarray(y, dtype=float)
        if xv.size < 2:
            return np.zeros_like(y), 0.0
        dx = np.diff(xv)
        m = (method or "trapezoid").lower()
        if m == "front":          # left rectangle: y at the start of each step
            incr = y[:-1] * dx
        elif m == "back":         # right rectangle: y at the end of each step
            incr = y[1:] * dx
        else:                     # trapezoid
            incr = 0.5 * (y[:-1] + y[1:]) * dx
        incr = np.nan_to_num(incr, nan=0.0)
        cumulative = np.concatenate([[0.0], np.cumsum(incr)])
        total = float(np.sum(incr))
        return cumulative, total

    return np.asarray(y, dtype=float), None
