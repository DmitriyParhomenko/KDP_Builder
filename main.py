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
@click.option("--validate-path", "validate_path", type=str, default=None, help="If provided, validates the given PDF and exits.")
@click.option("--validate-trim", "validate_trim", type=str, default=None, help="Trim key to validate against (defaults to --trim if omitted).")
def main(trim: str, pages: int, out_path: str, line_spacing_pt: float, line_weight_pt: float, validate_path: str | None, validate_trim: str | None):
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
    )
    click.echo(f"✅ Generated {out_path} with {pages} pages at trim {trim}")


if __name__ == "__main__":
    main()
