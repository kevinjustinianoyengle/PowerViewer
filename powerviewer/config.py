"""Central configuration: filesystem paths, palettes and viewer registry.

Everything that other modules need to agree on lives here so the rest of the
codebase stays decoupled. Paths are resolved relative to the repository root and
the required folders are created on first run by :func:`ensure_folders`.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Environment (.env) loading
# --------------------------------------------------------------------------- #
# The repository root is the parent of the ``powerviewer`` package directory.
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local ``.env`` (if python-dotenv is installed). This is
# optional: without it, plain OS environment variables still work and the
# built-in defaults below apply, so the app runs out of the box.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except Exception:  # noqa: BLE001 - dotenv missing or unreadable: use defaults
    pass


def _env_dir(var: str, default: Path) -> Path:
    """Return a Path from env var *var* if set and non-empty, else *default*."""
    value = os.environ.get(var, "").strip()
    return Path(value).expanduser() if value else default


# --------------------------------------------------------------------------- #
# Filesystem layout
# --------------------------------------------------------------------------- #
# Folder where the user drops the source data (.xlsx / .csv / .db).
DATA_DIR = _env_dir("POWERVIEWER_DATA_DIR", ROOT_DIR / "1. Data")

# Folder where saved screenshots are written (committed with the repo).
SCREENSHOT_DIR = _env_dir("POWERVIEWER_SCREENSHOT_DIR", ROOT_DIR / "2. Screenshots")

# File extensions we know how to parse.
SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls", ".db", ".sqlite", ".sqlite3")


def ensure_folders() -> None:
    """Create the data and screenshot folders if they do not yet exist.

    Called once at start-up so a fresh checkout becomes usable immediately:
    the folders appear and the UI prompts the user to drop in a data file.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Viewer registry
# --------------------------------------------------------------------------- #
# Each viewer is identified by a stable key. The carousel at the top of the UI
# is generated from this list, so registering a new viewer here (plus its graph
# and callback modules) is all that is needed to surface it.
VIEWERS = [
    {
        "key": "dispersion",
        "label": "1D Dispersion",
        "icon": "●",  # ●
        "help": "Pick ONE variable. Its values spread on X; the vertical "
                "axis shows the statistical distribution. Overlay theoretical "
                "fits (uniform / normal / log-normal / exponential).",
    },
    {
        "key": "trend",
        "label": "Trend",
        "icon": "↗",  # ↗
        "help": "Pick TWO variables. First click = X axis, second click = Y "
                "axis. Use Swap to exchange them. Drag horizontally to zoom X, "
                "vertically to zoom Y.",
    },
    {
        "key": "multi_trend",
        "label": "Multiple Trend",
        "icon": "≡",  # ≡
        "help": "Pick ONE X variable, then any number of Y variables. Each "
                "line gets an orange tone you can recolour and a scale factor; "
                "the axes auto-fit dynamically.",
    },
]

DEFAULT_VIEWER = VIEWERS[0]["key"]


# --------------------------------------------------------------------------- #
# Colour palette
# --------------------------------------------------------------------------- #
# Default palette for the Multiple Trend viewer: a ramp of orange tones.
ORANGE_PALETTE = [
    "#FF7A00",
    "#FF9A3D",
    "#FFB066",
    "#E8590C",
    "#FFC58C",
    "#D9480F",
    "#FFD8A8",
    "#C24B00",
    "#FF8C42",
    "#B34700",
]


def palette_color(index: int) -> str:
    """Return an orange tone for the *index*-th trend, cycling if needed."""
    return ORANGE_PALETTE[index % len(ORANGE_PALETTE)]


# Distinct (blue/teal) palette for series moved to the SECONDARY (right) Y axis,
# so it is obvious at a glance which scale a trend belongs to.
SECONDARY_PALETTE = [
    "#1F6FEB",
    "#3FB7C4",
    "#5AC8FA",
    "#1A7F8E",
    "#7AA2F7",
    "#2D9CDB",
    "#0E7490",
    "#56B6C2",
]


def secondary_color(index: int) -> str:
    """Return a blue/teal tone for the *index*-th right-axis trend."""
    return SECONDARY_PALETTE[index % len(SECONDARY_PALETTE)]


# --------------------------------------------------------------------------- #
# Theme tokens (kept here so graphs and UI share one source of truth)
# --------------------------------------------------------------------------- #
THEME = {
    "bg": "#FFFFFF",         # plot/background base
    "panel": "#F6F8FA",      # panels (header, sidebar, options, vars)
    "panel_alt": "#EDF1F5",  # cards, buttons, list items
    "border": "#D0D7DE",
    "text": "#1F2328",       # primary (dark) text on light surfaces
    "muted": "#656D76",
    "accent": "#E8590C",     # orange accent (readable on light)
    "accent_soft": "#FFE8D5",
    "x_select": "#1A7F37",   # colour used to flag the chosen X variable
    "y_select": "#E8590C",   # colour used to flag the chosen Y variable(s)
    "grid": "#E1E4E8",
}

# Plotly template used by every figure so all viewers (and screenshots) look
# identical — light mode.
PLOTLY_TEMPLATE = "plotly_white"
