from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import math

# Coordinate system expected: top-left (as produced by pdf_parser.analyze_pdf)

def _load_pages(analysis_dir: Path) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    if not analysis_dir.exists():
        return pages
    for p in sorted(analysis_dir.glob("page_*.json")):
        try:
            pages.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return pages


def _group_by_y(items: List[Dict[str, Any]], tol: float = 20.0) -> List[List[Dict[str, Any]]]:
    if not items:
        return []
    items_sorted = sorted(items, key=lambda it: it.get("y", 0.0))
    clusters: List[List[Dict[str, Any]]] = []
    for it in items_sorted:
        placed = False
        for cluster in clusters:
            cy = sum(c.get("y", 0.0) for c in cluster) / max(1, len(cluster))
            if abs(it.get("y", 0.0) - cy) <= tol:
                cluster.append(it)
                placed = True
                break
        if not placed:
            clusters.append([it])
    return clusters


def _find_header(texts: List[Dict[str, Any]], page_h: float) -> Dict[str, Any] | None:
    # Heuristic: wide text near top 25% of page
    candidates = [t for t in texts if t.get("y", 0) < page_h * 0.25]
    if not candidates:
        return None
    header = max(candidates, key=lambda t: (t.get("width", 0), -t.get("y", 0)))
    return header


def _find_weekly_rows(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Find clusters of 7 small rectangles on similar Y
    rows: List[Dict[str, Any]] = []
    rect_rows = _group_by_y([r for r in rects if 14 <= r.get("width", 0) <= 30 and 14 <= r.get("height", 0) <= 30], tol=25)
    for row in rect_rows:
        if len(row) < 7:
            continue
        # Try to take 7 by sorting x
        row_sorted = sorted(row, key=lambda r: r.get("x", 0))
        row7 = row_sorted[:7]
        # Attach labels: text just above within 60 px window, closest in y
        labels: List[Dict[str, Any]] = []
        for r in row7:
            rx = r.get("x", 0)
            ry = r.get("y", 0)
            best: Dict[str, Any] | None = None
            best_dy = 1e9
            for t in texts:
                tx = t.get("x", 0)
                ty = t.get("y", 0)
                if ty + t.get("height", 0) <= ry - 5 and abs((tx + t.get("width", 0) / 2) - (rx + r.get("width", 0) / 2)) < 60:
                    dy = ry - ty
                    if dy < best_dy and dy <= 80:
                        best = t
                        best_dy = dy
            if best:
                labels.append(best)
        block = {
            "type": "weekly_row",
            "rects": row7,
            "labels": labels,
        }
        rows.append(block)
    return rows


def _find_notes(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    big_rects = [r for r in rects if r.get("width", 0) >= 200 and r.get("height", 0) >= 100]
    for r in big_rects:
        # find a 'Notes' label near above/left if exists
        lbl = None
        for t in texts:
            content = (t.get("properties", {}).get("text") or "").strip().lower()
            if "note" in content:
                if abs(t.get("y", 0) - r.get("y", 0)) <= 80 and t.get("x", 0) <= r.get("x", 0) + 40:
                    lbl = t
                    break
        notes.append({"type": "notes", "rect": r, "label": lbl})
    return notes


def _flatten_blocks_to_elements(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = []
    for b in blocks:
        if b.get("type") == "header" and b.get("text"):
            t = b["text"].copy()
            t["properties"] = t.get("properties", {})
            t["properties"].setdefault("fontFamily", "Helvetica")
            t["properties"].setdefault("fontSize", 36)
            t["properties"].setdefault("color", "#2C2C2C")
            elements.append(t)
        elif b.get("type") == "weekly_row":
            for r in b.get("rects", []):
                rr = r.copy()
                rr["properties"] = {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}
                elements.append(rr)
            for t in b.get("labels", []):
                tt = t.copy()
                tt["properties"] = tt.get("properties", {})
                tt["properties"].setdefault("fontFamily", "Helvetica")
                tt["properties"].setdefault("fontSize", 14)
                tt["properties"].setdefault("color", "#2C2C2C")
                elements.append(tt)
        elif b.get("type") == "notes":
            r = b.get("rect")
            if r:
                rr = r.copy()
                rr["properties"] = {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}
                elements.append(rr)
            lbl = b.get("label")
            if lbl:
                tt = lbl.copy()
                tt["properties"] = tt.get("properties", {})
                tt["properties"].setdefault("fontFamily", "Helvetica")
                tt["properties"].setdefault("fontSize", 14)
                tt["properties"].setdefault("color", "#2C2C2C")
                elements.append(tt)
    return elements


def extract_blocks(pattern_dir: Path) -> Dict[str, Any]:
    analysis_dir = pattern_dir / "analysis"
    pages = _load_pages(analysis_dir)
    if not pages:
        return {"success": False, "error": "no analysis pages found"}

    all_blocks: List[Dict[str, Any]] = []

    for page in pages:
        page_w = float(page.get("width", 0))
        page_h = float(page.get("height", 0))
        elems = page.get("elements", [])
        texts = [e for e in elems if e.get("type") == "text"]
        rects = [e for e in elems if e.get("type") == "rectangle"]
        lines = [e for e in elems if e.get("type") == "line"]

        header = _find_header(texts, page_h)
        if header:
            all_blocks.append({"type": "header", "text": header, "page": page.get("page_index", 0)})

        weekly = _find_weekly_rows(rects, texts)
        for w in weekly:
            w["page"] = page.get("page_index", 0)
            all_blocks.append(w)

        note_blocks = _find_notes(rects, texts)
        for nb in note_blocks:
            nb["page"] = page.get("page_index", 0)
            all_blocks.append(nb)

    # Flatten to normalized elements list as a starting point
    elements = _flatten_blocks_to_elements(all_blocks)

    # Write outputs
    out_dir = pattern_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocks.json").write_text(json.dumps({"blocks": all_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "elements.json").write_text(json.dumps({"elements": elements}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"success": True, "blocks": all_blocks, "elements": elements}
