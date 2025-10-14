from dataclasses import dataclass
from typing import List, Tuple
import re
import math
from io import BytesIO
try:
    from PIL import Image  # type: ignore
except Exception:  # Pillow not installed; inline image DPI will be skipped
    Image = None  # type: ignore

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


def validate_pdf(pdf_path: str, trim_key: str, verbose: bool = False) -> ValidationReport:
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

    # Bleed auto-detect (common 0.125in = 9pt bleed). For interiors, width adds bleed on outer edge only (once),
    # height adds bleed on both top and bottom (twice).
    bleed_pt_detected: float | None = None
    expected_w = target_w
    expected_h = target_h
    if num_pages > 0:
        try:
            _w0 = float(reader.pages[0].mediabox.width)
            _h0 = float(reader.pages[0].mediabox.height)
            if _almost_equal(_w0, target_w) and _almost_equal(_h0, target_h):
                bleed_pt_detected = 0.0
            else:
                dw = _w0 - target_w
                dh = _h0 - target_h
                # Detect ~9pt width and ~18pt height increase (±0.75pt tolerance)
                if 8.25 <= dw <= 9.75 and 17.25 <= dh <= 18.75:
                    bleed_pt_detected = round(dh / 2.0, 3)
                    expected_w = target_w + bleed_pt_detected
                    expected_h = target_h + 2 * bleed_pt_detected
                else:
                    # Keep defaults; pages will be validated individually and flagged if mismatched
                    pass
        except Exception:
            pass

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

    dpi_checks = 0
    do_ops_total = 0
    do_ops_images = 0
    do_ops_forms = 0
    patterns_found = 0
    patterns_processed = 0
    shadings_found = 0
    shadings_processed = 0
    groups_found = 0
    groups_processed = 0

    for i, page in enumerate(reader.pages, start=1):
        media_box = page.mediabox
        w = float(media_box.width)
        h = float(media_box.height)
        # Accept rotation-independent match, with optional bleed allowance
        exp_w = expected_w
        exp_h = expected_h
        size_match = (_almost_equal(w, exp_w) and _almost_equal(h, exp_h)) or (
            _almost_equal(w, exp_h) and _almost_equal(h, exp_w)
        )
        if not size_match:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Page {i} size {w:.2f}x{h:.2f} pt does not match expected {'bleed' if (bleed_pt_detected and bleed_pt_detected>0) else 'trim'} size ({exp_w:.2f}x{exp_h:.2f} pt).",
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

        # Image DPI estimation: handle direct and nested (Form XObject) placements
        try:
            def mul(m1, m2):
                a1, b1, c1, d1, e1, f1 = m1
                a2, b2, c2, d2, e2, f2 = m2
                return [
                    a1 * a2 + b1 * c2,
                    a1 * b2 + b1 * d2,
                    c1 * a2 + d1 * c2,
                    c1 * b2 + d1 * d2,
                    e1 * a2 + f1 * c2 + e2,
                    e1 * b2 + f1 * d2 + f2,
                ]

            # Build string-keyed XObject map for lookup
            xobject_dict = {}
            if xobj and hasattr(xobj, "items"):
                for k, v in xobj.items():
                    xobject_dict[str(k)] = v

            def process_stream(res, contents, ctm_current):
                cur_xobj = res.get("/XObject") if hasattr(res, "get") else None
                img_px = {}
                if cur_xobj and hasattr(cur_xobj, "items"):
                    for name, obj in cur_xobj.items():
                        try:
                            if str(obj.get("/Subtype")) == "/Image":
                                img_px[str(name)] = (int(obj.get("/Width")), int(obj.get("/Height")))
                        except Exception:
                            continue

                data = b""
                if contents is not None:
                    if isinstance(contents, list):
                        for cs in contents:
                            try:
                                data += cs.get_data()
                            except Exception:
                                pass
                    else:
                        try:
                            data = contents.get_data()
                        except Exception:
                            data = b""
                if not data:
                    return

                s = data.decode("latin-1", errors="ignore")
                tokens = re.findall(r"cm|Do|q|Q|/[^^\s<>\[\]\(\)]+|-?\d*\.??\d+(?:[eE][+-]?\d+)?|BI|ID|EI|scn|SCN|cs|CS", s)
                ctm_stack = [ctm_current[:]]

                idx = 0
                while idx < len(tokens):
                    tkn = tokens[idx]
                    if tkn == "q":
                        ctm_stack.append(ctm_stack[-1][:])
                        idx += 1
                        continue
                    if tkn == "Q":
                        if len(ctm_stack) > 1:
                            ctm_stack.pop()
                        idx += 1
                        continue
                    if tkn == "cm":
                        try:
                            nums = [float(tokens[idx - 6 + k]) for k in range(6)]
                            ctm_stack[-1] = mul(ctm_stack[-1], [nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]])
                        except Exception:
                            pass
                        idx += 1
                        continue
                    if tkn == "Do":
                        try:
                            name = tokens[idx - 1]
                            if not name.startswith("/"):
                                idx += 1
                                continue
                            cur_ctm = ctm_stack[-1]
                            do_ops_total += 1
                            if name in img_px:
                                do_ops_images += 1
                                a, b, c_, d, e_, f_ = cur_ctm
                                sx = math.hypot(a, b)
                                sy = math.hypot(c_, d)
                                wpx, hpx = img_px[name]
                                if sx > 0 and sy > 0:
                                    dpi_x = (wpx * 72.0) / sx
                                    dpi_y = (hpx * 72.0) / sy
                                    dpi_min = min(dpi_x, dpi_y)
                                    issues.append(ValidationIssue("info", f"Page {i}: Image '{name}' estimated DPI {dpi_x:.0f}x{dpi_y:.0f} (min {dpi_min:.0f})."))
                                    dpi_checks += 1
                                    if dpi_min < 200:
                                        issues.append(ValidationIssue("error", f"Page {i}: Image '{name}' estimated DPI {dpi_min:.0f} (<200)."))
                                    elif dpi_min < 300:
                                        issues.append(ValidationIssue("warning", f"Page {i}: Image '{name}' estimated DPI {dpi_min:.0f} (<300)."))
                            else:
                                # Maybe a Form XObject; resolve and recurse
                                form_obj = None
                                if cur_xobj and hasattr(cur_xobj, "get"):
                                    try:
                                        form_obj = cur_xobj.get(name)
                                    except Exception:
                                        form_obj = None
                                if form_obj is None:
                                    form_obj = xobject_dict.get(name)
                                if form_obj is not None and str(form_obj.get("/Subtype")) == "/Form":
                                    do_ops_forms += 1
                                    new_ctm = cur_ctm[:]
                                    try:
                                        m_arr = form_obj.get("/Matrix")
                                        if m_arr and len(m_arr) == 6:
                                            m = [float(m_arr[0]), float(m_arr[1]), float(m_arr[2]), float(m_arr[3]), float(m_arr[4]), float(m_arr[5])]
                                            new_ctm = mul(cur_ctm, m)
                                    except Exception:
                                        pass
                                    form_res = form_obj.get("/Resources") or res
                                    form_contents = form_obj.get_contents()
                                    process_stream(form_res, form_contents, new_ctm)
                        except Exception:
                            pass
                        idx += 1
                        continue
                    # Skip inline image tokens for now
                    if tkn in ("BI", "ID", "EI"):
                        idx += 1
                        continue
                    idx += 1

            page_res = page.get("/Resources") or {}
            def process_patterns(res, base_ctm):
                nonlocal patterns_found, patterns_processed
                pat = res.get("/Pattern") if hasattr(res, "get") else None
                if not pat or not hasattr(pat, "items"):
                    return
                for _, pobj in pat.items():
                    try:
                        patterns_found += 1
                        contents = pobj.get_contents()
                        if contents is None:
                            continue
                        m = base_ctm[:]
                        try:
                            m_arr = pobj.get("/Matrix")
                            if m_arr and len(m_arr) == 6:
                                m = mul(base_ctm, [float(m_arr[0]), float(m_arr[1]), float(m_arr[2]), float(m_arr[3]), float(m_arr[4]), float(m_arr[5])])
                        except Exception:
                            pass
                        res2 = pobj.get("/Resources") or res
                        process_stream(res2, contents, m)
                        patterns_processed += 1
                    except Exception:
                        continue

            # Process shadings in page resources
            def process_shadings(res, base_ctm):
                nonlocal shadings_found, shadings_processed
                shad = res.get("/Shading") if hasattr(res, "get") else None
                if not shad or not hasattr(shad, "items"):
                    return
                for _, sobj in shad.items():
                    try:
                        shadings_found += 1
                        # Shading types 1-3 (function-based) don't have content streams, but others might
                        if str(sobj.get("/ShadingType")) in ("4", "5", "6", "7"):  # Gouraud, Coons, Tensor, Free-form
                            contents = sobj.get_contents()
                            if contents is None:
                                continue
                            m = base_ctm[:]
                            try:
                                m_arr = sobj.get("/Matrix")
                                if m_arr and len(m_arr) == 6:
                                    m = mul(base_ctm, [float(m_arr[0]), float(m_arr[1]), float(m_arr[2]), float(m_arr[3]), float(m_arr[4]), float(m_arr[5])])
                            except Exception:
                                pass
                            res2 = sobj.get("/Resources") or res
                            process_stream(res2, contents, m)
                            shadings_processed += 1
                    except Exception:
                        continue

            # Process transparency groups if present
            def process_groups(res, base_ctm):
                nonlocal groups_found, groups_processed
                grp = res.get("/Group") if hasattr(res, "get") else None
                if grp and hasattr(grp, "get"):
                    try:
                        groups_found += 1
                        # Transparency groups can have content streams
                        contents = grp.get_contents()
                        if contents is None:
                            return
                        m = base_ctm[:]
                        try:
                            m_arr = grp.get("/Matrix")
                            if m_arr and len(m_arr) == 6:
                                m = mul(base_ctm, [float(m_arr[0]), float(m_arr[1]), float(m_arr[2]), float(m_arr[3]), float(m_arr[4]), float(m_arr[5])])
                        except Exception:
                            pass
                        res2 = grp.get("/Resources") or res
                        process_stream(res2, contents, m)
                        groups_processed += 1
                    except Exception:
                        pass

            process_patterns(page_res, [1, 0, 0, 1, 0, 0])
            process_shadings(page_res, [1, 0, 0, 1, 0, 0])
            process_groups(page_res, [1, 0, 0, 1, 0, 0])
            process_stream(page_res, page.get_contents(), [1, 0, 0, 1, 0, 0])
        except Exception:
            pass

    if image_object_count > 0:
        issues.append(ValidationIssue("info", f"Detected {image_object_count} embedded image object(s). Verify print DPI ≥ 300 if images are used."))
    if low_res_image_guess > 0:
        issues.append(ValidationIssue("warning", f"{low_res_image_guess} image(s) have small intrinsic size (<900 px). They may print under 300 DPI if scaled large."))
    # Bleed detection summary
    if bleed_pt_detected is None:
        issues.append(ValidationIssue("info", "Bleed: could not auto-detect (non-standard size)."))
    elif bleed_pt_detected == 0.0:
        issues.append(ValidationIssue("info", "Bleed: not detected (trim size)."))
    else:
        issues.append(ValidationIssue("info", f"Bleed: detected ~{bleed_pt_detected:.1f} pt (≈ {bleed_pt_detected/72.0:.3f} in)."))
    # Fonts summary
    if fonts_type3:
        issues.append(ValidationIssue("warning", f"Type3 font(s) used: {sorted(fonts_type3)}. Type3 can print poorly; prefer embedded Type1/TrueType/OpenType."))
    if fonts_not_embedded:
        issues.append(ValidationIssue("error", f"Non-embedded font(s) detected: {sorted(fonts_not_embedded)}. All fonts must be embedded for print."))
    if fonts_subset:
        issues.append(ValidationIssue("info", f"Subset embedded font(s): {sorted(fonts_subset)}."))

    ok = not any(iss.level == "error" for iss in issues)
    # Summaries
    if dpi_checks == 0 and image_object_count > 0:
        issues.append(ValidationIssue("info", "Images detected but DPI could not be estimated (images may be drawn via unsupported operators)."))
    elif dpi_checks == 0 and image_object_count == 0:
        issues.append(ValidationIssue("info", "No embedded images detected in PDF."))
    elif dpi_checks > 0:
        issues.append(ValidationIssue("info", f"Estimated DPI for {dpi_checks} image placement(s)."))

    if verbose:
        issues.append(ValidationIssue("info", f"Diagnostics: Do={do_ops_total}, images={do_ops_images}, forms={do_ops_forms}, patterns={patterns_processed}/{patterns_found}, shadings={shadings_processed}/{shadings_found}, groups={groups_processed}/{groups_found}, dpi_placements={dpi_checks}"))

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
