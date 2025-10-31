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

def render_thumbnail(
    elements: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    page_width: float = 432.0,
    page_height: float = 648.0,
    size: Tuple[int, int] = (216, 324)
) -> bytes:
    """
    Render a small PNG thumbnail from elements and blocks.

    Args:
        elements: Raw elements list
        blocks: Extracted blocks list
        page_width: Original page width in points
        page_height: Original page height in points
        size: Thumbnail size in pixels (width, height)

    Returns:
        PNG image bytes
    """
    if Image is None or ImageDraw is None:
        raise RuntimeError("PIL is required for thumbnail generation")

    # Scale to thumbnail size
    scale_x = size[0] / page_width
    scale_y = size[1] / page_height

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)

    # Draw blocks (colored by type)
    block_colors = {
        "header": (52, 152, 219),      # blue
        "weekly_row": (46, 204, 113),   # green
        "grid": (230, 126, 34),         # orange
        "notes": (142, 68, 173),        # purple
        "checkbox_list": (231, 76, 60), # red
        "labeled_line": (39, 174, 96),  # dark green
        "star_row": (241, 196, 15),     # yellow
    }

    for block in blocks:
        color = block_colors.get(block.get("type"), (150, 150, 150))
        if block.get("type") == "labeled_line":
            line = block.get("line", {})
            x1 = line.get("x", 0) * scale_x
            y1 = line.get("y", 0) * scale_y
            x2 = (line.get("x", 0) + line.get("width", 0)) * scale_x
            draw.line([(x1, y1), (x2, y1)], fill=color, width=2)
        else:
            rect = block.get("rect", {})
            if rect:
                x = rect.get("x", 0) * scale_x
                y = rect.get("y", 0) * scale_y
                w = rect.get("width", 0) * scale_x
                h = rect.get("height", 0) * scale_y
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)

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
    from web.backend.services.pattern_db import pattern_db

    pattern = pattern_db.get_pattern_with_extracted(pattern_id)
    if not pattern:
        return False

    elements = pattern.get("elements", [])
    blocks = pattern.get("blocks", [])
    if not elements and not blocks:
        return False

    try:
        png_bytes = render_thumbnail(elements, blocks)
        pattern_dir = Path("./data/patterns") / pattern_id
        pattern_dir.mkdir(parents=True, exist_ok=True)
        (pattern_dir / "thumbnail.png").write_bytes(png_bytes)
        return True
    except Exception as e:
        print(f"⚠️  Failed to generate thumbnail for {pattern_id}: {e}")
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
