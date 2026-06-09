"""Numerical transforms shared by the Trend viewers: derivative and integral.

Kept separate so both Trend and Multiple Trend apply identical maths. The
integral is the *cumulative* integral plotted as a curve (not a shaded area);
its total value is returned so callers can surface it in the legend/label.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy import integrate

# Transform keys used across the UI and stores.
NONE = "none"
DERIVATIVE = "derivative"
INTEGRAL = "integral"

LABELS = {NONE: "Raw", DERIVATIVE: "d/dx", INTEGRAL: "∫ dx"}


def _to_numeric_x(x: pd.Series) -> np.ndarray:
    """Return X as a float array suitable for differentiation/integration.

    Datetime axes are converted to seconds; anything non-numeric falls back to
    the sample index so a transform is still possible.
    """
    if pd.api.types.is_datetime64_any_dtype(x):
        # Normalise to nanoseconds since epoch, then to seconds (works across
        # datetime64 units; Series.view was removed in pandas 3.0).
        ns = x.to_numpy().astype("datetime64[ns]").astype("int64")
        return ns / 1e9
    num = pd.to_numeric(x, errors="coerce")
    if num.isna().all():
        return np.arange(len(x), dtype=float)
    return num.to_numpy(dtype=float)


def apply_transform(
    x: pd.Series, y: np.ndarray, kind: str
) -> Tuple[np.ndarray, Optional[float]]:
    """Apply *kind* to (x, y).

    Returns ``(y_transformed, total)`` where ``total`` is the integral's total
    value for ``INTEGRAL`` (and ``None`` otherwise). ``y`` is returned unchanged
    for ``NONE`` or unknown kinds.
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
        cumulative = integrate.cumulative_trapezoid(y, xv, initial=0.0)
        total = float(integrate.trapezoid(y, xv))
        return cumulative, total

    return np.asarray(y, dtype=float), None
