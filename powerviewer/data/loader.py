"""Read the source data and expose it to the rest of the app.

Supported formats: ``.csv``, ``.xlsx`` / ``.xls`` and SQLite ``.db`` / ``.sqlite``.
Every file is expected to have a header row of field names; each row is one
instance (typically a unit of time).

The parsed :class:`pandas.DataFrame` is cached in-process keyed by the absolute
file path (and optional table name) so the heavy parsing happens once. Only the
small file/column metadata travels to the browser; the bulky frame stays here.
"""

from __future__ import annotations

import sqlite3
import warnings
from functools import lru_cache
from pathlib import Path
from typing import List

import pandas as pd

from ..config import DATA_DIR, SUPPORTED_EXTENSIONS


def list_data_files() -> List[str]:
    """Return the names of supported data files inside the data folder."""
    if not DATA_DIR.exists():
        return []
    files = [
        p.name
        for p in sorted(DATA_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return files


def _is_sqlite(path: Path) -> bool:
    return path.suffix.lower() in (".db", ".sqlite", ".sqlite3")


def list_db_tables(filename: str) -> List[str]:
    """List the user tables inside a SQLite database file."""
    path = DATA_DIR / filename
    if not path.exists() or not _is_sqlite(path):
        return []
    with sqlite3.connect(str(path)) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r[0] for r in rows]


@lru_cache(maxsize=16)
def _read(path_str: str, table: str | None) -> pd.DataFrame:
    """Parse a file into a DataFrame (cached). ``table`` only used for SQLite."""
    path = Path(path_str)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = _read_csv(path)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif _is_sqlite(path):
        with sqlite3.connect(str(path)) as conn:
            if table is None:
                # Default to the first user table.
                tables = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name LIMIT 1"
                ).fetchall()
                if not tables:
                    raise ValueError(f"No tables found in database '{path.name}'.")
                table = tables[0][0]
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    # Normalise column names to strings and strip whitespace.
    df.columns = [str(c).strip() for c in df.columns]
    # Recognise date/time columns (e.g. PeriodStartTime) so they can be used on
    # the X axis of the trend viewers.
    df = _coerce_datetimes(df)
    return df


# --------------------------------------------------------------------------- #
# CSV format handling
# --------------------------------------------------------------------------- #
# Files exported in some locales (e.g. Spanish/European) use ';' as the column
# separator and ',' as the decimal mark (with '.' as the thousands grouping) -
# the mirror of the US convention. We sniff the delimiter from the header and
# pick the matching decimal/thousands so values parse as real numbers.

def _sniff_csv(path: Path) -> tuple[str, dict]:
    """Return (encoding, pandas-read-kwargs) for *path* based on its header."""
    header = ""
    encoding = "utf-8-sig"
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as fh:
                header = fh.readline()
            encoding = enc
            break
        except UnicodeDecodeError:
            continue

    counts = {sep: header.count(sep) for sep in (";", "\t", ",")}
    sep = max(counts, key=counts.get)
    if counts[sep] == 0:
        sep = ","

    if sep == ";":  # European convention: decimal comma, thousands dot.
        return encoding, {"sep": ";", "decimal": ",", "thousands": "."}
    if sep == "\t":
        return encoding, {"sep": "\t", "decimal": "."}
    return encoding, {"sep": ",", "decimal": "."}


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV, auto-detecting delimiter and decimal/thousands marks."""
    encoding, kwargs = _sniff_csv(path)
    return pd.read_csv(path, encoding=encoding, **kwargs)


# --------------------------------------------------------------------------- #
# Datetime detection
# --------------------------------------------------------------------------- #
_DATE_HINTS = ("-", "/", ":")


def _coerce_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert text columns that look like dates/times into datetime dtype.

    A column is converted only when a clear majority of its values parse as
    dates (day-first, matching e.g. ``06-06-2026 8:00:00``); this leaves plain
    text and numeric columns untouched.
    """
    for col in df.columns:
        # Only text-like columns are candidates (pandas >=3 uses a 'str' dtype,
        # older versions use 'object' - skip anything already numeric/datetime).
        if (pd.api.types.is_numeric_dtype(df[col])
                or pd.api.types.is_datetime64_any_dtype(df[col])):
            continue
        sample = df[col].dropna().astype(str).head(25)
        if sample.empty or not any(
                any(h in v for h in _DATE_HINTS) for v in sample):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
        except Exception:  # noqa: BLE001
            continue
        if parsed.notna().mean() >= 0.8:
            df[col] = parsed
    return df


def load_dataframe(filename: str, table: str | None = None) -> pd.DataFrame:
    """Load (and cache) the DataFrame for *filename* inside the data folder."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return _read(str(path), table)


def get_columns(filename: str, table: str | None = None) -> List[str]:
    """Return all column names for the given file/table."""
    return list(load_dataframe(filename, table).columns)


def numeric_columns(filename: str, table: str | None = None) -> List[str]:
    """Return only the columns that hold numeric data (plottable values)."""
    df = load_dataframe(filename, table)
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def plottable_columns(filename: str, table: str | None = None) -> List[str]:
    """Return columns usable on an axis: numeric or datetime.

    Datetime columns are kept so a time-based X axis works in the Trend viewers;
    the 1D Dispersion viewer additionally restricts itself to numeric columns.
    """
    df = load_dataframe(filename, table)
    out = []
    for c in df.columns:
        if (pd.api.types.is_numeric_dtype(df[c])
                or pd.api.types.is_datetime64_any_dtype(df[c])):
            out.append(c)
    return out
