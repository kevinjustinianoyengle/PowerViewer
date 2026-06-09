"""PowerViewer - a decoupled, scalable web graphic builder for signal visualization.

Each graph type lives in its own module under ``powerviewer.graphs`` and is wired
through its own callback module under ``powerviewer.callbacks`` so that adding,
removing or modifying a viewer never touches the others.
"""

__version__ = "1.0.0"
