from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json

# Optional import to avoid hard failure if PyMuPDF isn't installed yet
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _rect_to_tuple(r: Any) -> Tuple[float, float, float, float]:
    # r: fitz.Rect or (x0,y0,x1,y1)
    try:
        return float(r.x0), float(r.y0), float(r.x1), float(r.y1)
    except Exception:
        x0, y0, x1, y1 = r
        return float(x0), float(y0), float(x1), float(y1)


def _extract_text(page: "fitz.Page") -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        # Aggregate the block bbox
        x0, y0, x1, y1 = _rect_to_tuple(block.get("bbox", (0, 0, 0, 0)))
        text_content: List[str] = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                s = span.get("text", "")
                if s:
                    text_content.append(s)
        full_text = " ".join(text_content).strip()
        if not full_text:
            continue
        items.append({
            "type": "text",
            "x": x0,
            "y": y0,
            "width": max(1.0, x1 - x0),
            "height": max(1.0, y1 - y0),
            "properties": {
                "text": full_text,
                "fontSize": 12,  # estimated; refined later if needed
                "fontFamily": "Helvetica",
                "color": "#2C2C2C",
                "align": "left"
            }
        })
    return items


def _extract_drawings(page: "fitz.Page") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rectangles: List[Dict[str, Any]] = []
    lines: List[Dict[str, Any]] = []
    drawings = page.get_drawings()
    for d in drawings:
        # Prefer a direct rect when present
        rect_obj = d.get("rect")
        if rect_obj:
            x0, y0, x1, y1 = _rect_to_tuple(rect_obj)
            rectangles.append({
                "type": "rectangle",
                "x": x0,
                "y": y0,
                "width": max(1.0, x1 - x0),
                "height": max(1.0, y1 - y0),
                "properties": {
                    "fill": "transparent",
                    "stroke": "#CCCCCC",
                    "strokeWidth": 0.5
                }
            })
            continue
        # Otherwise, approximate from path points
        pts: List[Tuple[float, float]] = []
        for it in d.get("items", []):
            if it[0] in ("l", "c", "re", "qu"):
                # it = (op, p1, p2, ...)
                for p in it[1:]:
                    try:
                        pts.append((float(p.x), float(p.y)))
                    except Exception:
                        try:
                            x, y = p
                            pts.append((float(x), float(y)))
                        except Exception:
                            pass
        if len(pts) >= 2:
            # treat as a polyline; add a line covering full bbox width
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
            if w > 2 and h > 2:
                rectangles.append({
                    "type": "rectangle",
                    "x": x0,
                    "y": y0,
                    "width": w,
                    "height": h,
                    "properties": {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}
                })
            else:
                lines.append({
                    "type": "line",
                    "x": x0,
                    "y": y0,
                    "width": w,
                    "height": 0,
                    "properties": {"stroke": "#CCCCCC", "strokeWidth": 0.5}
                })
    return rectangles, lines


def analyze_pdf(pattern_dir: Path) -> Dict[str, Any]:
    if fitz is None:
        return {"success": False, "error": "PyMuPDF (fitz) not installed. Run: pip install PyMuPDF"}

    pdf_path = pattern_dir / "original.pdf"
    if not pdf_path.exists():
        return {"success": False, "error": f"PDF not found: {pdf_path}"}

    out_dir = pattern_dir / "analysis"
    _ensure_dir(out_dir)

    doc = fitz.open(pdf_path)
    pages_summary: List[Dict[str, Any]] = []

    for i, page in enumerate(doc):
        # Extract primitives
        texts = _extract_text(page)
        rects, lines = _extract_drawings(page)
        elements = texts + rects + lines

        # Save page JSON
        page_json_path = out_dir / f"page_{i+1}.json"
        with page_json_path.open("w", encoding="utf-8") as f:
            json.dump({
                "page_index": i,
                "width": float(page.rect.width),
                "height": float(page.rect.height),
                "elements": elements,
                "coord_system": "top-left"
            }, f, ensure_ascii=False, indent=2)

        # Save raster preview
        try:
            pix = page.get_pixmap(alpha=False)
            (out_dir / f"page_{i+1}.png").write_bytes(pix.tobytes("png"))
        except Exception:
            pass

        pages_summary.append({
            "index": i,
            "elements": len(elements),
            "json": str(page_json_path)
        })

    doc.close()

    # Write an index file
    index_path = out_dir / "index.json"
    summary = {"pages": pages_summary}
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {"success": True, "pages": pages_summary, "index": str(index_path)}
