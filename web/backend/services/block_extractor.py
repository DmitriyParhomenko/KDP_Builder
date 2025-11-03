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
        lines = cv2.HoughLinesP(closed_img, rho=1, theta=np.pi/180 if orientation == 'h' else np.pi/2, threshold=30, minLineLength=int(40 * dpi_scale), maxLineGap=int(12 * dpi_scale))
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


def extract_blocks(pattern_dir: Path, ai_detect: bool = False) -> Dict[str, Any]:
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
                    ai_detections_page = detect(page_png_path, conf_threshold=0.01)
                except Exception as e:
                    print(f"⚠️ AI vision failed for {page_png_path.name}: {e}")
                    ai_detections_page = []

        header = _find_header(texts, page_h)
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
        grids2 = _find_grids_from_lines(lines, page_w, page_h)
        for g2 in grids2:
            g2["page"] = page.get("page_index", 0)
            all_blocks.append(g2)

        # Grids from CV-merged lines (more robust)
        if merged_h or merged_v:
            grids3 = _find_grids_from_merged_lines(merged_h, merged_v, page_w, page_h)
            for g3 in grids3:
                g3["page"] = page.get("page_index", 0)
                all_blocks.append(g3)

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

    # Expanded fusion with AI detections if enabled
    fused_blocks = all_blocks[:]
    ai_detections_all: List[Dict[str, Any]] = []
    if ai_detect:
        # For now, just collect AI detections; fusion can be expanded later
        ai_detections_all = ai_detections_page  # TODO: aggregate per page if multi-page

        # Helper: dedupe overlapping boxes (IoU > 0.6)
        def dedupe_boxes(boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            keep = []
            for b in boxes:
                if not any(_iou(b["bbox"], k["bbox"]) > 0.6 for k in keep):
                    keep.append(b)
            return keep

        ai_tables = [d for d in ai_detections_all if d.get("class") == "table"]
        ai_checkboxes = [d for d in ai_detections_all if d.get("class") == "checkbox"]
        ai_text_regions = [d for d in ai_detections_all if d.get("class") == "text_region"]
        ai_shapes = [d for d in ai_detections_all if d.get("class") == "shape"]

        # 1) Fuse AI tables with CV merged lines to improve grid recall
        if ai_tables or (merged_h and merged_v):
            # Start with CV merged-lines grids
            cv_grids = _find_grids_from_merged_lines(merged_h, merged_v, page_w, page_h)
            # Add AI table bounds as grids if they don't overlap too much
            for d in dedupe_boxes(ai_tables):
                bbox = d.get("bbox", {})
                # Ensure bbox is not too small/large
                if bbox.get("width", 0) < 30 or bbox.get("height", 0) < 30:
                    continue
                # Avoid high overlap with existing CV grids
                if any(_iou(bbox, g.get("bounds", {})) > 0.5 for g in cv_grids):
                    continue
                fused_grid = {
                    "type": "grid",
                    "bounds": bbox,
                    "source": "ai_table",
                    "lines_h": [],  # Could be enriched by intersecting CV lines
                    "lines_v": [],
                }
                fused_blocks.append(fused_grid)
            # Add CV grids
            for g in cv_grids:
                g["source"] = "cv_merged"
                fused_blocks.append(g)

        # 2) If no checkbox_list found, create from AI checkboxes (pair with nearest text)
        has_checkbox_list = any(b.get("type") == "checkbox_list" for b in fused_blocks)
        if not has_checkbox_list and ai_checkboxes:
            cb_items = []
            for d in dedupe_boxes(ai_checkboxes):
                bbox = d.get("bbox", {})
                bx, by, bw, bh = bbox.get("x", 0), bbox.get("y", 0), bbox.get("width", 0), bbox.get("height", 0)
                best = None
                best_dx = 1e9
                for t in texts:
                    tx = t.get("x", 0)
                    ty = t.get("y", 0)
                    th = t.get("height", 0)
                    if abs((ty + th / 2) - (by + bh / 2)) <= max(20, bh):
                        dx = tx - (bx + bw)
                        if 4 <= dx <= 500 and dx < best_dx:
                            best = t
                            best_dx = dx
                cb_items.append({"rect": {"type": "rectangle", "x": bx, "y": by, "width": bw, "height": bh, "properties": {}}, "label": best})
            if len(cb_items) >= 4:
                fused_blocks.append({"type": "checkbox_list", "items": cb_items, "source": "ai_fused"})

        # 3) If no header found, use large AI text_region near top as header
        has_header = any(b.get("type") == "header" for b in fused_blocks)
        if not has_header and ai_text_regions:
            for d in dedupe_boxes(ai_text_regions):
                bbox = d.get("bbox", {})
                if bbox.get("y", 0) > page_h * 0.4:
                    continue  # not near top
                if bbox.get("width", 0) < page_w * 0.2:
                    continue  # too narrow
                # Prefer widest
                fused_blocks.append({"type": "header", "text": {"type": "text", **bbox, "properties": {}}, "source": "ai_text_region"})
                break  # only one

        # 4) Keep notable shapes as generic elements (optional)
        for d in dedupe_boxes(ai_shapes):
            bbox = d.get("bbox", {})
            # Only keep reasonably large boxes
            if bbox.get("width", 0) < 20 or bbox.get("height", 0) < 20:
                continue
            fused_blocks.append({"type": "shape", "rect": {"type": "rectangle", **bbox, "properties": {}}, "source": "ai_shape"})

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
