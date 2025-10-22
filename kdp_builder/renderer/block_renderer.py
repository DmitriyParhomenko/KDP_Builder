"""
Block-to-PDF Renderer

Converts AI-composed block layouts into print-ready PDFs.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black
from reportlab.lib.units import inch
from typing import Dict, List, Any

from kdp_builder.blocks.block_library import BlockLibrary
from kdp_builder.config.sizes import SIZES


class BlockRenderer:
    """Renders block-based layouts to PDF"""
    
    def __init__(self, library_path: str = "kdp_builder/blocks/library"):
        """
        Initialize block renderer.
        
        Args:
            library_path: Path to block library
        """
        self.library = BlockLibrary(library_path)
    
    def render_composition_to_pdf(
        self,
        composition: Dict[str, Any],
        out_path: str,
        trim_key: str = "6x9",
        set_bleedbox: bool = True,
        bleed_pt: float = 9.0
    ):
        """
        Render a block composition to PDF.
        
        Args:
            composition: Composition from AIBlockComposer
            out_path: Output PDF path
            trim_key: Trim size key
            set_bleedbox: Whether to set bleed box
            bleed_pt: Bleed amount
        """
        if trim_key not in SIZES:
            raise ValueError(f"Unknown trim key '{trim_key}'")
        
        conf = SIZES[trim_key]
        width = conf["width"]
        height = conf["height"]
        
        c = canvas.Canvas(out_path, pagesize=(width, height))
        
        pages = composition.get("pages", [])
        
        for page in pages:
            page_num = page.get("page_number", 1)
            block_placements = page.get("blocks", [])
            
            # Render each block
            for placement in block_placements:
                block_id = placement.get("block_id")
                block = self.library.get_block(block_id)
                
                if not block:
                    continue
                
                # Get placement coordinates
                x = placement.get("x", 0)
                y = placement.get("y", 0)
                block_width = placement.get("width", block["dimensions"]["width"])
                block_height = placement.get("height", block["dimensions"]["height"])
                
                # Render block elements
                self._render_block(c, block, x, y, block_width, block_height)
            
            c.showPage()
        
        c.save()
        
        # Add bleed box if requested
        if set_bleedbox:
            self._add_bleedbox(out_path, trim_key, bleed_pt)
    
    def _render_block(
        self,
        c: canvas.Canvas,
        block: Dict[str, Any],
        x_offset: float,
        y_offset: float,
        block_width: float,
        block_height: float
    ):
        """
        Render a single block's elements.
        
        Args:
            c: ReportLab canvas
            block: Block definition
            x_offset: X position on page
            y_offset: Y position on page
            block_width: Rendered width
            block_height: Rendered height
        """
        elements = block.get("elements", [])
        original_width = block["dimensions"]["width"]
        original_height = block["dimensions"]["height"]
        
        # Calculate scaling factors if block is resized
        scale_x = block_width / original_width if original_width > 0 else 1.0
        scale_y = block_height / original_height if original_height > 0 else 1.0
        
        for element in elements:
            element_type = element.get("type")
            
            # Scale element coordinates
            ex = x_offset + (element.get("x", 0) * scale_x)
            ey = y_offset + (element.get("y", 0) * scale_y)
            ew = element.get("width", 0) * scale_x
            eh = element.get("height", 0) * scale_y
            
            style = element.get("style", {})
            
            # Render based on type
            if element_type == "text":
                self._render_text(c, element, ex, ey, ew, eh, style)
            elif element_type == "line":
                self._render_line(c, ex, ey, ew, eh, style)
            elif element_type == "rectangle":
                self._render_rectangle(c, ex, ey, ew, eh, style)
            elif element_type == "circle":
                self._render_circle(c, ex, ey, ew, eh, style)
            elif element_type == "checkbox":
                self._render_checkbox(c, ex, ey, ew, eh, style)
    
    def _render_text(
        self,
        c: canvas.Canvas,
        element: Dict[str, Any],
        x: float,
        y: float,
        width: float,
        height: float,
        style: Dict[str, Any]
    ):
        """Render text element"""
        content = element.get("content", "")
        
        # Only skip if it's ONLY a placeholder, not if it has actual text
        if content and "{{" in content and "}}" in content and content.strip().startswith("{{"):
            return  # Skip pure template placeholders
        
        if not content:
            return
        
        c.saveState()
        
        # Set font
        font_family = style.get("fontFamily", "Helvetica")
        font_size = style.get("fontSize", 12)
        
        # Handle font family variations
        try:
            c.setFont(font_family, font_size)
        except:
            # Fallback to Helvetica if font not found
            c.setFont("Helvetica", font_size)
        
        # Set color
        color = style.get("color", "#000000")
        if color.startswith("#"):
            c.setFillColor(HexColor(color))
        
        # Draw text (centered if width is specified)
        if width > 0:
            c.drawCentredString(x + width / 2, y, content)
        else:
            c.drawString(x, y, content)
        
        c.restoreState()
    
    def _render_line(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        style: Dict[str, Any]
    ):
        """Render line element"""
        c.saveState()
        
        line_weight = style.get("lineWeight", 0.5)
        c.setLineWidth(line_weight)
        
        color = style.get("color", "#000000")
        if color.startswith("#"):
            c.setStrokeColor(HexColor(color))
        
        # Draw line
        if width > height:
            # Horizontal line
            c.line(x, y, x + width, y)
        else:
            # Vertical line
            c.line(x, y, x, y + height)
        
        c.restoreState()
    
    def _render_rectangle(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        style: Dict[str, Any]
    ):
        """Render rectangle element"""
        c.saveState()
        
        line_weight = style.get("lineWeight", 1)
        c.setLineWidth(line_weight)
        
        # Stroke color
        color = style.get("color", "#000000")
        if color.startswith("#"):
            c.setStrokeColor(HexColor(color))
        
        # Fill color
        fill_color = style.get("fillColor")
        if fill_color and fill_color.startswith("#"):
            c.setFillColor(HexColor(fill_color))
            c.rect(x, y, width, height, stroke=1, fill=1)
        else:
            c.rect(x, y, width, height, stroke=1, fill=0)
        
        c.restoreState()
    
    def _render_circle(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        style: Dict[str, Any]
    ):
        """Render circle element"""
        c.saveState()
        
        line_weight = style.get("lineWeight", 1)
        c.setLineWidth(line_weight)
        
        # Stroke color
        color = style.get("color", "#000000")
        if color.startswith("#"):
            c.setStrokeColor(HexColor(color))
        
        # Fill color
        fill_color = style.get("fillColor")
        if fill_color and fill_color.startswith("#"):
            c.setFillColor(HexColor(fill_color))
            c.circle(x + width / 2, y + height / 2, width / 2, stroke=1, fill=1)
        else:
            c.circle(x + width / 2, y + height / 2, width / 2, stroke=1, fill=0)
        
        c.restoreState()
    
    def _render_checkbox(
        self,
        c: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        style: Dict[str, Any]
    ):
        """Render checkbox element"""
        c.saveState()
        
        c.setLineWidth(0.5)
        c.setStrokeColor(black)
        c.rect(x, y, width, height, stroke=1, fill=0)
        
        c.restoreState()
    
    def _add_bleedbox(self, pdf_path: str, trim_key: str, bleed_pt: float):
        """Add bleed box to PDF"""
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import RectangleObject
        
        conf = SIZES[trim_key]
        width = conf["width"]
        height = conf["height"]
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            media = page.mediabox
            
            # Set bleed box
            bleed_rect = RectangleObject([
                max(0, media.left - bleed_pt),
                max(0, media.bottom - bleed_pt),
                min(width, media.right + bleed_pt),
                min(height, media.top + bleed_pt)
            ])
            page.bleedbox = bleed_rect
            
            writer.add_page(page)
        
        with open(pdf_path, "wb") as f:
            writer.write(f)
