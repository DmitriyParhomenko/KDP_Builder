import click
from kdp_builder.renderer.pdf_renderer import generate_lined_pages
from kdp_builder.validator.kdp_validator import validate_pdf
import os


@click.command(help="Generate a simple lined interior PDF or validate an existing PDF for KDP sizing.")
@click.option("--trim", type=str, default="6x9", show_default=True, help="Trim size key, e.g., 6x9")
@click.option("--pages", type=click.IntRange(min=1), default=120, show_default=True, help="Number of interior pages")
@click.option("--out", "out_path", type=str, default="outputs/interior.pdf", show_default=True, help="Output PDF path")
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
@click.option("--validate-path", "validate_path", type=str, default=None, help="If provided, validates the given PDF and exits.")
@click.option("--validate-trim", "validate_trim", type=str, default=None, help="Trim key to validate against (defaults to --trim if omitted).")
def main(trim: str, pages: int, out_path: str, line_spacing_pt: float, line_weight_pt: float, gutter_pt: float, debug_safe_area: bool, template: str, grid_size_pt: float, dot_step_pt: float, dot_radius_pt: float, habit_rows: int, habit_cols: int, page_numbers: bool, header_text: str, footer_text: str, header_font_size: float, footer_font_size: float, page_number_font_size: float, validate_path: str | None, validate_trim: str | None):
    # Validation mode
    if validate_path:
        vt = validate_trim or trim
        report = validate_pdf(validate_path, vt)
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
    )
    click.echo(f"✅ Generated {out_path} with {pages} pages at trim {trim}")


if __name__ == "__main__":
    main()
