# KDP common trim sizes (in points). 72 points = 1 inch
# This MVP uses conservative safe margins; refine per KDP spec later.

INCH = 72.0

SIZES = {
    # Standard 6" x 9" trim
    "6x9": {
        "width": 6.0 * INCH,
        "height": 9.0 * INCH,
        # Safe margins (all sides). For thick books add a gutter later.
        "margin": {
            "top": 0.5 * INCH,
            "bottom": 0.5 * INCH,
            "inner": 0.5 * INCH,  # binding side
            "outer": 0.5 * INCH,
        },
        # Bleed flag; actual interior usually no-bleed unless graphics to edge
        "bleed": False,
    },
    # Add more keys like "8.5x11" or "5x8" later
}
