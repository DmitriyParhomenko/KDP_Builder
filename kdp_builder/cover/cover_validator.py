from dataclasses import dataclass
from typing import List

from pypdf import PdfReader
from kdp_builder.cover.cover_renderer import compute_cover_dims


@dataclass
class CoverIssue:
    level: str  # "error" | "warning" | "info"
    message: str


@dataclass
class CoverReport:
    ok: bool
    width_pt: float
    height_pt: float
    expected_width_pt: float
    expected_height_pt: float
    expected_spine_pt: float
    issues: List[CoverIssue]


def validate_cover(pdf_path: str, trim_key: str, page_count: int, paper: str, bleed_pt: float) -> CoverReport:
    issues: List[CoverIssue] = []
    dims = compute_cover_dims(trim_key, page_count, paper, bleed_pt)

    reader = PdfReader(pdf_path)
    if len(reader.pages) != 1:
        issues.append(CoverIssue("error", f"Cover must be a single-page PDF. Found {len(reader.pages)} page(s)."))

    page = reader.pages[0]
    media = page.mediabox
    w = float(media.width)
    h = float(media.height)

    # Size match (within small tolerance)
    tol = 0.5
    if abs(w - dims.width_pt) > tol or abs(h - dims.height_pt) > tol:
        issues.append(CoverIssue(
            "error",
            f"Page size {w:.2f}x{h:.2f} pt does not match expected cover {dims.width_pt:.2f}x{dims.height_pt:.2f} pt."
        ))

    # Basic checks
    try:
        if getattr(reader, "is_encrypted", False):
            issues.append(CoverIssue("error", "PDF is encrypted. Covers must be unencrypted."))
    except Exception:
        issues.append(CoverIssue("warning", "Could not determine encryption status."))

    # Optional: barcode clear zone check could be added later

    ok = not any(i.level == "error" for i in issues)
    return CoverReport(
        ok=ok,
        width_pt=w,
        height_pt=h,
        expected_width_pt=dims.width_pt,
        expected_height_pt=dims.height_pt,
        expected_spine_pt=dims.spine_pt,
        issues=issues,
    )
