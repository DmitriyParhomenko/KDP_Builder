# AI Vision & Document Analysis

This project uses AI to extract structured blocks (grids, headers, checkboxes, labeled inputs) from PDF pages. It combines computer vision (CV), vector analysis, and two AI backends: DocLayNet (YOLOv8) and Ollama Vision Language Models.

## Overview

- **Input**: Analyzed PDF pages (JSON + PNG per page)
- **Output**: Structured blocks (JSON) + visual thumbnails with overlays
- **AI backends**:
  - `doclayout`: YOLOv8-DocLayNet for tables/titles/text regions via SAHI slicing
  - `ollama_vl`: llava:13b (or qwen2.5-vl) for semantic labels (MONTH/YEAR/CLASS, column headers)
  - `both`: Combine DocLayNet geometry + Ollama VLM semantics
- **Fusion**: AI detections are merged with CV lines and vector rectangles, with strict pruning to avoid hallucinations.

## Setup

### 1) Install dependencies
```bash
# Ensure opencv-python (not headless) and numpy<2.0 for chromadb compatibility
python3 -m pip install -r requirements.txt
```

### 2) Local DocLayNet weights (optional but recommended)
- Place your DocLayNet YOLOv8 weights at `models/doclayout/yolov8_doclaynet.pt`.
- The server will auto-load them via `DOCLAYOUT_WEIGHTS`.
- If you use a different path:
  ```bash
  export DOCLAYOUT_WEIGHTS=/absolute/path/to/your_weights.pt
  uvicorn web.backend.main:app --reload --port 8000
  ```

### 3) Ollama Vision Model
- Install and run Ollama:
  ```bash
  # Install Ollama (macOS)
  curl -fsSL https://ollama.ai/install.sh | sh
  ollama serve
  ```
- Pull a vision model:
  ```bash
  ollama pull llava:13b
  # or
  ollama pull qwen2.5-vl  # if available
  ```

### 4) Start the API server
```bash
uvicorn web.backend.main:app --reload --port 8000
```

## API Endpoints

### Extract blocks from a pattern
```bash
# DocLayNet only (geometry)
curl -X POST "http://localhost:8000/api/patterns/{pattern_id}/extract?ai_detect=true&ai_model=doclayout&imgsz=1536&tile_size=640&tile_overlap=160"

# Ollama VLM only (semantic labels)
curl -X POST "http://localhost:8000/api/patterns/{pattern_id}/extract?ai_detect=true&ai_model=ollama_vl"

# Both: DocLayNet + llava:13b (recommended)
curl -X POST "http://localhost:8000/api/patterns/{pattern_id}/extract?ai_detect=true&ai_model=both&imgsz=1536&tile_size=640&tile_overlap=160"
```

#### Parameters
- `ai_detect`: true/false to enable AI
- `ai_model`: `doclayout`, `ollama_vl`, `both`, `yolov8`
- `imgsz`: Inference resize (e.g., 1280, 1536)
- `tile_size`: SAHI slice size (default 640)
- `tile_overlap`: SAHI overlap (default 100)

### Regenerate thumbnails
```bash
curl -X POST "http://localhost:8000/api/patterns/thumbnails/generate"
```

## How It Works

### 1) Per-page processing
- For each page, we have:
  - PDF vector elements (texts, rectangles, lines)
  - PNG rendering for CV and AI
- CV line merging (OpenCV) adds missing verticals/horizontals.
- Thin rectangles from PDF are converted to line primitives to improve grid detection.

### 2) AI Detection
- **DocLayNet (YOLOv8)**: Detects `table`, `text_region`, `title`, `cell` via SAHI sliced inference.
  - Tables become `grid` blocks with optional column headers from nearby texts.
  - Text regions near the top become `header` blocks.
- **Ollama VLM**: Returns JSON with `labeled_inputs`, `grid_headers`, `checkbox_groups`, `header_title`.
  - Only kept if the bounding boxes IoU-match real PDF rectangles (prevents hallucinations).

### 3) Fusion & Pruning
- AI detections are deduped (IoU > 0.6).
- **Strict filters**:
  - Generic AI shapes are never added.
  - AI checkboxes/labeled_inputs are kept only if they match a PDF rectangle and are not in the top 20% of the page.
  - CV contour checkbox lists are disabled (grid artifacts were being added).
- Result: Only elements present in the original PDF are rendered.

### 4) Output
- `extracted/blocks.json`: Structured blocks with types: `grid`, `header`, `checkbox_list`, `labeled_input`, `text_region`.
- `extracted/elements.json`: Flattened elements for rendering.
- `thumbnail.png`: Visual overlay showing detected blocks.

## Example Workflow

```bash
# 1. Analyze a PDF (if not already done)
python main.py analyze path/to/planner.pdf --pattern-id my-planner

# 2. Extract with both AI models
curl -X POST "http://localhost:8000/api/patterns/my-planner/extract?ai_detect=true&ai_model=both&imgsz=1536&tile_size=640&tile_overlap=160"

# 3. Generate thumbnail to visually verify
curl -X POST "http://localhost:8000/api/patterns/thumbnails/generate"

# 4. View results
open data/patterns/my-planner/thumbnail.png
cat data/patterns/my-planner/extracted/blocks.json | jq '.blocks[] | {type, source, page}'
```

## Troubleshooting

- Server crashes with `np.float_` error: Ensure `numpy<2.0` is installed (`pip install "numpy<2.0"`).
- Ollama “model not found”: Pull the model (`ollama pull llava:13b`).
- No DocLayNet detections: Place weights at `models/doclayout/yolov8_doclaynet.pt` or set `DOCLAYOUT_WEIGHTS`.
- Gray squares in overlay: Fixed by disabling CV contour checkbox lists and adding top-margin filters.

## File Structure

```
web/backend/services/
├── ai_vision.py          # DocLayNet + Ollama VLM detection
├── block_extractor.py   # Fusion logic and block creation
└── pattern_db.py         # Optional ChromaDB storage

models/doclayout/
└── yolov8_doclaynet.pt   # Local DocLayNet weights (optional)

data/patterns/{pattern_id}/
├── analysis/             # Per-page JSON + PNG
└── extracted/
    ├── blocks.json       # Structured blocks
    ├── elements.json     # Flattened elements
    └── thumbnail.png     # Visual overlay
```

## Extending

- Add new AI models by implementing a `detect_*` function in `ai_vision.py` and updating the `detect` dispatcher.
- Adjust pruning thresholds in `block_extractor.py` (top-margin, IoU, size).
- Add new block types (e.g., `signature`, `watermark`) by updating flattening and fusion logic.

## Dependencies

- `ultralytics`: YOLOv8
- `sahi`: Sliced inference for small objects
- `ollama`: Vision LLM client
- `opencv-python`: CV line merging and contour detection
- `huggingface_hub`: Optional model download
- `chromadb`: Vector storage (optional)
- `numpy<2.0`: ChromaDB compatibility
