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
        if max_gap > 120:  # likely two columns
            split = xs[idx]
    cols = [[], []] if split is not None else [[]]
    for p in entries:
        if split is None:
            cols[0].append(p)
        else:
            (cols[0] if p["x"] <= split else cols[1]).append(p)
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


def _find_labeled_lines(rects: List[Dict[str, Any]], texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect label text with a long horizontal line represented as a thin rectangle."""
    if not rects:
        return []
    # candidate lines: thin rectangles (height <= 6) and width >= 120
    candidates = [r for r in rects if r.get("width", 0) >= 120 and 0 < r.get("height", 0) <= 6]
    results: List[Dict[str, Any]] = []
    for ln in candidates:
        lx = ln.get("x", 0)
        # use vertical center of the thin rectangle as baseline
        ly = ln.get("y", 0) + ln.get("height", 0) / 2.0
        lw = ln.get("width", 0)
        best = None
        best_dist = 1e9
        for t in texts:
            tx = t.get("x", 0)
            ty = t.get("y", 0)
            th = t.get("height", 0)
            # label to the left of the line start, roughly same baseline
            if tx < lx and abs((ty + th / 2) - ly) <= 16 and (lx - (tx + t.get("width", 0))) <= 40:
                dist = lx - (tx + t.get("width", 0))
                if dist < best_dist:
                    best = t
                    best_dist = dist
        # Emit even without label, so overlays still show lines
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

        grids = _find_grids(rects)
        for g in grids:
            g["page"] = page.get("page_index", 0)
            all_blocks.append(g)

        note_blocks = _find_notes(rects, texts)
        for nb in note_blocks:
            nb["page"] = page.get("page_index", 0)
            all_blocks.append(nb)

        # Checkbox lists
        cb_lists = _find_checkbox_lists(rects, texts)
        for cb in cb_lists:
            cb["page"] = page.get("page_index", 0)
            all_blocks.append(cb)

        # Labeled lines
        ll_blocks = _find_labeled_lines(rects, texts)
        for lb in ll_blocks:
            lb["page"] = page.get("page_index", 0)
            all_blocks.append(lb)

        # Star rows
        sr_blocks = _find_star_rows(rects, texts)
        for sb in sr_blocks:
            sb["page"] = page.get("page_index", 0)
            all_blocks.append(sb)

    # Flatten to normalized elements list as a starting point
    elements = _flatten_blocks_to_elements(all_blocks)

    # Write outputs
    out_dir = pattern_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocks.json").write_text(json.dumps({"blocks": all_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
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
                    x, y, w, h = bd.get("x", 0), bd.get("y", 0), bd.get("width", 0), bd.get("height", 0)
                    draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
                elif b.get("type") == "notes":
                    color = (142, 68, 173)  # purple
                    r = b.get("rect")
                    if r:
                        x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                elif b.get("type") == "header":
                    color = (52, 152, 219)  # blue
                    t = b.get("text")
                    if t:
                        x, y, w, h = t.get("x", 0), t.get("y", 0), t.get("width", 0), t.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                elif b.get("type") == "checkbox_list":
                    color = (231, 76, 60)  # red
                    for item in b.get("items", []):
                        r = item.get("rect")
                        if r:
                            x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
                            draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                elif b.get("type") == "labeled_line":
                    color = (39, 174, 96)  # green-dark
                    ln = b.get("line")
                    if ln:
                        x, y, w = ln.get("x", 0), ln.get("y", 0), ln.get("width", 0)
                        draw.line([x, y, x + w, y], fill=color, width=3)
                elif b.get("type") == "star_row":
                    color = (241, 196, 15)  # yellow
                    for r in b.get("stars", []):
                        x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("width", 0), r.get("height", 0)
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)

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
                ]
                x0, y0 = 20, 20
                for idx, (name, col) in enumerate(legend_items):
                    y = y0 + idx * 18
                    draw.rectangle([x0, y, x0 + 14, y + 14], fill=None, outline=col, width=3)
                    draw.text((x0 + 20, y), name, fill=(0, 0, 0))
            except Exception:
                pass
            im.save(out_dir / f"preview_page_{i+1}.png")
    except Exception:
        # Pillow not installed or drawing failed; continue silently
        pass

    return {"success": True, "blocks": all_blocks, "elements": elements}
