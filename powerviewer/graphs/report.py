"""Report-only series operations (kept fully separate from the viewers).

This module is intentionally **decoupled** so report-specific maths can grow here
(statistics, summaries, …) without touching the interactive viewers. Today it
holds a single operation used to build the energy report:

``break_to_zero`` — for a storage *energy* curve that charges then discharges,
split the curve at a chosen **break time** (an X-axis instant) and re-shape the
**discharge half** so it ends at ``Y = 0`` and is *inverted* to read as a
depletion (remaining energy falling to zero).

It is a pure NumPy/pandas function (no Dash / Plotly), so it is trivially
unit-testable and reusable by any future report builder.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def break_index(x, break_time) -> Optional[int]:
    """Index of the first sample at/after *break_time* on the X axis.

    *break_time* is a datetime string (``YYYY-MM-DD HH:MM``, parsed day-first) for
    a datetime axis, or a number for a numeric axis. Returns ``None`` when it
    can't be parsed or no sample falls at/after it.
    """
    if break_time is None or (isinstance(break_time, str)
                              and not break_time.strip()):
        return None
    xs = pd.Series(x).reset_index(drop=True)
    if pd.api.types.is_datetime64_any_dtype(xs):
        bt = pd.to_datetime(break_time, dayfirst=True, errors="coerce")
        if pd.isna(bt):
            return None
        mask = xs >= bt
    else:
        try:
            bt = float(break_time)
        except (TypeError, ValueError):
            return None
        mask = pd.to_numeric(xs, errors="coerce") >= bt
    idx = np.where(mask.to_numpy())[0]
    return int(idx[0]) if idx.size else None


def break_to_zero(y, x, break_time):
    """Break *y* at *break_time* (an X instant) and re-shape the discharge half.

    The **charge half** (before the break time) is left untouched. The
    **discharge half** (from the break onward) is replaced by ``y_last - y`` so
    that:

    * its **last point lands on Y = 0** (``y_last - y_last == 0``); and
    * it is **inverted** — what was a curve rising back toward zero becomes one
      *falling* to zero, i.e. it reads as the stored energy depleting.

    Returns *y* unchanged when there is no break time or it can't be located.
    Pure function; *x* and *y* must be in the same (time-sorted) order.
    """
    y = np.asarray(y, dtype=float)
    if break_time is None or y.size < 2:
        return y
    k = break_index(x, break_time)
    if k is None:
        return y
    finite = np.where(np.isfinite(y))[0]
    if finite.size < 2:
        return y
    last = y[finite[-1]]
    out = y.copy()
    out[k:] = last - y[k:]
    return out
