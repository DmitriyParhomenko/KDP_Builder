"""
Local AI visual detector for PDF pages (YOLOv8/doclayout).
Detects tables, cells, checkboxes, text regions, and shapes.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
import os
import numpy as np
from PIL import Image

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False

# Optional: SAHI for sliced inference
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except Exception:
    SAHI_AVAILABLE = False

# Ollama client for vision models
try:
    import ollama
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False

# HuggingFace Hub for model download
try:
    from huggingface_hub import hf_hub_download
    HF_HUB_AVAILABLE = True
except Exception:
    HF_HUB_AVAILABLE = False

# Global model cache
_yolo_model = None
_doclayout_model = None
_ollama_client = None

def _load_model():
    """Load YOLOv8 model once and cache."""
    global _yolo_model
    if _yolo_model is None and YOLO_AVAILABLE:
        _yolo_model = YOLO("yolov8n.pt")
    return _yolo_model

def _map_yolo_class_to_our(cls_name: str) -> str:
    """Map generic YOLOv8 classes to our simplified schema."""
    lowered = cls_name.lower()
    if "table" in lowered or "cell" in lowered:
        return "table"
    if "book" in lowered or "laptop" in lowered or "tv" in lowered:
        return "text_region"
    if "remote" in lowered or "mouse" in lowered or "keyboard" in lowered or "cell phone" in lowered or "traffic light" in lowered:
        return "checkbox"
    return "shape"

def _get_doclayout_model():
    """Load a document-layout YOLO model once.

    Order of preference:
    1) Local path from env DOCLAYOUT_WEIGHTS (skip HF if set)
    2) HuggingFace download if configured
    3) Fallback to generic yolov8n.pt
    """
    global _doclayout_model
    if _doclayout_model is None and YOLO_AVAILABLE and SAHI_AVAILABLE:
        # 1) Local weights via env (skip HF if this is set)
        env_path = os.getenv("DOCLAYOUT_WEIGHTS")
        if env_path and Path(env_path).exists():
            try:
                _doclayout_model = AutoDetectionModel.from_pretrained(
                    model_type="yolov8",
                    model_path=env_path,
                    confidence_threshold=0.25,
                    device="cpu",
                )
                print(f"✅ Loaded DocLayout from local weights: {env_path}")
                return _doclayout_model
            except Exception as e:
                print(f"⚠️ Failed to load DocLayout weights from {env_path}: {e}")

        # 2) HuggingFace (only if DOCLAYOUT_WEIGHTS not set)
        if not env_path and HF_HUB_AVAILABLE:
            try:
                repo_id = os.getenv("DOCLAYOUT_HF_REPO", "microsoft/DocLayNet-yolov8")
                filename = os.getenv("DOCLAYOUT_HF_FILE", "yolov8n_doclaynet.pt")
                model_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    cache_dir="models/doclayout"
                )
                _doclayout_model = AutoDetectionModel.from_pretrained(
                    model_type="yolov8",
                    model_path=model_path,
                    confidence_threshold=0.25,
                    device="cpu",
                )
                print(f"✅ Loaded DocLayout from HuggingFace: {repo_id}/{filename}")
                return _doclayout_model
            except Exception as e:
                print(f"⚠️ Failed to load DocLayout from HuggingFace: {e}")

        # 3) Fallback: generic yolov8n
        _doclayout_model = AutoDetectionModel.from_pretrained(
            model_type="yolov8",
            model_path="yolov8n.pt",
            confidence_threshold=0.25,
            device="cpu",
        )
        print("⚠️ Using generic yolov8n.pt as DocLayout fallback")
    return _doclayout_model

def _get_ollama_client():
    """Return Ollama client if available."""
    global _ollama_client
    if _ollama_client is None and OLLAMA_AVAILABLE:
        _ollama_client = ollama.Client()
    return _ollama_client

def detect_doclayout(image_path: Path, conf_threshold: float = 0.25, imgsz: int = 1280, tile_size: int = 640, tile_overlap: int = 100) -> List[Dict[str, Any]]:
    """Detect document elements using DocLayNet YOLOv8 with SAHI slicing."""
    model = _get_doclayout_model()
    if model is None:
        return []
    result = get_sliced_prediction(
        image=str(image_path),
        detection_model=model,
        slice_height=tile_size,
        slice_width=tile_size,
        overlap_height_ratio=tile_overlap / tile_size,
        overlap_width_ratio=tile_overlap / tile_size,
    )
    detections = []
    for obj in result.object_prediction_list:
        bbox = obj.bbox.to_xywh()
        detections.append({
            "class": obj.category.name,
            "confidence": obj.score.value,
            "bbox": {"x": bbox[0], "y": bbox[1], "width": bbox[2], "height": bbox[3]},
        })
    return detections

def detect_ollama_vl(image_path: Path, model: str = "llava:13b", prompt: str = None) -> List[Dict[str, Any]]:
    """Detect semantic regions and labels via Ollama vision model (JSON-only response)."""
    client = _get_ollama_client()
    if client is None:
        return []
    if prompt is None:
        prompt = (
            "You are a document analyzer. Return only a JSON object with the following keys: "
            "header_title (string), labeled_inputs (array of {label_text, bbox: [x,y,w,h]}), "
            "grid_headers (array of strings), checkbox_groups (array of bbox). "
            "Coordinates are in pixels, origin top-left. Do not include explanations."
        )
    try:
        response = client.chat(
            model=model,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [str(image_path)],
            }],
        )
        import re
        txt = response["message"]["content"]
        # Extract JSON block
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            return []
        data = json.loads(m.group(0))
        # Normalize to detection-like list
        detections = []
        if data.get("header_title"):
            # We'll let the extractor handle title via text grouping; skip bbox here
            pass
        for li in data.get("labeled_inputs", []):
            if "bbox" in li and len(li["bbox"]) == 4:
                detections.append({
                    "class": "labeled_input",
                    "label": li.get("label_text", ""),
                    "bbox": {"x": li["bbox"][0], "y": li["bbox"][1], "width": li["bbox"][2], "height": li["bbox"][3]},
                })
        for cb in data.get("checkbox_groups", []):
            if len(cb) == 4:
                detections.append({
                    "class": "checkbox",
                    "bbox": {"x": cb[0], "y": cb[1], "width": cb[2], "height": cb[3]},
                })
        return detections
    except Exception as e:
        print(f"⚠️ Ollama VL detection failed: {e}")
        return []

def detect(image_path: Path, conf_threshold: float = 0.01, ai_model: str = "doclayout", imgsz: int = 1280, tile_size: int = 640, tile_overlap: int = 100) -> List[Dict[str, Any]]:
    """Unified detection entrypoint supporting doclayout, ollama_vl, yolov8, or both."""
    detections = []
    if ai_model in ("doclayout", "both"):
        detections.extend(detect_doclayout(image_path, conf_threshold=conf_threshold, imgsz=imgsz, tile_size=tile_size, tile_overlap=tile_overlap))
    if ai_model in ("ollama_vl", "both"):
        detections.extend(detect_ollama_vl(image_path))
    if ai_model == "yolov8":
        # fallback to generic COCO YOLOv8
        model = _load_model()
        if model is None:
            return []
        results = model(str(image_path), conf=conf_threshold, verbose=False)
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
    return detections

def save_detections(detections: List[Dict[str, Any]], output_path: Path):
    """Persist detections to JSON."""
    output_path.write_text(json.dumps(detections, indent=2), encoding="utf-8")
