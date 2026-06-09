"""Data access layer: file discovery, parsing and an in-process cache."""

from .loader import (
    list_data_files,
    load_dataframe,
    get_columns,
    numeric_columns,
    plottable_columns,
    list_db_tables,
)

__all__ = [
    "list_data_files",
    "load_dataframe",
    "get_columns",
    "numeric_columns",
    "plottable_columns",
    "list_db_tables",
]
