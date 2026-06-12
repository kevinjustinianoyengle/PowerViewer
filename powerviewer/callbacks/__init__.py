"""Callback registration.

Each viewer (and the shared concerns) registers its callbacks through its own
module so the wiring is as decoupled as the graph modules. ``register_all``
is the single entry point called by :mod:`app`.
"""

from dash import Dash

from . import (
    data_callbacks,
    shell_callbacks,
    ribbon_callbacks,
    labels_callbacks,
    variables,
    dispersion_callbacks,
    multi_callbacks,
    marks_callbacks,
    report_callbacks,
)


def register_all(app: Dash) -> None:
    """Register every callback group on *app*."""
    data_callbacks.register(app)
    shell_callbacks.register(app)
    ribbon_callbacks.register(app)
    labels_callbacks.register(app)
    variables.register(app)
    dispersion_callbacks.register(app)
    multi_callbacks.register(app)
    marks_callbacks.register(app)
    report_callbacks.register(app)
