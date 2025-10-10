from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.lib.units import inch

from kdp_builder.config.sizes import SIZES


def generate_lined_pages(
    trim_key: str,
    pages: int,
    out_path: str,
    line_spacing: float = 18.0,
    line_weight: float = 0.5,
):
    if trim_key not in SIZES:
        raise ValueError(f"Unknown trim key '{trim_key}'. Available: {list(SIZES.keys())}")

    conf = SIZES[trim_key]
    width = conf["width"]
    height = conf["height"]
    m = conf["margin"]

    c = canvas.Canvas(out_path, pagesize=(width, height))

    for _ in range(pages):
        # Draw lines within safe area
        left = m["inner"]
        right = width - m["outer"]
        top = height - m["top"]
        bottom = m["bottom"]

        c.setStrokeColor(black)
        c.setLineWidth(line_weight)

        # Compute y positions from top downward by line_spacing
        y = top
        # leave small header gap
        y -= 0.25 * inch
        while y > bottom + 0.25 * inch:
            c.line(left, y, right, y)
            y -= line_spacing

        # Optional: draw a thin border to visualize safe area (disabled by default)
        # c.setLineWidth(0.25)
        # c.setDash(2, 3)
        # c.rect(left, bottom, right - left, top - bottom)

        c.showPage()

    c.save()
