# KDP Builder

KDP Builder is a local-first toolkit for generating professional, print-ready interiors (and soon covers) for KDP. It focuses on speed, repeatability, and 100% vector output using ReportLab. Start with a CLI to create lined journals, then expand into grids, trackers, and AI-generated layouts.

## Features

- **Vector interiors**: Crisp, scalable PDFs suitable for print.
- **KDP-aware sizing**: Trim sizes and safe margins built-in (e.g., `6x9`).
- **Fast CLI**: Generate 20–150+ page interiors in seconds.
- **Templates**: `lined`, `grid`, `dot`, `habit` templates available via CLI.
- **Parity-aware safe area**: Even/odd pages mirror inner/outer margins; optional gutter.
- **Extensible**: Add validators, AI layout gen, and covers.
- **Local-first**: Works offline; no API keys required for the MVP.

## Project Structure

- `main.py` — CLI entrypoint (Click-based).
- `kdp_builder/config/sizes.py` — Trim sizes, margins, bleed flags.
- `kdp_builder/renderer/pdf_renderer.py` — Vector rendering with multiple templates.
- `kdp_builder/renderer/templates.py` — Template primitives (lined, grid, dot, habit).
- `kdp_builder/__init__.py` — Package marker.

Planned modules:
- `kdp_builder/validator/` — KDP checks (safe area, line weights, DPI).
- `kdp_builder/layout/` — AI layout generator (Ollama, Bedrock).
- `kdp_builder/cover/` — Vector/SDXL covers.

## Quickstart

1) Create and activate a virtual environment (macOS):
```bash
cd KDP_builder
python3 -m venv .venv
source .venv/bin/activate
```

2) Install minimal dependencies:
```bash
pip install -r requirements.txt
```

3) Generate your first interior (6x9, 120 pages) — defaults to `outputs/interior.pdf`:
```bash
python main.py --trim 6x9 --pages 120 --out outputs/interior.pdf
```

4) Customize spacing and line weight:
```bash
python main.py --line-spacing-pt 20 --line-weight-pt 0.6 --out interior_dense.pdf
```

## Templates

Use `--template` and related flags:

- **Lined** (default):
```bash
python main.py --template lined --pages 4 --gutter-pt 18
```

- **Grid**:
```bash
python main.py --template grid --grid-size-pt 18 --pages 2 --out outputs/grid.pdf
```

- **Dot grid**:
```bash
python main.py --template dot --dot-step-pt 18 --dot-radius-pt 0.6 --pages 2 --out outputs/dot.pdf
```

- **Habit tracker**:
```bash
python main.py --template habit --habit-rows 20 --habit-cols 7 --pages 2 --out outputs/habit.pdf
```

## CLI Options

- `--trim` Trim key (default: `6x9`). Defined in `kdp_builder/config/sizes.py`.
- `--pages` Number of pages (default: `120`, min `1`).
- `--out` Output PDF path (default: `outputs/interior.pdf`).
- `--line-spacing-pt` Line spacing in points (default: `18.0`).
- `--line-weight-pt` Stroke width in points (default: `0.5`).
- `--gutter-pt` Extra inner margin added to binding side (odd/even mirrored).
- `--template` One of `lined`, `grid`, `dot`, `habit`.
- `--grid-size-pt` Grid cell size (grid).
- `--dot-step-pt`, `--dot-radius-pt` Dot spacing and radius (dot).
- `--habit-rows`, `--habit-cols` Habit matrix size (habit).
- `--page-numbers` Add page numbers on the outer side (mirrored even/odd).
- `--header`, `--footer` Centered header/footer text within safe area.
- `--header-font-size`, `--footer-font-size`, `--page-number-font-size` Typography controls for pagination.
- `--set-trimbox` Write TrimBox equal to the safe area (for QA in viewers that show boxes).
- `--set-bleedbox` Write BleedBox around TrimBox by `--bleed-pt` (clamped to MediaBox).
- `--bleed-pt` Bleed amount in points (72pt = 1 inch).
- Cover generation:
  - `--make-cover` Generate a cover instead of interior
  - `--cover-pages` Interior page count for spine width
  - `--cover-paper` Paper type: `white|cream|color`
  - `--cover-bleed-pt` Cover bleed (points); e.g. 9pt = 0.125"
  - `--cover-title`, `--cover-subtitle`, `--cover-author`
