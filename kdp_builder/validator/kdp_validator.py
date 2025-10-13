from dataclasses import dataclass
from typing import List, Tuple

from pypdf import PdfReader
from kdp_builder.config.sizes import SIZES


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning" | "info"
    message: str


@dataclass
class ValidationReport:
    ok: bool
    trim_key: str
    page_count: int
    page_size_pt: Tuple[float, float]
    issues: List[ValidationIssue]


def _almost_equal(a: float, b: float, tol: float = 0.5) -> bool:
    return abs(a - b) <= tol


def validate_pdf(pdf_path: str, trim_key: str) -> ValidationReport:
    if trim_key not in SIZES:
        raise ValueError(f"Unknown trim key '{trim_key}'. Available: {list(SIZES.keys())}")

    target = SIZES[trim_key]
    target_w = float(target["width"])
    target_h = float(target["height"])

    issues: List[ValidationIssue] = []

    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    # KDP typical page count constraints for interiors (varies by paper/ink). Use broad safe range.
    if num_pages < 24:
        issues.append(ValidationIssue("error", f"Page count {num_pages} is below KDP minimum (24)."))
    if num_pages > 828:
        issues.append(ValidationIssue("error", f"Page count {num_pages} exceeds KDP maximum (828)."))

    # Check page sizes
    for i, page in enumerate(reader.pages, start=1):
        media_box = page.mediabox
        w = float(media_box.width)
        h = float(media_box.height)
        # Accept rotation-independent match
        size_match = (_almost_equal(w, target_w) and _almost_equal(h, target_h)) or (
            _almost_equal(w, target_h) and _almost_equal(h, target_w)
        )
        if not size_match:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Page {i} size {w:.2f}x{h:.2f} pt does not match trim {trim_key} ({target_w:.2f}x{target_h:.2f} pt).",
                )
            )

    ok = not any(iss.level == "error" for iss in issues)
    # Report uses first page size for summary
    first_w = float(reader.pages[0].mediabox.width)
    first_h = float(reader.pages[0].mediabox.height)

    return ValidationReport(
        ok=ok,
        trim_key=trim_key,
        page_count=num_pages,
        page_size_pt=(first_w, first_h),
        issues=issues,
    )
