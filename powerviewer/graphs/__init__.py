"""Graph viewers. Each module is fully decoupled from the others.

A viewer module exposes a single ``build_figure(...)`` function returning a
Plotly :class:`~plotly.graph_objects.Figure`. Shared concerns (theme, marks,
screenshot export) live in :mod:`powerviewer.graphs.base`.
"""
