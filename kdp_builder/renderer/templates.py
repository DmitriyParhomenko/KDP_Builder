from reportlab.lib.colors import black, Color
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch


def draw_lined_page(c: Canvas, left: float, right: float, top: float, bottom: float, line_spacing: float, line_weight: float):
    c.setStrokeColor(black)
    c.setLineWidth(line_weight)
    y = top - 0.25 * inch
    while y > bottom + 0.25 * inch:
        c.line(left, y, right, y)
        y -= line_spacing


def draw_grid_page(c: Canvas, left: float, right: float, top: float, bottom: float, grid_size: float, line_weight: float):
    c.setStrokeColor(black)
    c.setLineWidth(line_weight)
    x = left
    while x <= right:
        c.line(x, bottom, x, top)
        x += grid_size
    y = bottom
    while y <= top:
        c.line(left, y, right, y)
        y += grid_size


def draw_dot_grid_page(c: Canvas, left: float, right: float, top: float, bottom: float, step: float, dot_radius: float = 0.5):
    c.setFillColor(black)
    y = bottom
    while y <= top:
        x = left
        while x <= right:
            c.circle(x, y, dot_radius, stroke=0, fill=1)
            x += step
        y += step


def draw_habit_tracker_page(c: Canvas, left: float, right: float, top: float, bottom: float, rows: int = 20, cols: int = 7, line_weight: float = 0.5):
    c.setStrokeColor(black)
    c.setLineWidth(line_weight)
    w = right - left
    h = top - bottom
    row_h = h / rows
    col_w = w / cols
    y = bottom
    for _ in range(rows + 1):
        c.line(left, y, right, y)
        y += row_h
    x = left
    for _ in range(cols + 1):
        c.line(x, bottom, x, top)
        x += col_w
