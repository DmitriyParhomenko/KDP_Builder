from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.lib.units import inch

from kdp_builder.config.sizes import SIZES
from kdp_builder.renderer.templates import (
    draw_lined_page,
    draw_grid_page,
    draw_dot_grid_page,
    draw_habit_tracker_page,
)


def generate_lined_pages(
    trim_key: str,
    pages: int,
    out_path: str,
    line_spacing: float = 18.0,
    line_weight: float = 0.5,
    gutter_pt: float = 0.0,
    debug_safe_area: bool = False,
    template: str = "lined",  # lined | grid | dot | habit
    grid_size_pt: float = 18.0,
    dot_step_pt: float = 18.0,
    dot_radius_pt: float = 0.5,
    habit_rows: int = 20,
    habit_cols: int = 7,
):
    if trim_key not in SIZES:
        raise ValueError(f"Unknown trim key '{trim_key}'. Available: {list(SIZES.keys())}")

    conf = SIZES[trim_key]
    width = conf["width"]
    height = conf["height"]
    m = conf["margin"]

    c = canvas.Canvas(out_path, pagesize=(width, height))

    for page_index in range(pages):
        # Parity-aware inner/outer margins with optional gutter added to inner side
        is_odd = ((page_index + 1) % 2) == 1  # page 1 is odd (recto/right)
        inner = m["inner"] + gutter_pt
        outer = m["outer"]
        top = height - m["top"]
        bottom = m["bottom"]

        if is_odd:
            # Odd pages: binding on the left (inner margin at left)
            left = inner
            right = width - outer
        else:
            # Even pages: binding on the right (inner margin at right)
            left = outer
            right = width - inner

        # Draw by template
        if template == "lined":
            draw_lined_page(c, left, right, top, bottom, line_spacing, line_weight)
        elif template == "grid":
            draw_grid_page(c, left, right, top, bottom, grid_size_pt, line_weight)
        elif template == "dot":
            draw_dot_grid_page(c, left, right, top, bottom, dot_step_pt, dot_radius_pt)
        elif template == "habit":
            draw_habit_tracker_page(c, left, right, top, bottom, rows=habit_rows, cols=habit_cols, line_weight=line_weight)
        else:
            raise ValueError(f"Unknown template '{template}'. Use one of: lined, grid, dot, habit")

        # Optional: draw a thin border to visualize safe area
        if debug_safe_area:
            c.saveState()
            c.setLineWidth(0.25)
            c.setDash(2, 3)
            c.rect(left, bottom, right - left, top - bottom)
            c.restoreState()

        c.showPage()

    c.save()
