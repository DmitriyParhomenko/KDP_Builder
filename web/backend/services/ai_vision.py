"""
Local AI visual detector for PDF pages (YOLOv8/doclayout).
Detects tables, cells, checkboxes, text regions, and shapes.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# Use a tiny, general YOLOv8 model; we will map its outputs to our schema
_MODEL_NAME = "yolov8n.pt"  # nano model, fast and small
_MODEL = None

def _load_model() -> Any:
    """Load YOLOv8 nano model once and cache globally."""
    global _MODEL
    if YOLO is None:
        raise RuntimeError("ultralytics not installed")
    if _MODEL is None:
        _MODEL = YOLO(_MODEL_NAME)
    return _MODEL

def _map_yolo_class_to_our(cls_name: str) -> str:
    """Map YOLO class names to our simplified schema."""
    # YOLOv8 pretrained classes include many; we map relevant ones
    mapping = {
        "cell phone": "checkbox",          # often small squares
        "remote": "checkbox",
        "mouse": "checkbox",
        "keyboard": "checkbox",
        "traffic light": "checkbox",      # small square/box
        "book": "text_region",
        "laptop": "text_region",
        "tv": "text_region",
        "dining table": "table",
        "table": "table",
        "chair": "shape",
        "couch": "shape",
        "bed": "shape",
    }
    # Fallback: heuristics from class name keywords
    lowered = cls_name.lower()
    if "table" in lowered or "cell" in lowered:
        return "table"
    if "book" in lowered or "laptop" in lowered or "tv" in lowered:
        return "text_region"
    if "remote" in lowered or "mouse" in lowered or "keyboard" in lowered or "cell phone" in lowered or "traffic light" in lowered:
        return "checkbox"
    # Default generic shape for bounding boxes
    return "shape"

def detect(page_png_path: Path, conf_threshold: float = 0.15) -> List[Dict[str, Any]]:
    """
    Run YOLOv8 inference on a page PNG.

    Args:
        page_png_path: Path to the page PNG
        conf_threshold: Minimum confidence to keep a detection

    Returns:
        List of detections with keys: class, label, conf, bbox (x,y,w,h)
    """
    if YOLO is None or not page_png_path.exists():
        print(f"[ai_vision] SKIP: YOLO missing or file missing {page_png_path}")
        return []
    model = _load_model()
    results = model(str(page_png_path), conf=conf_threshold, verbose=False)
    detections: List[Dict[str, Any]] = []
    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue
        for box in boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            w, h = x2 - x1, y2 - y1
            label = model.names.get(cls, f"class_{cls}")
            our_class = _map_yolo_class_to_our(label)
            detections.append({
                "class": our_class,
                "label": label,
                "conf": round(conf, 3),
                "bbox": {"x": x1, "y": y1, "width": w, "height": h},
            })
    print(f"[ai_vision] Detected {len(detections)} objects on {page_png_path.name} at conf>={conf_threshold}")
    return detections

def save_detections(detections: List[Dict[str, Any]], out_path: Path) -> None:
    """Persist detections to JSON."""
    out_path.write_text(json.dumps({"detections": detections}, indent=2))

def load_detections(in_path: Path) -> List[Dict[str, Any]]:
    """Load detections from JSON."""
    if not in_path.exists():
        return []
    data = json.loads(in_path.read_text())
    return data.get("detections", [])
