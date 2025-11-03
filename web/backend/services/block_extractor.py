from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import math

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

# Coordinate system expected: top-left (as produced by pdf_parser.analyze_pdf)

def _iou(box_a: Dict[str, Any], box_b: Dict[str, Any]) -> float:
    """Compute Intersection over Union for two boxes with x,y,w,h."""
    x1 = max(box_a.get("x", 0), box_b.get("x", 0))
    y1 = max(box_a.get("y", 0), box_b.get("y", 0))
    x2 = min(box_a.get("x", 0) + box_a.get("width", 0), box_b.get("x", 0) + box_b.get("width", 0))
    y2 = min(box_a.get("y", 0) + box_a.get("height", 0), box_b.get("y", 0) + box_b.get("height", 0))
    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter = inter_w * inter_h
    area_a = box_a.get("width", 0) * box_a.get("height", 0)
    area_b = box_b.get("width", 0) * box_b.get("height", 0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def _merge_lines_cv(page_png_path: Path, dpi_scale: float = 1.0) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Use OpenCV to merge fragmented lines via morphological operations.
    Returns merged horizontal and vertical line primitives.
    """
    if cv2 is None or np is None or not page_png_path.exists():
        return [], []
    img = cv2.imread(str(page_png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return [], []
    # Binarize
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Morphological close to connect gaps
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (int(25 * dpi_scale), 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(25 * dpi_scale)))
    closed_h = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h)
    closed_v = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v)
    # HoughLinesP
    def _lines_from_image(closed_img, orientation):
        # Use a consistent theta step; filter orientation by slope
        lines = cv2.HoughLinesP(
            closed_img,
            rho=1,
            theta=np.pi/180,
            threshold=30,
            minLineLength=int(40 * dpi_scale),
            maxLineGap=int(12 * dpi_scale),
        )
        if lines is None:
            return []
        result = []
        for l in lines:
            x1, y1, x2, y2 = l[0]
            if orientation == 'h':
                # Ensure horizontal
                if abs(y2 - y1) > 5:
                    continue
                x, y = min(x1, x2), (y1 + y2) / 2.0
                w = abs(x2 - x1)
                result.append({"type": "line", "x": x / dpi_scale, "y": y / dpi_scale, "width": w / dpi_scale, "height": 0.0, "properties": {}})
            else:
                # Ensure vertical
                if abs(x2 - x1) > 5:
                    continue
                x, y = (x1 + x2) / 2.0, min(y1, y2)
                h = abs(y2 - y1)
                result.append({"type": "line", "x": x / dpi_scale, "y": y / dpi_scale, "width": 0.0, "height": h / dpi_scale, "properties": {}})
        return result
    merged_h = _lines_from_image(closed_h, 'h')
    merged_v = _lines_from_image(closed_v, 'v')
    return merged_h, merged_v


def _find_contour_checkboxes(page_png_path: Path, dpi_scale: float = 1.0) -> List[Dict[str, Any]]:
    """
    Detect checkboxes via contours (small squares) using OpenCV.
    Returns list of rectangle primitives.
    """
    if cv2 is None or np is None or not page_png_path.exists():
        return []
    img = cv2.imread(str(page_png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    checkboxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Filter small squares
        if 8 <= w / dpi_scale <= 30 and 8 <= h / dpi_scale <= 30 and abs(w - h) <= max(6, 0.3 * max(w, h)):
            checkboxes.append({"type": "rectangle", "x": x / dpi_scale, "y": y / dpi_scale, "width": w / dpi_scale, "height": h / dpi_scale, "properties": {}})
    return checkboxes


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

def _find_header_group(texts: List[Dict[str, Any]], page_w: float, page_h: float) -> Dict[str, Any] | None:
    """Fallback header by grouping multiple text spans near the top and returning their union as a header box."""
    tops = [t for t in texts if t.get("y", 0) < page_h * 0.3]
    if not tops:
        return None
    # cluster by baseline y
    clusters = _group_by_y(tops, tol=24)
    best = []
    best_cov = 0.0
    for cl in clusters:
        min_x = min(t.get("x", 0) for t in cl)
        max_x = max(t.get("x", 0) + t.get("width", 0) for t in cl)
        width = max(0.0, max_x - min_x)
        cov = width / max(1.0, page_w)
        if cov > best_cov:
            best_cov = cov; best = cl
    if not best or best_cov < 0.25:
        return None
    x0 = min(t.get("x", 0) for t in best)
    y0 = min(t.get("y", 0) for t in best)
    x1 = max(t.get("x", 0) + t.get("width", 0) for t in best)
    y1 = max(t.get("y", 0) + t.get("height", 0) for t in best)
    return {"type": "text", "x": float(x0), "y": float(y0), "width": float(x1 - x0), "height": float(y1 - y0), "properties": {}}


def _median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    m = n // 2
    return (s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0)


def _find_weekly_rows(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find clusters of 7 small checkboxes in a row with labels above.
    Heuristics:
    - Rect size ~ 14..30
    - Group by Y (tol=18)
    - Within a row, look for a run of 7 with consistent width and spacing (relative stdev < 0.25)
    - Attach nearest label above each rect within horizontal center tolerance
    """
    rows: List[Dict[str, Any]] = []
    small_rects = [r for r in rects if 14 <= r.get("width", 0) <= 30 and 14 <= r.get("height", 0) <= 30]
    rect_rows = _group_by_y(small_rects, tol=18)
    for row in rect_rows:
        if len(row) < 7:
            continue
        row_sorted = sorted(row, key=lambda r: r.get("x", 0))
        # Precompute centers and gaps
        centers = [r.get("x", 0) + r.get("width", 0) / 2 for r in row_sorted]
        widths = [r.get("width", 0) for r in row_sorted]
        gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        med_w = _median(widths)
        med_gap = _median(gaps) if gaps else 0
        for i in range(0, len(row_sorted) - 6):
            run = row_sorted[i:i + 7]
            run_centers = centers[i:i + 7]
            run_widths = [r.get("width", 0) for r in run]
            run_gaps = [run_centers[j + 1] - run_centers[j] for j in range(6)]
            # consistency checks
            if med_gap <= 0:
                continue
            if any(w < 10 or w > 36 for w in run_widths):
                continue
            # relative stddev of gaps within tolerance
            mean_gap = sum(run_gaps) / len(run_gaps)
            var_gap = sum((g - mean_gap) ** 2 for g in run_gaps) / len(run_gaps)
            rel_std = math.sqrt(var_gap) / max(1e-6, mean_gap)
            if rel_std > 0.25:
                continue
            # Attach labels for this run
            labels: List[Dict[str, Any]] = []
            for r in run:
                rx = r.get("x", 0)
                rw = r.get("width", 0)
                ry = r.get("y", 0)
                cx = rx + rw / 2
                best: Dict[str, Any] | None = None
                best_score = 1e9
                for t in texts:
                    tx = t.get("x", 0)
                    tw = t.get("width", 0)
                    ty = t.get("y", 0)
                    th = t.get("height", 0)
                    t_center = tx + tw / 2
                    # label above within vertical window and horizontally near center
                    if ty + th <= ry - 5 and ry - ty <= 90 and abs(t_center - cx) <= max(60, mean_gap / 2):
                        score = (abs(t_center - cx)) + 0.5 * (ry - ty)
                        if score < best_score:
                            best = t
                            best_score = score
                if best:
                    labels.append(best)
            rows.append({"type": "weekly_row", "rects": run, "labels": labels})
            break  # one run per row is enough
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


def _quantize(val: float, step: float) -> float:
    return round(val / step) * step


def _find_grids(rects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect rectangular grids (e.g., calendars) by uniform cell size and regular gaps.
    Returns blocks with type 'grid' and list of cells.
    """
    blocks: List[Dict[str, Any]] = []
    if not rects:
        return blocks
    # candidate cells: moderate rectangles
    cells = [r for r in rects if r.get("width", 0) >= 20 and r.get("height", 0) >= 15]
    if len(cells) < 6:
        return blocks
    # group by approximate size using quantization
    groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for r in cells:
        qw = int(_quantize(r.get("width", 0.0), 5.0))
        qh = int(_quantize(r.get("height", 0.0), 5.0))
        groups.setdefault((qw, qh), []).append(r)
    for (qw, qh), group in groups.items():
        if len(group) < 9:
            continue
        # derive rows and cols by quantizing x and y
        xs = sorted(set(int(_quantize(g.get("x", 0.0), 5.0)) for g in group))
        ys = sorted(set(int(_quantize(g.get("y", 0.0), 5.0)) for g in group))
        rows_n = len(ys)
        cols_n = len(xs)
        if rows_n >= 3 and cols_n >= 3 and rows_n * cols_n <= len(group) * 1.5:
            # compute outer bounds
            min_x = min(g.get("x", 0.0) for g in group)
            min_y = min(g.get("y", 0.0) for g in group)
            max_x = max(g.get("x", 0.0) + g.get("width", 0.0) for g in group)
            max_y = max(g.get("y", 0.0) + g.get("height", 0.0) for g in group)
            blocks.append({
                "type": "grid",
                "rows": rows_n,
                "cols": cols_n,
                "bounds": {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y},
                "cells": group,
            })
    return blocks


def _infer_grid_from_parallel_lines(lines: List[Dict[str, Any]], page_w: float, page_h: float) -> List[Dict[str, Any]]:
    """Infer a grid from many parallel horizontal lines with similar x and width, even if verticals are missing."""
    if not lines:
        return []
    # Filter horizontal line elements
    hs = []
    for l in lines:
        w = float(l.get("width", 0))
        h = float(l.get("height", 0))
        if w > 20 and abs(h) < 1e-3:
            hs.append(l)
    if len(hs) < 8:
        return []
    # Cluster by left x and width
    def q(v, q=5.0):
        return int(round(float(v) / q) * q)
    clusters = {}
    for l in hs:
        key = (q(l.get("x", 0), 5.0), q(l.get("width", 0), 10.0))
        clusters.setdefault(key, []).append(l)
    # pick the largest cluster
    best_key = None
    best = []
    for k, v in clusters.items():
        if len(v) > len(best):
            best = v; best_key = k
    if len(best) < 8:
        return []
    xs = [b.get("x", 0) for b in best]
    ys = [b.get("y", 0) for b in best]
    ws = [b.get("width", 0) for b in best]
    min_x = min(xs); max_x = max([x + w for x, w in zip(xs, ws)])
    min_y = min(ys); max_y = max(ys)
    # Validate coverage and aspect
    if max_y - min_y < 60 or (max_x - min_x) < page_w * 0.2:
        return []
    lines_h = [{"type": "line", "x": b.get("x", 0), "y": b.get("y", 0), "width": b.get("width", 0), "height": 0.0, "properties": {}} for b in best]
    grid = {
        "type": "grid",
        "bounds": {"x": float(min_x), "y": float(min_y), "width": float(max_x - min_x), "height": float(max_y - min_y)},
        "lines_h": lines_h,
        "lines_v": [],
        "source": "inferred_h_lines",
    }
    return [grid]


def _thin_rects_to_lines(rects: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convert very thin rectangles to horizontal/vertical line primitives."""
    hs: List[Dict[str, Any]] = []
    vs: List[Dict[str, Any]] = []
    for r in rects or []:
        w = float(r.get("width", 0)); h = float(r.get("height", 0)); x = float(r.get("x", 0)); y = float(r.get("y", 0))
        if w >= 80 and h > 0 and h <= 3:
            hs.append({"type": "line", "x": x, "y": y + h / 2.0, "width": w, "height": 0.0, "properties": {}})
        elif h >= 80 and w > 0 and w <= 3:
            vs.append({"type": "line", "x": x + w / 2.0, "y": y, "width": 0.0, "height": h, "properties": {}})
    return hs, vs

def _find_grids_from_lines(lines: List[Dict[str, Any]], page_w: float, page_h: float) -> List[Dict[str, Any]]:
    """Detect table-like grids from stroke lines (horizontal/vertical).
    Accepts line primitives where horizontal lines have near-zero height and vertical lines have near-zero width.
    """
    blocks: List[Dict[str, Any]] = []
    if not lines:
        return blocks
    # Separate horizontal and vertical lines
    horizontals = [l for l in lines if abs(l.get("height", 0.0)) <= 2 and l.get("width", 0.0) >= 100]
    verticals = [l for l in lines if abs(l.get("width", 0.0)) <= 2 and l.get("height", 0.0) >= 100]
    if len(horizontals) < 3 or len(verticals) < 2:
        return blocks
    # Cluster by quantized positions to reduce DPI noise
    y_clusters = sorted(set(int(_quantize(h.get("y", 0.0), 5.0)) for h in horizontals))
    x_clusters = sorted(set(int(_quantize(v.get("x", 0.0), 5.0)) for v in verticals))
    if len(y_clusters) < 3 or len(x_clusters) < 2:
        return blocks
    # Compute outer bounds from horizontal spans and vertical spans
    min_x = min((h.get("x", 0.0) for h in horizontals), default=0.0)
    max_x = max((h.get("x", 0.0) + h.get("width", 0.0) for h in horizontals), default=page_w)
    min_y = min((min(h.get("y", 0.0), v.get("y", 0.0)) for v in verticals for h in horizontals), default=0.0)
    max_y = max((max(h.get("y", 0.0), v.get("y", 0.0) + v.get("height", 0.0)) for v in verticals for h in horizontals), default=page_h)
    bw, bh = float(max_x - min_x), float(max_y - min_y)
    # Reject tiny or edge artifacts
    if bw < 200 or bh < 120:
        return blocks
    # Coverage checks: average line lengths should cover majority of bounds
    avg_h_len = (_median([h.get("width", 0.0) for h in horizontals]) or 0.0)
    avg_v_len = (_median([v.get("height", 0.0) for v in verticals]) or 0.0)
    if bw > 0 and bh > 0:
        if (avg_h_len / bw) < 0.6 or (avg_v_len / bh) < 0.6:
            return blocks
    bounds = {"x": float(min_x), "y": float(min_y), "width": bw, "height": bh}
    blocks.append({
        "type": "grid",
        "rows": len(y_clusters),
        "cols": len(x_clusters),
        "bounds": bounds,
        "lines_h": horizontals,
        "lines_v": verticals,
    })
    return blocks


def _find_grids_from_merged_lines(merged_h: List[Dict[str, Any]], merged_v: List[Dict[str, Any]], page_w: float, page_h: float) -> List[Dict[str, Any]]:
    """Detect grids from CV-merged lines (more robust to gaps)."""
    blocks: List[Dict[str, Any]] = []
    if len(merged_h) < 3 or len(merged_v) < 2:
        return blocks
    # Cluster by quantized positions
    y_clusters = sorted(set(int(_quantize(h.get("y", 0.0), 5.0)) for h in merged_h))
    x_clusters = sorted(set(int(_quantize(v.get("x", 0.0), 5.0)) for v in merged_v))
    if len(y_clusters) < 3 or len(x_clusters) < 2:
        return blocks
    min_x = min((h.get("x", 0.0) for h in merged_h), default=0.0)
    max_x = max((h.get("x", 0.0) + h.get("width", 0.0) for h in merged_h), default=page_w)
    min_y = min((min(h.get("y", 0.0), v.get("y", 0.0)) for v in merged_v for h in merged_h), default=0.0)
    max_y = max((max(h.get("y", 0.0), v.get("y", 0.0) + v.get("height", 0.0)) for v in merged_v for h in merged_h), default=page_h)
    bw, bh = float(max_x - min_x), float(max_y - min_y)
    # Reject tiny candidates (likely text strokes) and those with insufficient lines
    if bw < 200 or bh < 120 or len(y_clusters) < 3 or len(x_clusters) < 3:
        return blocks
    # Coverage checks: median lengths should span most of bounds
    med_h_len = (_median([h.get("width", 0.0) for h in merged_h]) or 0.0)
    med_v_len = (_median([v.get("height", 0.0) for v in merged_v]) or 0.0)
    if (med_h_len / bw) < 0.6 or (med_v_len / bh) < 0.6:
        return blocks
    bounds = {"x": float(min_x), "y": float(min_y), "width": bw, "height": bh}
    blocks.append({
        "type": "grid",
        "rows": len(y_clusters),
        "cols": len(x_clusters),
        "bounds": bounds,
        "lines_h": merged_h,
        "lines_v": merged_v,
        "source": "cv_merged"
    })
    return blocks


def _find_checkbox_lists_from_contours(contour_checkboxes: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect checkbox + label pairs from CV-detected contours."""
    if not contour_checkboxes:
        return []
    entries: List[Dict[str, Any]] = []
    for b in contour_checkboxes:
        bx = b.get("x", 0)
        by = b.get("y", 0)
        bw = b.get("width", 0)
        bh = b.get("height", 0)
        # find nearest text to the right on same baseline window
        best = None
        best_dx = 1e9
        for t in texts:
            tx = t.get("x", 0)
            ty = t.get("y", 0)
            th = t.get("height", 0)
            # vertical overlap with box centerline
            if abs((ty + th / 2) - (by + bh / 2)) <= max(20, bh):
                dx = tx - (bx + bw)
                if 4 <= dx <= 500:
                    if dx < best_dx:
                        best = t
                        best_dx = dx
        entries.append({"rect": b, "label": best, "x": bx, "y": by})
    if len(entries) < 2:
        return []
    # simple single-column grouping for contours
    items = []
    for it in sorted(entries, key=lambda v: v["y"]):
        items.append({"rect": it["rect"], "label": it["label"]})
    if len(items) >= 4:
        blocks = [{"type": "checkbox_list", "items": items, "source": "cv_contour"}]
    else:
        blocks = []
    return blocks


def _find_checkbox_lists(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect checkbox + label pairs, group into list blocks (1-2 columns)."""
    # candidate checkboxes: small near-square rects
    boxes = [
        r for r in rects
        if 14 <= r.get("width", 0) <= 120
        and 14 <= r.get("height", 0) <= 120
        and abs(r.get("width", 0) - r.get("height", 0)) <= max(6, 0.25 * max(r.get("width", 0), r.get("height", 0)))
    ]
    if not boxes:
        return []
    entries: List[Dict[str, Any]] = []
    for b in boxes:
        bx = b.get("x", 0)
        by = b.get("y", 0)
        bw = b.get("width", 0)
        bh = b.get("height", 0)
        # find nearest text to the right on same baseline window
        best = None
        best_dx = 1e9
        for t in texts:
            tx = t.get("x", 0)
            ty = t.get("y", 0)
            th = t.get("height", 0)
            # vertical overlap with box centerline
            if abs((ty + th / 2) - (by + bh / 2)) <= max(20, bh):
                dx = tx - (bx + bw)
                if 4 <= dx <= 500:  # label 4..500 px to the right (handle larger DPI)
                    if dx < best_dx:
                        best = t
                        best_dx = dx
        entries.append({"rect": b, "label": best, "x": bx, "y": by})

    if len(entries) < 2:
        return []
    # group into 1-2 columns by x of boxes (use all boxes, even unlabeled)
    xs = sorted(p["x"] for p in entries)
    split = None
    if len(xs) >= 4:
        # try a simple two-cluster split using mid-gap
        gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
        max_gap, idx = max(gaps, key=lambda g: g[0])
        if max_gap > 200:  # likely two columns (tighter split to avoid mis-grouping)
            split = xs[idx]
    cols = [[], []] if split is not None else [[]]
    for p in entries:
        if split is None:
            cols[0].append(p)
        else:
            (cols[0] if p["x"] <= split else cols[1]).append(p)
    # Fallback: if one column has too few items, use single-column list
    if split is not None and (len(cols[0]) < 2 or len(cols[1]) < 2):
        cols = [[]]
        for p in entries:
            cols[0].append(p)
    # Build blocks per column set
    blocks: List[Dict[str, Any]] = []
    items = []
    for col in cols:
        for it in sorted(col, key=lambda v: v["y"]):
            items.append({"rect": it["rect"], "label": it["label"]})
    # require at least 4 items to avoid noise; labels optional
    if len(items) >= 4:
        blocks.append({"type": "checkbox_list", "items": items})
    return blocks


def _find_labeled_lines(rects: List[Dict[str, Any]], lines: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect label text with a long horizontal line represented either as a thin rectangle or a line primitive."""
    results: List[Dict[str, Any]] = []
    # candidate thin-rect lines
    rect_candidates = [r for r in (rects or []) if r.get("width", 0) >= 120 and 0 < r.get("height", 0) <= 6]
    # candidate line primitives
    line_candidates = [l for l in (lines or []) if l.get("width", 0) >= 120 and abs(l.get("height", 0)) <= 2]

    def _attach_label(lx: float, ly: float, lw: float) -> Dict[str, Any] | None:
        best = None
        best_dist = 1e9
        for t in texts:
            tx = t.get("x", 0)
            ty = t.get("y", 0)
            th = t.get("height", 0)
            if tx < lx and abs((ty + th / 2) - ly) <= 16 and (lx - (tx + t.get("width", 0))) <= 120:
                dist = lx - (tx + t.get("width", 0))
                if dist < best_dist:
                    best = t
                    best_dist = dist
        return best

    # From rectangles
    for ln in rect_candidates:
        lx = ln.get("x", 0)
        ly = ln.get("y", 0) + ln.get("height", 0) / 2.0
        lw = ln.get("width", 0)
        best = _attach_label(lx, ly, lw)
        results.append({"type": "labeled_line", "label": best, "line": {"x": lx, "y": ly, "width": lw}})

    # From line primitives
    for ln in line_candidates:
        lx = ln.get("x", 0)
        ly = ln.get("y", 0)
        lw = ln.get("width", 0)
        best = _attach_label(lx, ly, lw)
        results.append({"type": "labeled_line", "label": best, "line": {"x": lx, "y": ly, "width": lw}})

    return results


def _find_labeled_inputs(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect input rectangles with a label to the left or above (e.g., MONTH:, YEAR:, CLASS:)."""
    blocks: List[Dict[str, Any]] = []
    candidates = [r for r in rects if r.get("width", 0) >= 40 and 10 <= r.get("height", 0) <= 40]
    for r in candidates:
        rx, ry, rw, rh = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
        best = None
        best_score = 1e9
        # prefer label to the left, otherwise above
        for t in texts:
            tx = t.get("x", 0); ty = t.get("y", 0); tw = t.get("width", 0); th = t.get("height", 0)
            # left-label: vertically aligned, immediately left within 140px
            if (ry - th <= ty <= ry + rh) and (0 < rx - (tx + tw) <= 140):
                score = (rx - (tx + tw)) + abs((ty + th/2) - (ry + rh/2))
                if score < best_score:
                    best = t; best_score = score
            # above-label: centered horizontally and above within 100px
            if (tx <= rx + rw/2 <= tx + tw) and (0 < ry - (ty + th) <= 100):
                score = (ry - (ty + th))
                if score < best_score:
                    best = t; best_score = score
        if best:
            blocks.append({"type": "labeled_input", "rect": r, "label": best})
    return blocks


def _attach_grid_headers(grid: Dict[str, Any], texts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Attach column header text spans to a grid using vertical lines when available."""
    bounds = grid.get("bounds", {}) or {}
    x = bounds.get("x", 0.0); y = bounds.get("y", 0.0); w = bounds.get("width", 0.0); h = bounds.get("height", 0.0)
    if not w or not h:
        return grid
    # Build column spans from vertical lines if present, else try to split equally using known thin-rect verticals
    cols: List[Tuple[float, float]] = []
    vlines = grid.get("lines_v", []) or []
    if vlines and len(vlines) >= 2:
        xs = sorted([vl.get("x", x) for vl in vlines])
        # add grid left/right edges as boundaries if needed
        if xs[0] > x + 2: xs = [x] + xs
        if xs[-1] < x + w - 2: xs = xs + [x + w]
        for i in range(len(xs) - 1):
            cols.append((xs[i], xs[i + 1]))
    else:
        # fallback: 5 equal columns (common for expenses table)
        N = 5
        step = w / N if N else 0
        for i in range(N):
            cols.append((x + i * step, x + (i + 1) * step))
    # Header band near grid top
    band_top = y - 28
    band_bottom = y + 22
    headers: List[Dict[str, Any]] = []
    for t in texts or []:
        tx = t.get("x", 0); ty = t.get("y", 0); tw = t.get("width", 0); th = t.get("height", 0)
        if ty + th < band_top or ty > band_bottom:
            continue
        cx = tx + tw / 2
        for (c0, c1) in cols:
            if c0 <= cx <= c1:
                headers.append(t); break
    if headers:
        grid = dict(grid)
        grid["column_headers"] = headers
    return grid

def _find_star_rows(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect 5 near-identical small shapes (stars) in a row with even spacing."""
    # stars often ~ 18-36 square-ish
    stars = [
        r for r in rects
        if 18 <= r.get("width", 0) <= 140
        and 18 <= r.get("height", 0) <= 140
        and abs(r.get("width", 0) - r.get("height", 0)) <= max(8, 0.2 * max(r.get("width", 0), r.get("height", 0)))
    ]
    rows: List[Dict[str, Any]] = []
    if len(stars) < 5:
        return rows
    clusters = _group_by_y(stars, tol=18)
    for cl in clusters:
        if len(cl) < 5:
            continue
        rs = sorted(cl, key=lambda r: r.get("x", 0))
        centers = [r.get("x", 0) + r.get("width", 0) / 2 for r in rs]
        for i in range(0, len(rs) - 4):
            run = rs[i:i + 5]
            c = centers[i:i + 5]
            gaps = [c[j + 1] - c[j] for j in range(4)]
            mean_gap = sum(gaps) / len(gaps)
            var_gap = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            rel_std = math.sqrt(var_gap) / max(1e-6, mean_gap)
            if rel_std <= 0.35:
                rows.append({"type": "star_row", "stars": run})
                break
    return rows
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
        elif b.get("type") == "grid":
            for r in b.get("cells", []):
                rr = r.copy()
                rr["properties"] = {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}
                elements.append(rr)
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
        elif b.get("type") == "labeled_input":
            # add label text and input rectangle
            lbl_text = b.get("label_text", "")
            r = b.get("rect")
            if r:
                rr = r.copy()
                rr["properties"] = {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}
                elements.append(rr)
            if lbl_text:
                # create a text element near the rect (left or above)
                x = r.get("x", 0) if r else 0
                y = r.get("y", 0) if r else 0
                w = r.get("width", 0) if r else 0
                h = r.get("height", 0) if r else 0
                # try to place label to the left
                txt_elem = {"type": "text", "x": max(0, x - 80), "y": y + h / 2, "width": 70, "height": h, "properties": {"text": lbl_text, "fontFamily": "Helvetica", "fontSize": 14, "color": "#2C2C2C"}}
                elements.append(txt_elem)
        elif b.get("type") == "grid":
            # render grid bounds and optional column headers
            bounds = b.get("bounds", {})
            if bounds:
                grid_rect = {"type": "rectangle", "x": bounds.get("x", 0), "y": bounds.get("y", 0), "width": bounds.get("width", 0), "height": bounds.get("height", 0), "properties": {"fill": "transparent", "stroke": "#CCCCCC", "strokeWidth": 0.5}}
                elements.append(grid_rect)
            # column headers as text
            for hdr in b.get("column_headers", []):
                txt = hdr.copy()
                txt["properties"] = txt.get("properties", {})
                txt["properties"].setdefault("fontFamily", "Helvetica")
                txt["properties"].setdefault("fontSize", 14)
                txt["properties"].setdefault("color", "#2C2C2C")
                elements.append(txt)
        elif b.get("type") == "checkbox_list":
            for item in b.get("items", []):
                r = item.get("rect")
                t = item.get("label")
                if r:
                    rr = r.copy()
                    rr["properties"] = {"fill": "transparent", "stroke": "#000000", "strokeWidth": 1}
                    elements.append(rr)
                if t:
                    tt = t.copy()
                    tt["properties"] = tt.get("properties", {})
                    tt["properties"].setdefault("fontFamily", "Helvetica")
                    tt["properties"].setdefault("fontSize", 14)
                    tt["properties"].setdefault("color", "#2C2C2C")
                    elements.append(tt)
        elif b.get("type") == "labeled_line":
            # add label text and a thin line
            lab = b.get("label")
            ln = b.get("line")
            if lab:
                tt = lab.copy()
                tt["properties"] = tt.get("properties", {})
                tt["properties"].setdefault("fontFamily", "Helvetica")
                tt["properties"].setdefault("fontSize", 14)
                tt["properties"].setdefault("color", "#2C2C2C")
                elements.append(tt)
            if ln:
                ll = {"type": "line", "x": ln.get("x", 0), "y": ln.get("y", 0), "width": ln.get("width", 100), "height": 0, "properties": {"stroke": "#2C2C2C", "strokeWidth": 1}}
                elements.append(ll)
        elif b.get("type") == "star_row":
            for r in b.get("stars", []):
                rr = r.copy()
                rr["properties"] = {"fill": "transparent", "stroke": "#999999", "strokeWidth": 1}
                elements.append(rr)
    return elements


def extract_blocks(pattern_dir: Path, ai_detect: bool = False, ai_model: str = "doclayout", imgsz: int = 1280, tile_size: int = 640, tile_overlap: int = 100) -> Dict[str, Any]:
    analysis_dir = pattern_dir / "analysis"
    pages = _load_pages(analysis_dir)
    if not pages:
        return {"success": False, "error": "no analysis pages found"}

    all_blocks: List[Dict[str, Any]] = []
    pages_data: List[Dict[str, Any]] = []

    for page in pages:
        page_w = float(page.get("width", 0))
        page_h = float(page.get("height", 0))
        elems = page.get("elements", [])
        texts = [e for e in elems if e.get("type") == "text"]
        rects = [e for e in elems if e.get("type") == "rectangle"]
        lines = [e for e in elems if e.get("type") == "line"]
        # derive line primitives from thin rectangles
        thin_h, thin_v = _thin_rects_to_lines(rects)
        lines_for_grid = (lines or []) + thin_h + thin_v

        # CV line merging and contour detection if PNG available
        page_png_path = analysis_dir / f"page_{page.get('page_index', 0)+1}.png"
        merged_h, merged_v = [], []
        contour_checkboxes = []
        ai_detections_page = []
        if page_png_path.exists():
            # Estimate DPI scale from page size vs typical letter size (612x792)
            dpi_scale = max(page_w / 612.0, page_h / 792.0)
            merged_h, merged_v = _merge_lines_cv(page_png_path, dpi_scale)
            contour_checkboxes = _find_contour_checkboxes(page_png_path, dpi_scale)
            # AI detection if requested
            if ai_detect:
                try:
                    from web.backend.services.ai_vision import detect, save_detections
                    ai_detections_page = detect(page_png_path, conf_threshold=0.01, ai_model=ai_model, imgsz=imgsz, tile_size=tile_size, tile_overlap=tile_overlap)
                except Exception as e:
                    print(f"⚠️ AI vision failed for {page_png_path.name}: {e}")
                    ai_detections_page = []

        header = _find_header(texts, page_h) or _find_header_group(texts, page_w, page_h)
        if header:
            all_blocks.append({"type": "header", "text": header, "page": page.get("page_index", 0)})

        weekly = _find_weekly_rows(rects, texts)
        for w in weekly:
            w["page"] = page.get("page_index", 0)
            all_blocks.append(w)

        grids = _find_grids(rects)
        for g in grids:
            g["page"] = page.get("page_index", 0)
            all_blocks.append(g)

        # Grids from stroke lines (tables)
        grids2 = _find_grids_from_lines(lines_for_grid, page_w, page_h)
        for g2 in grids2:
            g2 = _attach_grid_headers(g2, texts)
            g2["page"] = page.get("page_index", 0)
            all_blocks.append(g2)

        # Record per-page data for later fusion
        pages_data.append({
            "page_index": int(page.get("page_index", 0)),
            "page_w": page_w,
            "page_h": page_h,
            "texts": texts,
            "merged_h": merged_h,
            "merged_v": merged_v,
            "ai": ai_detections_page,
        })

        # Grids from CV-merged lines (more robust)
        if merged_h or merged_v:
            grids3 = _find_grids_from_merged_lines(merged_h, merged_v, page_w, page_h)
            for g3 in grids3:
                g3 = _attach_grid_headers(g3, texts)
                g3["page"] = page.get("page_index", 0)
                all_blocks.append(g3)

        # Fallback: infer grid from many parallel horizontals when verticals are missing
        has_grid_page = any(b.get("type") == "grid" and int(b.get("page", 0)) == int(page.get("page_index", 0)) for b in all_blocks)
        if not has_grid_page:
            inferred_grids = _infer_grid_from_parallel_lines(lines_for_grid, page_w, page_h)
            for ig in inferred_grids:
                ig = _attach_grid_headers(ig, texts)
                ig["page"] = page.get("page_index", 0)
                all_blocks.append(ig)

        note_blocks = _find_notes(rects, texts)
        for nb in note_blocks:
            nb["page"] = page.get("page_index", 0)
            all_blocks.append(nb)

        # Checkbox lists (original rects)
        cb_lists = _find_checkbox_lists(rects, texts)
        for cb in cb_lists:
            cb["page"] = page.get("page_index", 0)
            all_blocks.append(cb)

        # Checkbox lists from CV contours (fallback if no original rects)
        if not cb_lists and contour_checkboxes:
            cb_contour_lists = _find_checkbox_lists_from_contours(contour_checkboxes, texts)
            for cb in cb_contour_lists:
                cb["page"] = page.get("page_index", 0)
                all_blocks.append(cb)

        # Labeled inputs (MONTH, YEAR, CLASS, etc.)
        li_blocks = _find_labeled_inputs(rects, texts)
        for li in li_blocks:
            li["page"] = page.get("page_index", 0)
            all_blocks.append(li)

        # Labeled lines
        ll_blocks = _find_labeled_lines(rects, lines, texts)
        for lb in ll_blocks:
            lb["page"] = page.get("page_index", 0)
            all_blocks.append(lb)

        # Star rows
        sr_blocks = _find_star_rows(rects, texts)
        for sb in sr_blocks:
            sb["page"] = page.get("page_index", 0)
            all_blocks.append(sb)

    # Expanded fusion with AI detections if enabled (per page)
    fused_blocks = all_blocks[:]
    ai_detections_all: List[Dict[str, Any]] = []
    if ai_detect:
        # Helper: dedupe overlapping boxes (IoU > 0.6)
        def dedupe_boxes(boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            keep: List[Dict[str, Any]] = []
            for b in boxes:
                if not any(_iou(b.get("bbox", {}), k.get("bbox", {})) > 0.6 for k in keep):
                    keep.append(b)
            return keep

        # Helper: convert AI detections to blocks/elements
        def ai_to_blocks(dets: List[Dict[str, Any]], page_idx: int, page_w: float, page_h: float, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            blocks: List[Dict[str, Any]] = []
            if not dets:
                return blocks
            # Group detections by class
            by_class: Dict[str, List[Dict[str, Any]]] = {}
            for d in dets:
                by_class.setdefault(d.get("class", "shape"), []).append(d)
            # Tables: use AI bbox as grid bounds, then intersect with CV lines
            for t in by_class.get("table", []):
                bbox = t.get("bbox", {})
                if bbox.get("width", 0) < 120 or bbox.get("height", 0) < 80:
                    continue
                grid = {
                    "type": "grid",
                    "bounds": bbox,
                    "rows": None,
                    "cols": None,
                    "source": "ai_table",
                    "page": page_idx,
                }
                # Attach column headers from nearby texts
                grid = _attach_grid_headers(grid, texts)
                blocks.append(grid)
            # Text regions: treat as headers if near top, otherwise generic text_region
            for tr in by_class.get("text_region", []):
                bbox = tr.get("bbox", {})
                if bbox.get("y", 0) < page_h * 0.25 and bbox.get("width", 0) > page_w * 0.3:
                    blocks.append({"type": "header", "text": {"type": "text", **bbox, "properties": {}}, "source": "ai_text_region", "page": page_idx})
                else:
                    blocks.append({"type": "text_region", "rect": {"type": "rectangle", **bbox, "properties": {}}, "source": "ai_text_region", "page": page_idx})
            # Checkboxes: add as checkbox_list if grouped; else as individual checkboxes
            cbs = by_class.get("checkbox", [])
            if len(cbs) >= 4:
                items = []
                for cb in sorted(cbs, key=lambda d: d.get("bbox", {}).get("y", 0)):
                    items.append({"rect": {"type": "rectangle", **cb.get("bbox", {}), "properties": {}}, "label": None})
                blocks.append({"type": "checkbox_list", "items": items, "source": "ai_checkbox", "page": page_idx})
            else:
                for cb in cbs:
                    blocks.append({"type": "checkbox", "rect": {"type": "rectangle", **cb.get("bbox", {}), "properties": {}}, "source": "ai_checkbox", "page": page_idx})
            # Labeled inputs from VLM
            for li in by_class.get("labeled_input", []):
                bbox = li.get("bbox", {})
                label_text = li.get("label", "")
                blocks.append({"type": "labeled_input", "rect": {"type": "rectangle", **bbox, "properties": {}}, "label_text": label_text, "source": "ollama_vl", "page": page_idx})
            # Generic shapes
            for sh in by_class.get("shape", []):
                bbox = sh.get("bbox", {})
                if bbox.get("width", 0) < 20 or bbox.get("height", 0) < 20:
                    continue
                blocks.append({"type": "shape", "rect": {"type": "rectangle", **bbox, "properties": {}}, "source": "ai_shape", "page": page_idx})
            return blocks

        # Per-page AI fusion
        for pdata in pages_data:
            page_idx = pdata["page_index"]
            page_w = pdata["page_w"]
            page_h = pdata["page_h"]
            texts = pdata["texts"]
            ai_page = pdata.get("ai", [])
            if ai_page:
                deduped = dedupe_boxes(ai_page)
                ai_blocks = ai_to_blocks(deduped, page_idx, page_w, page_h, texts)
                # Prefer vector/CV geometry; add AI as fallback/semantics
                # Example: if no grid on this page, add AI grid
                has_grid = any(b.get("type") == "grid" and int(b.get("page", 0)) == page_idx for b in fused_blocks)
                for b in ai_blocks:
                    if b.get("type") == "grid" and has_grid:
                        continue  # keep CV grid
                    fused_blocks.append(b)
                ai_detections_all.extend([{"page": page_idx, **d} for d in deduped])

    # Save AI detections if any
    if ai_detect and ai_detections_all:
        extracted_dir = pattern_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        try:
            from web.backend.services.ai_vision import save_detections
            save_detections(ai_detections_all, extracted_dir / "ai_detections.json")
        except Exception as e:
            print(f"⚠️ Failed to save AI detections: {e}")

    # Flatten to normalized elements list as a starting point
    elements = _flatten_blocks_to_elements(fused_blocks)

    # Write outputs
    out_dir = pattern_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocks.json").write_text(json.dumps({"blocks": fused_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "elements.json").write_text(json.dumps({"elements": elements}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generate overlay PNGs for validation using Pillow if available
    try:
        from PIL import Image, ImageDraw
        analysis_dir = pattern_dir / "analysis"
        # group blocks by page
        by_page: Dict[int, List[Dict[str, Any]]] = {}
        for b in all_blocks:
            by_page.setdefault(int(b.get("page", 0)), []).append(b)
        for i, page in enumerate(pages):
            img_path = analysis_dir / f"page_{i+1}.png"
            if not img_path.exists():
                continue
            im = Image.open(img_path).convert("RGB")
            draw = ImageDraw.Draw(im)
            for b in by_page.get(int(page.get("page_index", 0)), []):
                if b.get("type") == "weekly_row":
                    color = (46, 204, 113)  # green
                    for r in b.get("rects", []):
                        x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                elif b.get("type") == "grid":
                    color = (230, 126, 34)  # orange
                    bd = b.get("bounds", {})
                    if bd:
                        x, y, w, h = bd.get("x", 0), bd.get("y", 0), bd.get("width", 0), bd.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
                    for hl in b.get("lines_h", []):
                        xh, yh, wh = hl.get("x", 0), hl.get("y", 0), hl.get("width", 0)
                        draw.line([xh, yh, xh + wh, yh], fill=color, width=2)
                    for vl in b.get("lines_v", []):
                        xv, yv, hv = vl.get("x", 0), vl.get("y", 0), vl.get("height", 0)
                        draw.line([xv, yv, xv, yv + hv], fill=color, width=2)
                    if b.get("source") == "cv_merged":
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=5)
                elif b.get("type") == "header":
                    color = (52, 152, 219)  # blue
                    t = b.get("text")
                    if t:
                        x, y, w, h = t.get("x", 0), t.get("y", 0), t.get("width", 0), t.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                elif b.get("type") == "star_row":
                    color = (241, 196, 15)  # yellow
                    for r in b.get("stars", []):
                        x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
            # Draw AI detections in cyan
            for d in ai_dets:
                bbox = d.get("bbox", {})
                x, y, w, h = bbox.get("x", 0), bbox.get("y", 0), bbox.get("width", 0), bbox.get("height", 0)
                draw.rectangle([x, y, x + w, y + h], outline=(0, 255, 255), width=2)
                # Optional: label
                label = d.get("label", d.get("class", ""))
                draw.text((x + 2, y + 2), f"{label} {d.get('conf', 0)}", fill=(0, 255, 255))
            # Draw all text spans to validate detection
            try:
                text_elems = [e for e in page.get("elements", []) if e.get("type") == "text"]
                for t in text_elems:
                    x, y, w, h = t.get("x", 0), t.get("y", 0), t.get("width", 0), t.get("height", 0)
                    draw.rectangle([x, y, x + w, y + h], outline=(100, 100, 100), width=1)
            except Exception:
                pass
            # Draw legend
            try:
                legend_items = [
                    ("Header", (52, 152, 219)),
                    ("Weekly Row", (46, 204, 113)),
                    ("Grid", (230, 126, 34)),
                    ("Notes", (142, 68, 173)),
                    ("Checkbox List", (231, 76, 60)),
                    ("Labeled Line", (39, 174, 96)),
                    ("Star Row", (241, 196, 15)),
                    ("AI Detection", (0, 255, 255)),
                    ("Text Span", (100, 100, 100)),
                ]
                x0, y0 = 20, 20
                for idx, (name, col) in enumerate(legend_items):
                    y = y0 + idx * 18
                    draw.rectangle([x0, y, x0 + 14, y + 14], fill=None, outline=col, width=3)
                    draw.text((x0 + 20, y), name, fill=(0, 0, 0))
            except Exception:
                pass
            out_dir = pattern_dir / "extracted"
            out_dir.mkdir(parents=True, exist_ok=True)
            im.save(out_dir / f"preview_page_{i+1}.png")
    except Exception:
        # Pillow not installed or drawing failed; continue silently
        pass

    return {"success": True, "blocks": fused_blocks, "elements": elements, "ai_detections": ai_detections_all}
