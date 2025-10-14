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


def _rect_inside(inner, outer, tol: float = 0.1) -> bool:
    try:
        return (
            (inner.left   >= outer.left   - tol)
            and (inner.bottom >= outer.bottom - tol)
            and (inner.right  <= outer.right  + tol)
            and (inner.top    <= outer.top    + tol)
        )
    except Exception:
        return True


def validate_pdf(pdf_path: str, trim_key: str) -> ValidationReport:
    if trim_key not in SIZES:
        raise ValueError(f"Unknown trim key '{trim_key}'. Available: {list(SIZES.keys())}")

    target = SIZES[trim_key]
    target_w = float(target["width"])
    target_h = float(target["height"])

    issues: List[ValidationIssue] = []

    reader = PdfReader(pdf_path)

    # Encryption check
    try:
        if getattr(reader, "is_encrypted", False):
            issues.append(ValidationIssue("error", "PDF is encrypted. KDP requires unencrypted, printable PDFs."))
    except Exception:
        issues.append(ValidationIssue("warning", "Could not determine encryption status."))

    # PDF version check (recommend <= 1.7)
    try:
        pdf_header = getattr(reader, "pdf_header", None)
        version = getattr(pdf_header, "version", None)
        if version is not None:
            # version may be a tuple (1, 7) or float-like; normalize to string
            ver_str = f"{version}"
            issues.append(ValidationIssue("info", f"PDF header version: {ver_str}"))
            try:
                # crude parse: accept values up to 1.7
                if isinstance(version, (tuple, list)):
                    major, minor = int(version[0]), int(version[1])
                else:
                    parts = str(version).split(".")
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                if (major, minor) > (1, 7):
                    issues.append(ValidationIssue("warning", "PDF version is > 1.7. Consider exporting as 1.7 or earlier for print compatibility."))
            except Exception:
                pass
    except Exception:
        issues.append(ValidationIssue("warning", "Could not read PDF version header."))

    num_pages = len(reader.pages)

    # KDP typical page count constraints for interiors (varies by paper/ink). Use broad safe range.
    if num_pages < 24:
        issues.append(ValidationIssue("error", f"Page count {num_pages} is below KDP minimum (24)."))
    if num_pages > 828:
        issues.append(ValidationIssue("error", f"Page count {num_pages} exceeds KDP maximum (828)."))

    # Check page sizes, uniformity, rotation, annotations, and basic image presence
    first_w = None
    first_h = None
    landscape_pages = 0
    pages_with_rotation = 0
    pages_with_annots = 0
    image_object_count = 0
    low_res_image_guess = 0
    fonts_seen = set()
    fonts_not_embedded = set()
    fonts_subset = set()
    fonts_type3 = set()

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

        # Record first page size and ensure uniform MediaBox across pages
        if first_w is None:
            first_w, first_h = w, h
        else:
            if not (_almost_equal(w, first_w) and _almost_equal(h, first_h)):
                issues.append(ValidationIssue("error", f"Page {i} size differs from first page ({first_w:.2f}x{first_h:.2f} pt)."))

        # Orientation (warn if landscape)
        if w > h:
            landscape_pages += 1

        # Rotation check (warn if rotated)
        try:
            rot = getattr(page, "rotation", 0) or page.get("/Rotate", 0)
            if rot not in (0, None):
                pages_with_rotation += 1
        except Exception:
            pass

        # Font embedding checks
        try:
            resources = resources if 'resources' in locals() else (page.get("/Resources") or {})
            font_dict = resources.get("/Font") if hasattr(resources, "get") else None
            if font_dict and hasattr(font_dict, "items"):
                for font_name, font_obj in font_dict.items():
                    try:
                        base_name = str(font_obj.get("/BaseFont")) if hasattr(font_obj, "get") else str(font_name)
                        fonts_seen.add(base_name)

                        subtype = str(font_obj.get("/Subtype")) if hasattr(font_obj, "get") else ""
                        if subtype == "/Type3":
                            fonts_type3.add(base_name)

                        fd = font_obj.get("/FontDescriptor") if hasattr(font_obj, "get") else None
                        embedded = False
                        if fd and hasattr(fd, "get"):
                            if fd.get("/FontFile") or fd.get("/FontFile2") or fd.get("/FontFile3"):
                                embedded = True
                        if not embedded:
                            fonts_not_embedded.add(base_name)

                        # Subset names typically start with ABCDEF+ prefix
                        if "+" in base_name:
                            prefix, _ = base_name.split("+", 1)
                            if prefix.isupper() and len(prefix) >= 6:
                                fonts_subset.add(base_name)
                    except Exception:
                        continue
        except Exception:
            pass

        # Annotations check
        try:
            annots = page.get("/Annots")
            if annots:
                pages_with_annots += 1
        except Exception:
            pass

        # TrimBox/BleedBox sanity (if present)
        try:
            trim = getattr(page, "trimbox", None)
            bleed = getattr(page, "bleedbox", None)
            if trim is not None:
                if not _rect_inside(trim, media_box):
                    issues.append(ValidationIssue("warning", f"Page {i} TrimBox lies outside MediaBox; check export settings."))
            if bleed is not None:
                # Bleed should encompass trim and be inside media
                if trim is not None and not _rect_inside(trim, bleed):
                    issues.append(ValidationIssue("warning", f"Page {i} TrimBox is not inside BleedBox; check bleed settings."))
                if not _rect_inside(bleed, media_box):
                    issues.append(ValidationIssue("warning", f"Page {i} BleedBox lies outside MediaBox; check export settings."))
        except Exception:
            pass

        # Basic image XObject presence count (no DPI calc in this pass)
        try:
            resources = page.get("/Resources") or {}
            xobj = resources.get("/XObject") if hasattr(resources, "get") else None
            if xobj and hasattr(xobj, "items"):
                for _, obj in xobj.items():
                    try:
                        subtype = obj.get("/Subtype") if hasattr(obj, "get") else None
                        if str(subtype) == "/Image":
                            image_object_count += 1
                            # Heuristic: if intrinsic pixel dims are small (<900), flag potential low DPI when used large
                            w_px = obj.get("/Width") if hasattr(obj, "get") else None
                            h_px = obj.get("/Height") if hasattr(obj, "get") else None
                            try:
                                if w_px is not None and h_px is not None:
                                    if int(w_px) < 900 or int(h_px) < 900:
                                        low_res_image_guess += 1
                            except Exception:
                                pass
                    except Exception:
                        continue
        except Exception:
            pass

    ok = not any(iss.level == "error" for iss in issues)
    # Orientation/annotation summary warnings
    if landscape_pages > 0:
        issues.append(ValidationIssue("warning", f"{landscape_pages} page(s) are landscape. Interiors are typically portrait."))
    if pages_with_rotation > 0:
        issues.append(ValidationIssue("warning", f"{pages_with_rotation} page(s) have a rotation set. Ensure orientation is intended."))
    if pages_with_annots > 0:
        issues.append(ValidationIssue("error", f"{pages_with_annots} page(s) contain annotations/form fields. Remove all interactive elements for print."))
    if image_object_count > 0:
        issues.append(ValidationIssue("info", f"Detected {image_object_count} embedded image object(s). Verify print DPI ≥ 300 if images are used."))
    if low_res_image_guess > 0:
        issues.append(ValidationIssue("warning", f"{low_res_image_guess} image(s) have small intrinsic size (<900 px). They may print under 300 DPI if scaled large."))
    # Fonts summary
    if fonts_type3:
        issues.append(ValidationIssue("warning", f"Type3 font(s) used: {sorted(fonts_type3)}. Type3 can print poorly; prefer embedded Type1/TrueType/OpenType."))
    if fonts_not_embedded:
        issues.append(ValidationIssue("error", f"Non-embedded font(s) detected: {sorted(fonts_not_embedded)}. All fonts must be embedded for print."))
    if fonts_subset:
        issues.append(ValidationIssue("info", f"Subset embedded font(s): {sorted(fonts_subset)}."))

    # Report uses first page size for summary (fallback if empty doc)
    if num_pages > 0:
        first_w = float(reader.pages[0].mediabox.width)
        first_h = float(reader.pages[0].mediabox.height)
    else:
        first_w = first_h = 0.0

    return ValidationReport(
        ok=ok,
        trim_key=trim_key,
        page_count=num_pages,
        page_size_pt=(first_w, first_h),
        issues=issues,
    )
