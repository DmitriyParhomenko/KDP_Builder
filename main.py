import click
from kdp_builder.renderer.pdf_renderer import generate_lined_pages


@click.command(help="Generate a simple lined interior PDF suitable for KDP.")
@click.option("--trim", type=str, default="6x9", show_default=True, help="Trim size key, e.g., 6x9")
@click.option("--pages", type=click.IntRange(min=1), default=120, show_default=True, help="Number of interior pages")
@click.option("--out", "out_path", type=str, default="interior.pdf", show_default=True, help="Output PDF path")
@click.option("--line-spacing-pt", "line_spacing_pt", type=float, default=18.0, show_default=True, help="Line spacing in points (72pt = 1 inch)")
@click.option("--line-weight-pt", "line_weight_pt", type=float, default=0.5, show_default=True, help="Stroke width in points (>=0.5pt for print)")
def main(trim: str, pages: int, out_path: str, line_spacing_pt: float, line_weight_pt: float):
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