- `--validate-path` Validate an existing PDF and exit.
- `--validate-trim` Trim key used for validation (defaults to `--trim`).
 - Cover validation:
   - `--validate-cover-path` Validate a cover (requires `--trim`, `--cover-pages`, `--cover-paper`, `--cover-bleed-pt`).

See help:
```bash
python main.py --help
```

## How It Works

- Layouts are defined procedurally and rendered with ReportLab into vector PDFs compliant with typical KDP trims and margins.
- The MVP now includes multiple templates (lined, grid, dot grid, habit tracker) with mirrored safe areas and optional gutter.

## Validation

Use `--validate-path` (interior) or `--validate-cover-path` (cover). Current checks include:

- Page count within KDP interior range (24–828)
- Uniform page size vs `--trim`
- PDF encryption status
- PDF header version (warn > 1.7)
- Rotation/orientation warnings
- Annotations/form fields not allowed
- TrimBox/BleedBox sanity (inside MediaBox; Trim inside Bleed)
- Embedded images count and small intrinsic size heuristic (<900 px)
- Fonts: non-embedded (error), Type3 (warning), subset fonts (info)

## Pagination

Add page numbers, header, and footer:

```bash
python main.py --trim 6x9 --pages 24 --template lined --gutter-pt 18 \
  --page-numbers --header "My Journal" --footer "www.example.com" \
  --header-font-size 12 --footer-font-size 10 --page-number-font-size 10 \
  --out outputs/paginated_24.pdf
```

Page numbers render on the outer side (right on odd pages, left on even).

## QA: TrimBox/BleedBox

Optionally write TrimBox/BleedBox to the PDF for better QA in compatible viewers:

```bash
python main.py --trim 6x9 --pages 2 --template grid --grid-size-pt 18 \
  --gutter-pt 18 --set-trimbox --set-bleedbox --bleed-pt 9 \
  --out outputs/boxes.pdf
```

This sets TrimBox to the mirrored safe area and BleedBox to TrimBox expanded by `bleed-pt` (e.g., 9pt = 0.125").

## Covers

Generate a full-wrap cover (back + spine + front) with a simple placeholder layout:

```bash
python main.py --make-cover --trim 6x9 --cover-pages 120 --cover-paper white \
  --cover-bleed-pt 9 --cover-title "My Planner" --cover-subtitle "Undated" \
  --cover-author "D. Parhomenko" --out outputs/cover.pdf
```

Validate the cover against expected dimensions for the given trim/pages/paper/bleed:

```bash
python main.py --validate-cover-path outputs/cover.pdf \
  --trim 6x9 --cover-pages 120 --cover-paper white --cover-bleed-pt 9
```

## Outputs directory

Generated files are written to `outputs/` (ignored by git). Override with `--out` if needed.

## Roadmap

- Templates: grid, dot grid, habit/expense trackers.
- Validator: safe area checks, line thickness, font embedding.
- Covers: vector typography + color systems; optional SDXL artwork.
- AI: Ollama-driven JSON layout generation (local), Bedrock option.
- Web UI: FastAPI + React for preview, drag-and-drop adjustments.

## Tech Stack

- **Python**: ReportLab, Click (CLI).
- Optional/Planned: Typer, FastAPI, Ollama (local LLM), Diffusers/SDXL, OpenCV, Tesseract.

## Contributing

- Fork, create a feature branch, and submit a PR.
- Keep PRs focused; include before/after screenshots or sample PDFs when relevant.
- For new templates, add sample outputs to a `samples/` folder (git LFS recommended for large assets).

## License

Code: MIT

Models & dataset: “All Rights Reserved”

## Disclaimer

Always verify KDP guidelines for your chosen trim size, margins, and bleed settings before publishing. Test-print when possible.
