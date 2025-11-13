"""
Thumbnail Generator for Patterns

Renders small PNG previews from extracted blocks/elements.
"""

import io
from pathlib import Path
from typing import Dict, Any, List, Tuple
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

def _estimate_page_size(elements: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Estimate page width/height from element and block extents.
    Falls back to at least (432, 648) if nothing found.
    """
    max_x = 0.0
    max_y = 0.0
    def upd_rect(x, y, w, h):
        nonlocal max_x, max_y
        max_x = max(max_x, float(x) + float(w))
        max_y = max(max_y, float(y) + float(h))

    # Elements
    for el in elements or []:
        if not isinstance(el, dict):
            continue
        t = el.get("type")
        x = el.get("x", 0.0)
        y = el.get("y", 0.0)
        w = el.get("width", 0.0)
        h = el.get("height", 0.0)
        if t in ("rectangle", "text"):
            upd_rect(x, y, w, h)
        elif t == "line":
            upd_rect(x, y, w, h)

    # Blocks
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        bt = b.get("type")
        if bt == "labeled_line":
            ln = b.get("line", {})
            upd_rect(ln.get("x", 0.0), ln.get("y", 0.0), ln.get("width", 0.0), 0.0)
        elif bt == "grid":
            bd = b.get("bounds", {}) or {}
            upd_rect(bd.get("x", 0.0), bd.get("y", 0.0), bd.get("width", 0.0), bd.get("height", 0.0))
        elif bt == "weekly_row":
            for r in b.get("rects", []) or []:
                upd_rect(r.get("x", 0.0), r.get("y", 0.0), r.get("width", 0.0), r.get("height", 0.0))
        elif bt == "checkbox_list":
            for it in b.get("items", []) or []:
                r = it.get("rect") or {}
                upd_rect(r.get("x", 0.0), r.get("y", 0.0), r.get("width", 0.0), r.get("height", 0.0))
        elif bt == "star_row":
            for r in b.get("stars", []) or []:
                upd_rect(r.get("x", 0.0), r.get("y", 0.0), r.get("width", 0.0), r.get("height", 0.0))
        else:
            r = b.get("rect") or {}
            if r:
                upd_rect(r.get("x", 0.0), r.get("y", 0.0), r.get("width", 0.0), r.get("height", 0.0))

    return max(432.0, max_x), max(648.0, max_y)

def render_thumbnail(
    elements: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    page_width: float = 432.0,
    page_height: float = 648.0,
    size: Tuple[int, int] = (1800, 2700)
) -> bytes:
    """
    Render a full-size PNG preview from elements and blocks at 300 DPI (6x9 inch = 1800x2700 px).

    Args:
        elements: Raw elements list
        blocks: Extracted blocks list
        page_width: Original page width in points
        page_height: Original page height in points
        size: Thumbnail size in pixels (width, height) - default is 6x9 at 300 DPI

    Returns:
        PNG image bytes
    """
    if Image is None or ImageDraw is None:
        raise RuntimeError("PIL is required for thumbnail generation")

    # Detect if blocks use percentage coordinates (0-100) vs points
    # Claude returns percentages, local pipeline returns points
    uses_percentages = False
    if blocks:
        # Check first block with coordinates
        for b in blocks:
            if "x" in b and "width" in b:
                # If x + width > page_width, likely using percentages
                if b.get("x", 0) + b.get("width", 0) <= 100:
                    uses_percentages = True
                break
    
    # Convert percentage coordinates to points if needed
    if uses_percentages:
        print(f"🔄 Converting percentage coordinates to points (page: {page_width}x{page_height})")
        for block in blocks:
            if "x" in block:
                block["x"] = (block["x"] / 100.0) * page_width
            if "y" in block:
                block["y"] = (block["y"] / 100.0) * page_height
            if "width" in block:
                block["width"] = (block["width"] / 100.0) * page_width
            if "height" in block:
                block["height"] = (block["height"] / 100.0) * page_height

    # Scale to thumbnail size
    scale_x = size[0] / page_width
    scale_y = size[1] / page_height

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)

    # Draw blocks (colored by type)
    block_colors = {
        # Old block types
        "header": (52, 152, 219),      # blue
        "weekly_row": (46, 204, 113),   # green
        "grid": (230, 126, 34),         # orange
        "notes": (142, 68, 173),        # purple
        "checkbox_list": (231, 76, 60), # red
        "labeled_line": (39, 174, 96),  # dark green
        "star_row": (241, 196, 15),     # yellow
        # New VLM label types
        "habit_tracker": (46, 204, 113),   # green
        "calendar": (52, 152, 219),        # blue
        "title": (241, 196, 15),           # yellow
        "goal_tracker": (230, 126, 34),    # orange
        "water_tracker": (52, 152, 219),   # blue
        "mood_tracker": (142, 68, 173),    # purple
        "schedule": (39, 174, 96),         # dark green
        "gratitude": (231, 76, 60),        # red
        "table": (150, 150, 150),          # gray
        "decorative": (200, 200, 200),     # light gray
        "text_field": (100, 100, 100),     # dark gray
        "other": (180, 180, 180),          # gray
        "unknown": (150, 150, 150),        # gray
    }

    for block in blocks:
        btype = block.get("type")
        color = block_colors.get(btype, (150, 150, 150))
        if btype == "labeled_line":
            line = block.get("line", {})
            x1 = line.get("x", 0) * scale_x
            y1 = line.get("y", 0) * scale_y
            x2 = (line.get("x", 0) + line.get("width", 0)) * scale_x
            draw.line([(x1, y1), (x2, y1)], fill=color, width=2)
        elif btype == "grid":
            # Draw bounds
            bd = block.get("bounds") or {}
            if bd:
                x = bd.get("x", 0) * scale_x
                y = bd.get("y", 0) * scale_y
                w = bd.get("width", 0) * scale_x
                h = bd.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
            # Draw internal lines if present
            for hl in block.get("lines_h", []) or []:
                xh = hl.get("x", 0) * scale_x
                yh = hl.get("y", 0) * scale_y
                wh = hl.get("width", 0) * scale_x
                draw.line([(xh, yh), (xh + wh, yh)], fill=color, width=1)
            for vl in block.get("lines_v", []) or []:
                xv = vl.get("x", 0) * scale_x
                yv = vl.get("y", 0) * scale_y
                hv = vl.get("height", 0) * scale_y
                draw.line([(xv, yv), (xv, yv + hv)], fill=color, width=1)
        elif btype == "weekly_row":
            for r in block.get("rects", []) or []:
                x = r.get("x", 0) * scale_x
                y = r.get("y", 0) * scale_y
                w = r.get("width", 0) * scale_x
                h = r.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=1)
        elif btype == "checkbox_list":
            for item in block.get("items", []) or []:
                r = item.get("rect") or {}
                if r:
                    x = r.get("x", 0) * scale_x
                    y = r.get("y", 0) * scale_y
                    w = r.get("width", 0) * scale_x
                    h = r.get("height", 0) * scale_y
                    draw.rectangle([x, y, x + w, y + h], outline=color, width=1)
        elif btype == "star_row":
            for r in block.get("stars", []) or []:
                x = r.get("x", 0) * scale_x
                y = r.get("y", 0) * scale_y
                w = r.get("width", 0) * scale_x
                h = r.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=1)
        elif btype == "header":
            t = block.get("text") or {}
            if t:
                x = t.get("x", 0) * scale_x
                y = t.get("y", 0) * scale_y
                w = t.get("width", 0) * scale_x
                h = t.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=1)
        else:
            # Try direct x,y,width,height (VLM-labeled blocks)
            if "x" in block and "y" in block:
                x = block.get("x", 0) * scale_x
                y = block.get("y", 0) * scale_y
                w = block.get("width", 0) * scale_x
                h = block.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=1)
            # Fallback to rect property
            else:
                rect = block.get("rect", {})
                if rect:
                    x = rect.get("x", 0) * scale_x
                    y = rect.get("y", 0) * scale_y
                    w = rect.get("width", 0) * scale_x
                    h = rect.get("height", 0) * scale_y
                    draw.rectangle([x, y, x + w, y + h], outline=color, width=1)

    # Draw raw elements (light gray)
    for el in elements:
        el_type = el.get("type")
        if el_type == "rectangle":
            x = el.get("x", 0) * scale_x
            y = el.get("y", 0) * scale_y
            w = el.get("width", 0) * scale_x
            h = el.get("height", 0) * scale_y
            draw.rectangle([x, y, x + w, y + h], outline=(200, 200, 200), width=1)
        elif el_type == "line":
            x1 = el.get("x", 0) * scale_x
            y1 = el.get("y", 0) * scale_y
            x2 = (el.get("x", 0) + el.get("width", 0)) * scale_x
            y2 = (el.get("y", 0) + el.get("height", 0)) * scale_y
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
        elif el_type == "text":
            x = el.get("x", 0) * scale_x
            y = el.get("y", 0) * scale_y
            w = el.get("width", 0) * scale_x
            h = el.get("height", 0) * scale_y
            draw.rectangle([x, y, x + w, y + h], outline=(180, 180, 180), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def generate_thumbnail_for_pattern(pattern_id: str) -> bool:
    """
    Generate and save thumbnail for a stored pattern.

    Args:
        pattern_id: Pattern ID

    Returns:
        True if successful, False otherwise
    """
    print(f"🔍 generate_thumbnail_for_pattern: start for {pattern_id}")
    from web.backend.services.pattern_db import pattern_db

    pattern = pattern_db.get_pattern_with_extracted(pattern_id)
    if not pattern:
        print(f"❌ No pattern found for {pattern_id}")
        return False

    elements = pattern.get("elements", [])
    blocks = pattern.get("blocks", [])
    print(f"🔍 Found {len(elements)} elements, {len(blocks)} blocks")
    if not elements and not blocks:
        print(f"❌ No elements or blocks for {pattern_id}")
        return False

    try:
        # Try to read page dimensions from pattern metadata (VLM blocks use pixel coords)
        pattern_dir = Path("./data/patterns") / pattern_id
        page_w, page_h = 432.0, 648.0
        
        # First try to get from pattern metadata (for VLM-extracted patterns)
        try:
            from web.backend.services.pattern_db import pattern_db
            pat = pattern_db.get_pattern(pattern_id)
            if pat and pat.get("metadata"):
                meta = pat["metadata"]
                if "page_width_px" in meta:
                    page_w = float(meta["page_width_px"])
                    page_h = float(meta["page_height_px"])
                    print(f"📄 Page size from metadata (px): {page_w}x{page_h}")
        except Exception as e:
            print(f"⚠️ Could not read metadata: {e}")
        
        # Fallback: try analysis JSON
        if page_w == 432.0 and page_h == 648.0:
            try:
                page1 = pattern_dir / "analysis" / "page_1.json"
                if page1.exists():
                    meta = __import__("json").loads(page1.read_text())
                    page_w = float(meta.get("width", page_w))
                    page_h = float(meta.get("height", page_h))
                    print(f"📄 Page size from JSON: {page_w}x{page_h}")
            except Exception as e:
                print(f"⚠️ Could not read page_1.json: {e}")
        
        # Final fallback: estimate from extracted elements/blocks
        if page_w == 432.0 and page_h == 648.0:
            est_w, est_h = _estimate_page_size(elements, blocks)
            page_w, page_h = est_w, est_h
            print(f"📐 Estimated page size: {page_w}x{page_h}")

        print(f"🎨 Rendering thumbnail...")
        png_bytes = render_thumbnail(elements, blocks, page_width=page_w, page_height=page_h)
        pattern_dir = Path("./data/patterns") / pattern_id
        pattern_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = pattern_dir / "thumbnail.png"
        thumb_path.write_bytes(png_bytes)
        print(f"✅ Thumbnail saved to {thumb_path} ({len(png_bytes)} bytes)")
        return True
    except Exception as e:
        import traceback
        print(f"⚠️ Failed to generate thumbnail for {pattern_id}: {e}")
        traceback.print_exc()
        return False

def generate_all_thumbnails() -> int:
    """
    Generate thumbnails for all patterns that have extracted data.

    Returns:
        Number of thumbnails generated
    """
    from web.backend.services.pattern_db import pattern_db

    patterns = pattern_db.list_patterns_with_extracted()
    count = 0
    for p in patterns:
        if generate_thumbnail_for_pattern(p["id"]):
            count += 1
    return count
