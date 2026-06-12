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
    │   ├── series_figure.py    # shared builder: series list, scatter, regression
    │   ├── report.py           # DECOUPLED report-only ops (break-to-zero; future stats)
    │   ├── dispersion_1d.py    # viewer 1 (1D Dispersion)
    │   ├── multi_trend.py      # viewer 2 (Trends: lines/scatter + regression)
    │   └── __init__.py
    ├── ui/
    │   ├── theme.py            # style dictionaries (built from config.THEME)
    │   ├── cards.py            # bottom chip-bar + per-series options popovers
    │   ├── layout.py           # page grid + all components + dcc.Store state
    │   └── __init__.py
    └── callbacks/              # ONE module per viewer + shared concerns
        ├── data_callbacks.py   # file chooser, viewer switching, visibility
        ├── shell_callbacks.py  # burger sidebar, under-graph caption, screenshot
        ├── ribbon_callbacks.py # ribbon popovers + chip-open + per-view chrome
        ├── labels_callbacks.py # title/axis editing + legend (series) renames
        ├── variables.py        # right-hand variable list + click selection
        ├── dispersion_callbacks.py
        ├── multi_callbacks.py  # series + line/scatter mode + per-curve regression
        ├── marks_callbacks.py  # shared add/list/delete marks
        ├── report_callbacks.py # DECOUPLED report tool: Break-to-zero wiring
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
│ header  ☰|title|file chooser|..|shot-name|📷 right   │
├────────────────────────────────────────────────────┤
│ ribbon   ✎ Edit Labels · ⇄ Adjust Axes · ⚐ Marks · ⚙ View │
├──────────────────────────────────────┬─────────────┤
│ graph (active viewer)                 │ vars (slim,  │
│                                       │ right panel) │
├──────────────────────────────────────┴─────────────┤
│ chips   ● series-a   ● series-b   …  (→ options pop) │
└────────────────────────────────────────────────────┘
```

The header has a **screenshot-name input** (`screenshot-name`) just left of the
📷 Screenshot button: typing a name saves the PNG as `<name>.png` (sanitised by
`base._safe_stem`); blank falls back to `<viewer>_<timestamp>.png`. It does **not**
change the graph title (the title is edited only in the Edit Labels popover).

The UI is split into a **top options ribbon** and a **bottom chip bar** that
frame the graph (`gridTemplateAreas` rows `header / ribbon / graph+vars / chips`).

The **☰ burger** (top-left) opens a **left sidebar drawer** that overlays the UI
(top z-index, dimmed backdrop). The sidebar is the **graph chooser**: it lists
the viewers to pick from and, at its **bottom**, shows the selected graph's
**title + small description** (driven by `active-view`; see
`callbacks/shell_callbacks.py`).

**Top ribbon** (`ui/layout._ribbon`, wiring in `callbacks/ribbon_callbacks.py`):
each button toggles one floating **popover** anchored beneath it; only one is
open at a time (`ribbon-open` store), and switching viewer closes it.
- **✎ Edit Labels** — title + X/Y axis titles (+ **Y-right** title for Trends) +
  the **Legend box** position (`label-legend-pos` → `labels-store[...]["legend_pos"]`:
  `tl`/`tr`/`bl`/`br` put the legend in that in-plot corner as a bordered box,
  `out` floats it outside on the right). Applied in `base.apply_labels`.
- **⇄ Adjust Axes** — Trends only (hidden for Dispersion): **shared-zero**
  alignment + manual **Left/Right min/max** ranges.
- **Σ Combine** — Trends only: build a derived line from two existing source
  columns with an **operator** (`+` / `−` / `×` / `÷`, `multi-op`). The new series
  carries `sources=[a, b]` + `op`; `series_figure._combine` applies it
  (÷ guards /0 → NaN). Its chip badge shows the operator symbol.
- **⌁ Break** — Trends only, **report tool**: pick a line + a **break time** (an
  X instant, `YYYY-MM-DD HH:MM`, day-first) and re-shape its discharge half to
  deplete to zero (energy report). Sets `break_time` on the chosen series in
  `multi-store`; the maths lives in the decoupled `graphs/report.break_to_zero`
  and is applied by `series_figure.build` (charge half before the time is kept;
  the discharge half from that time on → `last - y`, so it inverts and ends at
  `Y = 0`). Wiring in `callbacks/report_callbacks.py`. **Clear** removes all
  breaks. This view is report-only and kept separate from the analysis viewers.
- **⚐ Marks** — the horizontal type → value → (y) → label → [+] controls + the
  pill history (`callbacks/marks_callbacks.py`). The value box's **placeholder
  hints the format** per type (a vertical/point mark on a time axis takes
  `YYYY-MM-DD HH:MM`, parsed day-first; numbers also work).
- **⚙ View** — the active viewer's own controls (label changes per viewer:
  *Distribution* / *Display*); the two per-viewer option divs
  (`dispersion-options` / `multi-options`) live inside and are toggled by
  `data_callbacks.toggle_visibility`. The Trends *Display* popover holds just the
  **Lines ↔ Scatter** mode radio (`multi-style`); the *Combine* builder is its own
  ribbon button (above).

**Bottom chip bar** (`ui/layout._chip_bar`, renderer `ui/cards.py`): one **chip
per series drawn in the graph** — a colour dot + name (+ an **L/R axis badge** for
Trends). Clicking a chip raises a **popover *above* it** (`chip-open` store) with
that series' options. The options shown are tailored per viewer:
- **1D Dispersion** — colour + rename only (least, as requested);
- **Trends** — colour + name; axis (Y ◀ / Y ▶) + scale + displacement; **+d/dx**
  + integral (with a trapezoid/front/back **rule**) + **+∫**; and a **per-curve
  Regression** block (line toggle + **fit colour** + equation-box corner) *greyed
  out until the graph is in Scatter mode*, then Remove.

The popover is laid out in compact horizontal rows (see `ui/cards._series_menu`):
**row 1** = a compact colour swatch (square + arrow, *no* label/hex) + the name
input; **row 2** = axis + scale + displacement; **row 3** = **+ d/dx** and the
integral (an **integral-rule** dropdown — Trapezoid / Front rect. / Back rect. —
plus **+ ∫**); then the **regression** row; **Remove** at the bottom.
The series cards' inputs keep their original pattern-matching IDs
(`mt-name/-color/-scale/-displace/-axis/-add-d/-add-i/-del`, plus
`mt-fit/-fit-color/-fit-pos`), and *every* series' inputs are rendered (only the open chip's
popover is visible), so the ALL-pattern Trends callbacks are unchanged.
Dispersion's chip rename input reuses `{"type":"series-name","index":col}` so the
shared `labels_callbacks.save_legend` still applies them. The variables panel on
the right is intentionally narrow (15% slimmer than default).

## The Two Viewers

### 1. 1D Dispersion (`graphs/dispersion_1d.py`)
- Takes **one** variable. Values spread along **X**; the vertical axis lifts the
  1D cloud into 2D via a density histogram.
- The histogram's **bar colour** and the variable's **legend name** are edited
  from its **chip popover** (`disp-store["color"]`, applied via the `color` arg
  of `build_figure`); this is intentionally the *minimum* per-series UI.
- A **single** theoretical fit can be selected at a time (radio: None / uniform
  / normal / log-normal / exponential), fitted on the fly with SciPy. The fit
  curve's **colour is editable** (swatch dropdown in the **View** popover).
- When a distribution is selected the raw **samples scatter under that fitted
  curve** (each point at a random height in `[0, pdf(x)]`), so the point-cloud
  silhouette mirrors the chosen distribution — a quick visual goodness-of-fit.
  With no distribution selected, samples sit as a jittered strip below zero.
- **Zoom recomputes the dispersion**: zooming the X axis re-bins the histogram so
  the same bar count spreads across the visible window, and re-fits the
  distribution to just those samples. The render callback reads the graph's
  `relayoutData` and passes `value_range` to `build_figure`, which filters,
  re-bins (explicit `xbins`) and re-fits on the subset, then pins the X range.
  Double-click to reset to the full range.
- **Fitted moments** (`dispersion_1d.fit_moments`): the selected distribution's
  key parameters (normal → mean & std, uniform → min/max/spread, log-normal →
  median/mean/std/σ(log), exponential → mean/rate/std, plus the sample count) are
  shown as **pills in the View popover — outside the plot, not in the legend**
  (`disp-stats`). They honour the current zoom window too.
- Selection is **exclusive**: choosing one variable blocks the others until it
  is deselected (enforced in `callbacks/variables.py`).

### Series model (Trends)

The Trends viewer draws a **list of series** (`graphs/series_figure.py`). A series
is `{id, source|sources, transform, name, color, scale, displace, axis}` where
`transform` is `none` / `derivative` / `integral`. So a derivative or integral is
**just another series over the same source column** — Raw + d/dx + ∫ can all be
shown at once, each as its own **chip** in the bottom bar whose popover holds an
**editable name**, **colour**, **scale** and **displacement** (chips rendered by
`ui/cards.render_series_chips`, namespaced `mt`). Per series, maths is applied in
the order *transform → scale → displacement*. Each chip popover has **+ d/dx**,
**+ ∫** (add a derivative/integral of that chip's source as a brand-new series)
and **Remove series**. The legend shows just the series **name** (the integral's
running total is computed but **not** appended). Clearing a scale/displacement box
keeps the previous value (identity fallback scale 1, displacement 0).

**Time-aware maths** (`graphs/transforms.py`): derivative and integral integrate
against the **real timestamps**, measured in **elapsed hours** (NaT-safe), so
minute-resolution data contributes `y · (1/60)` per step — power integrates
straight to energy and the derivative is a per-hour rate (no MW/MWh labels are
added). Non-uniform spacing is respected. The integral takes a **rule**
(`apply_transform(..., method=)`): `"trapezoid"` (default), `"front"`
(left/forward rectangles) or `"back"` (right/backward rectangles), chosen per
series via the chip's integral-rule dropdown (`mt-int-method`, stored as
`integral_method`). Switch `_NS_PER_UNIT` to `1e9` for seconds.

### 2. Trends (`graphs/multi_trend.py`)
- **One X**, **any number of Y** source variables, each adding a raw series; add
  derivative/integral series on top of any of them.
- **Combine two lines**: the **Σ Combine** ribbon popover (two dropdowns + an
  **operator** `+ − × ÷` + **Add combined line**) creates a new series whose value
  is the row-wise combination of two source columns. Such a series carries
  `sources=[a, b]` + `op`; `series_figure._combine` applies the operator (then
  transform → scale → displace), so you can also take the derivative/integral of a
  combined line. Combined chips show the **operator symbol** as their badge.
  (Multiple-Trend only.)
- **Two Y axes**: each chip popover has a **Y ◀ / Y ▶** selector assigning its
  series to the left (primary) or right (secondary) axis, so trends with very
  different scales are both readable. Each axis auto-fits independently. Series
  moved to the right axis are recoloured from a distinct blue/teal palette
  (`config.SECONDARY_PALETTE`) so it's obvious which scale a trend belongs to.
  The **Adjust Axes** ribbon popover (Multiple-Trend only) controls them: a
  **shared-zero** checkbox aligns both axes' zero lines at the same vertical
  position (`series_figure._aligned_ranges`), and **Left/Right min/max** boxes set
  each axis range manually (blank = auto-fit). The **left** axis title is the Edit
  Labels *Y-axis title*; the **right** axis title is the *Y-right title* box
  (shown only here), stored in `labels-store[...]["yaxis2"]`.
- Default colours come from `config.ORANGE_PALETTE` (recolourable per chip).
- The **Y axis auto-fits dynamically** to the highest/lowest *displayed* values.
- **Lines ↔ Scatter** (the **Display** = ⚙ View popover, `multi-style`): switches
  *all* curves between connected lines and unconnected points. The mode lives in
  `multi-store["style"]`.
- **Per-curve regression** (merged in from the former standalone viewer): in
  **Scatter** mode each chip exposes a **Regression line** toggle (`mt-fit`), a
  **fit colour** (`mt-fit-color`, defaults to the curve's colour) and an
  **Equation box** corner dropdown (`mt-fit-pos`); all **greyed out in Lines
  mode**. An enabled curve gets its own **least-squares** fit (`numpy.polyfit`
  deg 1) drawn **on that curve's own Y axis**, in the fit colour, as
  `lines+markers` so the predicted value at each sample is readable. Its
  **equation + R²** show in an on-graph box (not the legend) at the chosen corner,
  coloured to match; boxes sharing a corner are **stacked** (vertical `yshift`).
  The fit is **zoom-aware**: `multi_callbacks.render` reads the graph's
  `relayoutData` and passes the visible X window as `value_range`, so the
  regression recomputes for the section you zoom into.
- Adding/removing a series **restarts the view** (figure `uirevision`, which is
  keyed to the **series ids + style + axis_cfg**) so toggling line/scatter,
  shared-zero or a manual range actually re-applies the new figure instead of
  Plotly preserving the stale view.

## Common Capabilities (all viewers)

Implemented once in `graphs/base.py`:
- **Zoom / pan** — native Plotly (scroll-zoom enabled, axis-wise on trends).
- **Screenshots** — two ways:
  - In-browser snapshot button on the Plotly modebar (downloads).
  - **"📷 Screenshot"** button top-right in the header → captures the **active**
    viewer and writes a PNG into `2. Screenshots/` via Kaleido (server-side,
    committed with the repo). Named from the header **screenshot-name** box, or
    `<viewer>_<YYYYMMDD_HHMMSS>.png` when blank.
    The saved image reflects the **current zoom/pan**: Plotly keeps interactive
    zoom in the graph's `relayoutData` (not the `figure` prop), so
    `shell_callbacks._apply_view` copies those ranges onto the figure before
    export (works for numeric and datetime axes).
- **Marks** — the **⚐ Marks** ribbon popover reads **type → value →
  (y for point) → label → [+]**. Added marks appear as well-spaced **pills**
  (e.g. `H: nominal = 100`, `P: peak = (3, 5)`), each with a **✕ delete**, plus
  **Clear all**. Marks are stored **per viewer** in `marks-store`.
- **Labels** — title, X/Y axis titles and the **legend-box position** are editable
  per viewer from the **✎ Edit Labels** ribbon popover; **legend (series) names**
  are edited from the bottom **chip popovers**. All stored in `labels-store` and
  applied via `graphs/base.apply_labels` / `series_name`. The **legend renders as a
  box inside the plot** (top-right by default) and can be moved to any corner or
  pushed outside.

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
3. Add the graph container in `ui/layout.py::_graph_area`, a per-viewer **View**
   options div in `_view_popover` (id `<name>-options`), a chip-bar section in
   `_chip_bar` (id `<name>-chips`), and any `dcc.Store` state in `_stores`.
4. Register the viewer in `config.VIEWERS` (key, label, icon, help); add it to
   `data_callbacks.toggle_visibility` (graph + options divs) and to
   `ribbon_callbacks.chrome` (chip section + `_VIEW_LABEL`).
5. Call your `register` from `callbacks/__init__.register_all`.

Because each viewer is isolated, none of the above touches the other viewers.

## Conventions

- Keep graph modules free of Dash imports (pure plotting).
- Read theme/palette/paths from `config.py`; don't hard-code colours or paths.
- New state → a `dcc.Store`, not a module global.
- Per-viewer selection rules live in `callbacks/variables.py::select`.
- Screenshots must stay tracked in the repo (see `.gitignore`).
