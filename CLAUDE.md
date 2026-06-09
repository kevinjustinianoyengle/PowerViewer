# PowerViewer — Project Guidelines (CLAUDE.md)

## Project Overview

**PowerViewer** is a scalable, decoupled, web-based graphic builder for
visualising signals and important variables in different scenarios (think
*oscilloscope*). It loads a dataset (`.xlsx`, `.csv` or SQLite `.db`) whose
header row holds the field names and whose rows are instances (usually a unit of
time), then lets the user explore that data through several **independent**
viewer types.

**Stack:** Python-first, to avoid web tooling and npm dependencies.
- [Dash](https://dash.plotly.com/) (Flask under the hood) — pure-Python web UI.
- [Plotly](https://plotly.com/python/) — interactive figures (zoom, pan, hover,
  in-browser snapshot) with no manual JS/npm.
- [pandas](https://pandas.pydata.org/) + `openpyxl` — read CSV / Excel.
- `sqlite3` (stdlib) — read `.db` / `.sqlite`.
- [SciPy](https://scipy.org/) — distribution fitting for the 1D Dispersion view.
- [Kaleido](https://github.com/plotly/Kaleido) — **server-side** PNG export so
  screenshots are written into the repository (not just downloaded).

## Quick Start

```bash
pip install -r requirements.txt          # first time only
python app.py                            # serves http://127.0.0.1:8050
```

On the **first run** the app creates the folders it needs (`1. Data` and
`2. Screenshots`). If `1. Data` is empty it prints a prompt and the UI asks you
to drop a data file in and press **Refresh**. Once a file is chosen from the
header dropdown the front end updates to show that file's variables.

> Kaleido 1.x needs a Chromium build to render PNGs. If screenshot saving fails
> with a "browser closed immediately" error, run `plotly_get_chrome -y` once to
> download a known-good Chrome (installed under `%LOCALAPPDATA%\plotly`).

## Repository Layout

```
3. Data Viewer/
├── app.py                      # entry point: builds the Dash app, runs server
├── requirements.txt
├── CLAUDE.md                   # this file
├── 1. Data/                    # <- drop .csv / .xlsx / .db here (auto-created)
├── 2. Screenshots/             # <- saved PNGs land here (auto-created, tracked)
└── powerviewer/                # the package
    ├── config.py               # paths, viewer registry, orange palette, theme
    ├── data/
    │   ├── loader.py           # file discovery + parsing + in-process cache
    │   └── __init__.py
    ├── graphs/                 # ONE module per viewer — fully decoupled
    │   ├── base.py             # shared: styling, marks, labels, screenshots
    │   ├── transforms.py       # shared derivative / cumulative-integral maths
    │   ├── series_figure.py    # shared series-list builder (both trend viewers)
    │   ├── dispersion_1d.py    # viewer 1
    │   ├── trend.py            # viewer 2 (thin wrapper over series_figure)
    │   ├── multi_trend.py      # viewer 3 (thin wrapper over series_figure)
    │   └── __init__.py
    ├── ui/
    │   ├── theme.py            # style dictionaries (built from config.THEME)
    │   ├── layout.py           # page grid + all components + dcc.Store state
    │   └── __init__.py
    └── callbacks/              # ONE module per viewer + shared concerns
        ├── data_callbacks.py   # file chooser, viewer switching, visibility
        ├── shell_callbacks.py  # burger sidebar, under-graph caption, screenshot
        ├── labels_callbacks.py # sidebar title/axis/legend editing
        ├── variables.py        # right-hand variable list + click selection
        ├── dispersion_callbacks.py
        ├── trend_callbacks.py
        ├── multi_callbacks.py
        ├── marks_callbacks.py  # shared add/list/delete marks
        └── __init__.py         # register_all(app)
```

## Architecture & Decoupling

The core design rule is that **viewers do not know about each other**.

- **`powerviewer/graphs/*`** are *pure plotting* modules. Each exposes a single
  `build_figure(...)` that takes plain data + options and returns a Plotly
  `Figure`. They have **no Dash imports** — they are unit-testable on their own.
- **`powerviewer/callbacks/*`** hold all Dash wiring. Each viewer's callbacks
  live in their own module and write to their own `dcc.Graph`. Adding a viewer =
  add a graph module + a callback module + one entry in `config.VIEWERS`.
- **Shared concerns** (theme, marks, screenshots) live exactly once in
  `graphs/base.py`, so every viewer zooms, marks and screenshots identically.
- **State** lives in `dcc.Store` objects (see `ui/layout.py::_stores`), never in
  globals, so it survives re-renders and stays per-viewer.
- **Data** is cached in-process (`data/loader.py`, `lru_cache`) keyed by file
  path (+ table). Only small metadata (file name, column list) travels to the
  browser; the heavy DataFrame stays server-side.

### UI regions (CSS grid, see `ui/theme.PAGE`)

```
┌────────────────────────────────────────────────────┐
│ header  ☰ | title | file chooser | ...... | 📷 right │
├──────────────────────────────────────┬─────────────┤
│ graph (active viewer)                 │ vars (slim,  │
│                                       │ right panel) │
├──────────────────────────────────────┴─────────────┤
│ options — per-viewer opts · labels · marks (bottom)  │
└────────────────────────────────────────────────────┘
```

The **☰ burger** (top-left) opens a **left sidebar drawer** that overlays the UI
(top z-index, dimmed backdrop). The sidebar is the **graph chooser**: it lists
the viewers to pick from and, at its **bottom**, shows the selected graph's
**title + small description** (driven by `active-view`; see
`callbacks/shell_callbacks.py`).

The **bottom options panel** holds, in order: the active viewer's functional
options, the **Labels** row (editable **title**, **X/Y axis titles** and — for
dispersion — **legend name**; `callbacks/labels_callbacks.py`, stored in
`labels-store`), and the **Marks** row + history. It has a **fixed height**
(`theme.OPTIONS_PANEL`, scrolls internally) so the **graph section keeps a
constant height** no matter how many series cards or marks are added. The
variables panel on the right is intentionally narrow (15% slimmer than default).

## The Three Viewers

### 1. 1D Dispersion (`graphs/dispersion_1d.py`)
- Takes **one** variable. Values spread along **X**; the vertical axis lifts the
  1D cloud into 2D via a density histogram.
- A **single** theoretical fit can be selected at a time (radio: None / uniform
  / normal / log-normal / exponential), fitted on the fly with SciPy. The fit
  curve's **colour is editable** (swatch dropdown in the bottom options).
- When a distribution is selected the raw **samples scatter under that fitted
  curve** (each point at a random height in `[0, pdf(x)]`), so the point-cloud
  silhouette mirrors the chosen distribution — a quick visual goodness-of-fit.
  With no distribution selected, samples sit as a jittered strip below zero.
- Selection is **exclusive**: choosing one variable blocks the others until it
  is deselected (enforced in `callbacks/variables.py`).

### Series model (shared by both Trend viewers)

Both trend viewers draw a **list of series** (`graphs/series_figure.py`). A series
is `{id, source, transform, name, color, scale, displace}` where `transform` is
`none` / `derivative` / `integral`. So a derivative or integral is **just another
series over the same source column** — Raw + d/dx + ∫ can all be shown at once,
each as its own **card** with an **editable name**, **colour**, **scale** and
**displacement** (cards rendered by `ui/cards.py`, namespaced `tr`/`mt`). Per
series, maths is applied in the order *transform → scale → displacement*. Each
card has **+d/dx**, **+∫** (add a derivative/integral of that card's source as a
brand-new series) and **✕** (delete). The integral's total value is shown in its
legend entry. Clearing a scale/displacement box keeps the previous value
(identity fallback scale 1, displacement 0).

### 2. Trend (`graphs/trend.py`)
- Exactly **one X** and **one Y** source. **First** click → X, **second** → Y;
  the **Swap** button exchanges them. With both set, other variables are blocked.
- The single Y starts as a raw series; add its **derivative / integral** on top
  via the card **+d/dx** / **+∫** buttons (all coexist).
- **Axis-wise zoom**: `dragmode="zoom"` so horizontal drag zooms X, vertical
  zooms Y; spikes guide intent.

### 3. Multiple Trend (`graphs/multi_trend.py`)
- **One X**, **any number of Y** source variables, each adding a raw series; add
  derivative/integral series on top of any of them.
- **Sum of two lines**: the *Sum two lines* control (two dropdowns + **Add sum**)
  creates a new series whose value is the row-wise **sum of two source columns**.
  Such a series carries `sources=[a, b]` (instead of a single `source`); the
  shared builder sums those columns, then applies transform → scale → displace,
  so you can also take the derivative/integral of a sum. Sum cards show a **Σ**
  badge. (Sum is Multiple-Trend only.)
- Default colours come from `config.ORANGE_PALETTE` (recolourable per card).
- The **Y axis auto-fits dynamically** to the highest/lowest *displayed* values.
- Adding/removing a series **restarts the view** (figure `uirevision` keyed to
  the series ids) to avoid stale-zoom bugs.

## Common Capabilities (all viewers)

Implemented once in `graphs/base.py`:
- **Zoom / pan** — native Plotly (scroll-zoom enabled, axis-wise on trends).
- **Screenshots** — two ways:
  - In-browser snapshot button on the Plotly modebar (downloads).
  - **"📷 Screenshot"** button top-right in the header → captures the **active**
    viewer and writes a PNG into `2. Screenshots/` via Kaleido (server-side,
    committed with the repo). Files are named `<viewer>_<YYYYMMDD_HHMMSS>.png`.
    The saved image reflects the **current zoom/pan**: Plotly keeps interactive
    zoom in the graph's `relayoutData` (not the `figure` prop), so
    `shell_callbacks._apply_view` copies those ranges onto the figure before
    export (works for numeric and datetime axes).
- **Marks** — the horizontal controls at the bottom read **type → value →
  (y for point) → label → [+]**. Added marks appear as well-spaced **pills**
  (e.g. `H: nominal = 100`, `P: peak = (3, 5)`), each with a **✕ delete**, plus
  **Clear all**. Marks are stored **per viewer** in `marks-store`.
- **Labels** — title, X/Y axis titles and legend (series) names are editable per
  viewer from the **bottom options panel**, stored in `labels-store` and applied
  via `graphs/base.apply_labels` / `series_name`.

## Data Format

- First row = field names (column headers).
- Each subsequent row = one instance (typically a unit of time).
- For SQLite files, a **table chooser** appears in the header; the first user
  table is selected by default.
- Only **numeric** (and **datetime**, for the X axis) columns are listed as
  plottable variables. 1D Dispersion expects numeric data.
- **CSV locale auto-detection** (`data/loader.py::_sniff_csv`): the delimiter is
  sniffed from the header. A `;`-separated file is treated as the European
  convention — **decimal comma** and **thousands dot** (e.g. `-8,77E-02`,
  `1.234,5`) — so values parse as real numbers; `,`/tab files use the US
  convention. UTF-8/Latin-1 encodings are both handled.
- **Datetime detection** (`_coerce_datetimes`): text columns whose values look
  like dates/times are parsed **day-first** (e.g. `06-06-2026 8:00:00`) and
  converted to datetime dtype, so a time column like `PeriodStartTime` becomes
  selectable on the trend X axis.

## Extending PowerViewer (add a new viewer)

1. Create `powerviewer/graphs/<name>.py` with a pure `build_figure(...)`.
2. Create `powerviewer/callbacks/<name>_callbacks.py` with a `register(app)`
   that renders into a new `dcc.Graph(id="<name>-graph")`.
3. Add the graph container in `ui/layout.py::_graph_area`, an options panel in
   `_options_panel`, and any `dcc.Store` state in `_stores`.
4. Register the viewer in `config.VIEWERS` (key, label, icon, help) and add it
   to the visibility toggles in `data_callbacks.toggle_visibility`.
5. Call your `register` from `callbacks/__init__.register_all`.

Because each viewer is isolated, none of the above touches the other viewers.

## Conventions

- Keep graph modules free of Dash imports (pure plotting).
- Read theme/palette/paths from `config.py`; don't hard-code colours or paths.
- New state → a `dcc.Store`, not a module global.
- Per-viewer selection rules live in `callbacks/variables.py::select`.
- Screenshots must stay tracked in the repo (see `.gitignore`).
