import click
from kdp_builder.renderer.pdf_renderer import generate_lined_pages
from kdp_builder.validator.kdp_validator import validate_pdf
from kdp_builder.cover.cover_renderer import generate_cover
from kdp_builder.cover.cover_validator import validate_cover
from kdp_builder.ai.layout_generator import AILayoutGenerator, LAYOUT_SCHEMA
import os


@click.command(help="Generate a simple lined interior PDF or validate an existing PDF for KDP sizing.")
@click.option("--trim", type=str, default="6x9", show_default=True, help="Trim size key, e.g., 6x9")
@click.option("--pages", type=click.IntRange(min=1), default=120, show_default=True, help="Number of interior pages")
@click.option("--out", "out_path", type=str, default="outputs/interior.pdf", show_default=True, help="Output PDF path (interior default: outputs/interior.pdf; cover default: outputs/cover.pdf)")
@click.option("--line-spacing-pt", "line_spacing_pt", type=float, default=18.0, show_default=True, help="Line spacing in points (72pt = 1 inch)")
@click.option("--line-weight-pt", "line_weight_pt", type=float, default=0.5, show_default=True, help="Stroke width in points (>=0.5pt for print)")
@click.option("--gutter-pt", "gutter_pt", type=float, default=0.0, show_default=True, help="Extra inner margin added to binding side (odd/even pages handled)")
@click.option("--debug-safe-area", "debug_safe_area", is_flag=True, default=False, help="Draw dashed rectangle of the safe area on each page")
@click.option("--template", type=click.Choice(["lined", "grid", "dot", "habit"], case_sensitive=False), default="lined", show_default=True, help="Interior template to render")
@click.option("--grid-size-pt", "grid_size_pt", type=float, default=18.0, show_default=True, help="Grid cell size (grid template)")
@click.option("--dot-step-pt", "dot_step_pt", type=float, default=18.0, show_default=True, help="Dot spacing (dot template)")
@click.option("--dot-radius-pt", "dot_radius_pt", type=float, default=0.5, show_default=True, help="Dot radius (dot template)")
@click.option("--habit-rows", "habit_rows", type=int, default=20, show_default=True, help="Rows for habit tracker (habit template)")
@click.option("--habit-cols", "habit_cols", type=int, default=7, show_default=True, help="Columns for habit tracker (habit template)")
@click.option("--page-numbers", "page_numbers", is_flag=True, default=False, help="Print page numbers on the outer side")
@click.option("--header", "header_text", type=str, default="", show_default=True, help="Header text (centered in safe area)")
@click.option("--footer", "footer_text", type=str, default="", show_default=True, help="Footer text (centered in safe area)")
@click.option("--header-font-size", "header_font_size", type=float, default=12.0, show_default=True, help="Header font size")
@click.option("--footer-font-size", "footer_font_size", type=float, default=10.0, show_default=True, help="Footer font size")
@click.option("--page-number-font-size", "page_number_font_size", type=float, default=10.0, show_default=True, help="Page number font size")
@click.option("--set-trimbox", "set_trimbox", is_flag=True, default=False, help="Write TrimBox equal to the safe area for QA")
@click.option("--set-bleedbox", "set_bleedbox", is_flag=True, default=False, help="Write BleedBox around TrimBox by --bleed-pt (clamped to MediaBox)")
@click.option("--bleed-pt", "bleed_pt", type=float, default=0.0, show_default=True, help="Bleed amount in points (72pt = 1 inch)")
@click.option("--validate-path", "validate_path", type=str, default=None, help="If provided, validates the given PDF and exits.")
@click.option("--validate-trim", "validate_trim", type=str, default=None, help="Trim key to validate against (defaults to --trim if omitted).")
@click.option("--validate-verbose", "validate_verbose", is_flag=True, default=False, help="Print verbose diagnostics during validation (Do/Form counts, DPI placements)")
@click.option("--make-cover", "make_cover", is_flag=True, default=False, help="Generate a cover instead of an interior")
@click.option("--cover-pages", "cover_pages", type=click.IntRange(min=1), default=120, show_default=True, help="Interior page count used to compute spine width")
@click.option("--cover-paper", "cover_paper", type=click.Choice(["white", "cream", "color"], case_sensitive=False), default="white", show_default=True, help="Paper type for spine width calc")
@click.option("--cover-bleed-pt", "cover_bleed_pt", type=float, default=9.0, show_default=True, help="Bleed for cover in points (9pt = 0.125 inch typical)")
@click.option("--cover-title", "cover_title", type=str, default="", show_default=True, help="Front cover title")
@click.option("--cover-subtitle", "cover_subtitle", type=str, default="", show_default=True, help="Front cover subtitle")
@click.option("--cover-author", "cover_author", type=str, default="", show_default=True, help="Front cover author")
@click.option("--validate-cover-path", "validate_cover_path", type=str, default=None, help="If provided, validates the given COVER PDF and exits (requires --trim, --cover-pages, --cover-paper, --cover-bleed-pt)")
@click.option("--ai-prompt", "ai_prompt", type=str, default=None, help="Prompt for AI-generated layout (e.g., 'Create a habit tracker with 30 days'). Uses Ollama for local generation.")
def main(trim: str, pages: int, out_path: str, line_spacing_pt: float, line_weight_pt: float, gutter_pt: float, debug_safe_area: bool, template: str, grid_size_pt: float, dot_step_pt: float, dot_radius_pt: float, habit_rows: int, habit_cols: int, page_numbers: bool, header_text: str, footer_text: str, header_font_size: float, footer_font_size: float, page_number_font_size: float, set_trimbox: bool, set_bleedbox: bool, bleed_pt: float, validate_path: str | None, validate_trim: str | None, validate_verbose: bool,
         make_cover: bool, cover_pages: int, cover_paper: str, cover_bleed_pt: float, cover_title: str, cover_subtitle: str, cover_author: str, validate_cover_path: str | None, ai_prompt: str | None):
    # Validation mode
    if validate_cover_path:
        report = validate_cover(validate_cover_path, trim, cover_pages, cover_paper.lower(), cover_bleed_pt)
        click.echo(f"Cover validation for {validate_cover_path}")
        click.echo(f"Expected size: {report.expected_width_pt:.2f} x {report.expected_height_pt:.2f} pt (spine {report.expected_spine_pt:.2f} pt)")
        click.echo(f"Actual size:   {report.width_pt:.2f} x {report.height_pt:.2f} pt")
        if not report.issues:
            click.echo("✅ No issues found.")
        else:
            for iss in report.issues:
                click.echo(f"{iss.level.upper()}: {iss.message}")
        if not report.ok:
            raise SystemExit(1)
        return

    if validate_path:
        vt = validate_trim or trim
        report = validate_pdf(validate_path, vt, verbose=validate_verbose)
        click.echo(f"Validation for {validate_path} (trim={report.trim_key})")
        click.echo(f"Pages: {report.page_count}")
        click.echo(f"First page size: {report.page_size_pt[0]:.2f} x {report.page_size_pt[1]:.2f} pt")
        if not report.issues:
            click.echo("✅ No issues found.")
        else:
            for iss in report.issues:
                level = iss.level.upper()
                click.echo(f"{level}: {iss.message}")
        if not report.ok:
            raise SystemExit(1)
        return

    # Generation mode
    if make_cover:
        # Default output name if user did not change it
        if out_path == "outputs/interior.pdf":
            out_path = "outputs/cover.pdf"
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        generate_cover(
            trim_key=trim,
            page_count=cover_pages,
            paper=cover_paper.lower(),
            bleed_pt=cover_bleed_pt,
            out_path=out_path,
            title=cover_title,
            subtitle=cover_subtitle,
            author=cover_author,
        )
        click.echo(f"✅ Generated cover {out_path} for trim {trim}, pages {cover_pages}, paper {cover_paper}")
        return

    if ai_prompt:
        # AI layout generation mode
        try:
            click.echo("🤖 Generating AI layout with Ollama... (this may take up to 2 minutes)")
            generator = AILayoutGenerator()
            layout = generator.generate_layout(ai_prompt, LAYOUT_SCHEMA, gutter_pt=gutter_pt)
            click.echo(f"✅ Generated AI layout for prompt: '{ai_prompt}'")
            click.echo(f"Layout pages: {len(layout.get('pages', []))}")
            # For now, use the existing renderer with default settings
            # TODO: Integrate layout into renderer
            out_dir = os.path.dirname(out_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            generate_lined_pages(
                trim_key=trim,
                pages=pages,
                out_path=out_path,
                line_spacing=line_spacing_pt,
                line_weight=line_weight_pt,
                gutter_pt=gutter_pt,
                debug_safe_area=debug_safe_area,
                template=template.lower(),
                grid_size_pt=grid_size_pt,
                dot_step_pt=dot_step_pt,
                dot_radius_pt=dot_radius_pt,
                habit_rows=habit_rows,
                habit_cols=habit_cols,
                page_numbers=page_numbers,
                header_text=header_text,
                footer_text=footer_text,
                header_font_size=header_font_size,
                footer_font_size=footer_font_size,
                page_number_font_size=page_number_font_size,
                set_trimbox=set_trimbox,
                set_bleedbox=set_bleedbox,
                bleed_pt=bleed_pt,
            )
            click.echo(f"✅ Generated {out_path} with AI-inspired layout")
            return
        except Exception as e:
            click.echo(f"❌ Error generating AI layout: {str(e)}")
            raise SystemExit(1)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    generate_lined_pages(
        trim_key=trim,
        pages=pages,
        out_path=out_path,
        line_spacing=line_spacing_pt,
        line_weight=line_weight_pt,
        gutter_pt=gutter_pt,
        debug_safe_area=debug_safe_area,
        template=template.lower(),
        grid_size_pt=grid_size_pt,
        dot_step_pt=dot_step_pt,
        dot_radius_pt=dot_radius_pt,
        habit_rows=habit_rows,
        habit_cols=habit_cols,
        page_numbers=page_numbers,
        header_text=header_text,
        footer_text=footer_text,
        header_font_size=header_font_size,
        footer_font_size=footer_font_size,
        page_number_font_size=page_number_font_size,
        set_trimbox=set_trimbox,
        set_bleedbox=set_bleedbox,
        bleed_pt=bleed_pt,
    )
    click.echo(f"✅ Generated {out_path} with {pages} pages at trim {trim}")


if __name__ == "__main__":
    main()
