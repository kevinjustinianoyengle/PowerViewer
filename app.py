"""PowerViewer - application entry point.

Run with::

    python app.py

On first launch it creates the ``1. Data`` and ``2. Screenshots`` folders if they
are missing, then serves the UI. If no data file is present yet, the interface
prompts you to drop a ``.csv`` / ``.xlsx`` / ``.db`` into ``1. Data`` and refresh.
"""

from __future__ import annotations

import os

from dash import Dash

# Importing config first triggers .env loading (see powerviewer/config.py).
from powerviewer.callbacks import register_all
from powerviewer.config import DATA_DIR, ensure_folders
from powerviewer.data import list_data_files
from powerviewer.ui import build_layout

# Server settings (overridable via .env / environment variables).
HOST = os.environ.get("POWERVIEWER_HOST", "127.0.0.1")
PORT = int(os.environ.get("POWERVIEWER_PORT", "8050"))
DEBUG = os.environ.get("POWERVIEWER_DEBUG", "true").strip().lower() == "true"

# Inline stylesheet: light scrollbars + a touch of polish for native controls.
_INDEX_CSS = """
    body { margin: 0; background: #FFFFFF; }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #EDF1F5; }
    ::-webkit-scrollbar-thumb { background: #C4CDD5; border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: #E8590C; }
    .Select-control, .Select-menu-outer { color: #111 !important; }
"""

INDEX_STRING = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>PowerViewer</title>
        {%favicon%}
        {%css%}
        <style>""" + _INDEX_CSS + """</style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>"""


def create_app() -> Dash:
    """Build and configure the Dash application."""
    ensure_folders()  # first-run: make '1. Data' and '2. Screenshots'

    app = Dash(__name__, title="PowerViewer", update_title=None)
    app.index_string = INDEX_STRING
    app.layout = build_layout()
    register_all(app)
    return app


app = create_app()
server = app.server  # exposed for WSGI deployment (gunicorn/waitress)


if __name__ == "__main__":
    if not list_data_files():
        print(f"\n[PowerViewer] No data files yet. Drop a .csv / .xlsx / .db "
              f"into:\n    {DATA_DIR}\nthen click Refresh in the UI.\n")
    print(f"[PowerViewer] Starting on http://{HOST}:{PORT} …")
    app.run(debug=DEBUG, host=HOST, port=PORT)
