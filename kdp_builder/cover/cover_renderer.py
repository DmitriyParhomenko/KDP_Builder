from dataclasses import dataclass
from typing import Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.lib.units import inch

from kdp_builder.config.sizes import SIZES

# Approximate KDP spine width (inches) per page by paper type
# Sources: common community references; verify before publishing
SPINE_IN_PER_PAGE = {
    "white": 0.002252,
    "cream": 0.0025,
    "color": 0.002347,
}


@dataclass
class CoverDims:
    width_pt: float
    height_pt: float
    spine_pt: float


def compute_cover_dims(trim_key: str, page_count: int, paper: str, bleed_pt: float) -> CoverDims:
    if trim_key not in SIZES:
        raise ValueError(f"Unknown trim key '{trim_key}'. Available: {list(SIZES.keys())}")
    if paper not in SPINE_IN_PER_PAGE:
        raise ValueError(f"Unknown paper '{paper}'. Use one of {list(SPINE_IN_PER_PAGE.keys())}")

    conf = SIZES[trim_key]
    trim_w = float(conf["width"])  # points
    trim_h = float(conf["height"])  # points

    spine_in = page_count * SPINE_IN_PER_PAGE[paper]
    spine_pt = spine_in * inch

    # Full cover including bleed on all outer edges: +bleed top/bottom and on left/right outer edges
    width_pt = (2 * trim_w) + spine_pt + 2 * bleed_pt
    height_pt = trim_h + 2 * bleed_pt

    return CoverDims(width_pt=width_pt, height_pt=height_pt, spine_pt=spine_pt)


def generate_cover(
    trim_key: str,
    page_count: int,
    paper: str,
    bleed_pt: float,
    out_path: str,
    title: str = "",
    subtitle: str = "",
    author: str = "",
    bg_gray: float = 0.9,
):
    dims = compute_cover_dims(trim_key, page_count, paper, bleed_pt)

    c = canvas.Canvas(out_path, pagesize=(dims.width_pt, dims.height_pt))

    # Background
    c.setFillGray(bg_gray)
    c.rect(0, 0, dims.width_pt, dims.height_pt, fill=1, stroke=0)

    # Guides (back | spine | front)
    trim_w = SIZES[trim_key]["width"]
    left_x = bleed_pt
    back_right = left_x + trim_w
    spine_right = back_right + dims.spine_pt
    front_left = spine_right

    # Draw separator lines for reference (non-printing in real covers)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(back_right, 0, back_right, dims.height_pt)
    c.line(spine_right, 0, spine_right, dims.height_pt)

    # Front cover title block
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 28)
    cx = (front_left + (front_left + trim_w)) / 2.0
    cy = dims.height_pt * 0.6
    if title:
        c.drawCentredString(cx, cy, title)
    if subtitle:
        c.setFont("Helvetica", 16)
        c.drawCentredString(cx, cy - 28, subtitle)
    if author:
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(cx, bleed_pt + 0.3 * inch, author)

    # Spine text (simple vertical)
    if title:
        c.saveState()
        c.setFont("Helvetica", 10)
        c.translate(back_right + dims.spine_pt / 2.0, dims.height_pt / 2.0)
        c.rotate(90)
        c.drawCentredString(0, 0, title[:40])
        c.restoreState()

    c.showPage()
    c.save()
