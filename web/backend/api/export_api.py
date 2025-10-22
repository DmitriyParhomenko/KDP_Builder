"""
Export API endpoints

Convert visual designs to print-ready PDFs.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from web.backend.models.design import Design, DesignElement

router = APIRouter()

# Export directory
EXPORTS_DIR = Path("./exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

class ExportRequest(BaseModel):
    """Request to export design to PDF"""
    design: Design
    include_bleed: bool = True
    bleed_pt: float = 9.0

class ExportResponse(BaseModel):
    """Response with export status"""
    success: bool
    message: str
    file_path: str = ""
    download_url: str = ""

def _render_element(c: canvas.Canvas, element: DesignElement):
    """Render a single element to PDF canvas"""
    elem_type = element.type
    props = element.properties
    
    c.saveState()
    
    if elem_type == "text":
        # Render text
        text = props.get("text", "")
        font_family = props.get("fontFamily", "Helvetica")
        font_size = props.get("fontSize", 12)
        color = props.get("color", "#000000")
        align = props.get("align", "left")
        
        try:
            c.setFont(font_family, font_size)
        except:
            c.setFont("Helvetica", font_size)
        
        if color.startswith("#"):
            c.setFillColor(HexColor(color))
        
        if align == "center":
            c.drawCentredString(element.x + element.width / 2, element.y, text)
        elif align == "right":
            c.drawRightString(element.x + element.width, element.y, text)
        else:
            c.drawString(element.x, element.y, text)
    
    elif elem_type == "rectangle":
        # Render rectangle
        fill = props.get("fill", "none")
        stroke = props.get("stroke", "#000000")
        stroke_width = props.get("strokeWidth", 1.0)
        
        c.setLineWidth(stroke_width)
        
        if stroke.startswith("#"):
            c.setStrokeColor(HexColor(stroke))
        
        if fill != "none" and fill.startswith("#"):
            c.setFillColor(HexColor(fill))
            c.rect(element.x, element.y, element.width, element.height, fill=1, stroke=1)
        else:
            c.rect(element.x, element.y, element.width, element.height, fill=0, stroke=1)
    
    elif elem_type == "circle":
        # Render circle
        fill = props.get("fill", "none")
        stroke = props.get("stroke", "#000000")
        stroke_width = props.get("strokeWidth", 1.0)
        
        c.setLineWidth(stroke_width)
        
        if stroke.startswith("#"):
            c.setStrokeColor(HexColor(stroke))
        
        radius = min(element.width, element.height) / 2
        center_x = element.x + element.width / 2
        center_y = element.y + element.height / 2
        
        if fill != "none" and fill.startswith("#"):
            c.setFillColor(HexColor(fill))
            c.circle(center_x, center_y, radius, fill=1, stroke=1)
        else:
            c.circle(center_x, center_y, radius, fill=0, stroke=1)
    
    elif elem_type == "line":
        # Render line
        stroke = props.get("stroke", "#000000")
        stroke_width = props.get("strokeWidth", 1.0)
        
        c.setLineWidth(stroke_width)
        
        if stroke.startswith("#"):
            c.setStrokeColor(HexColor(stroke))
        
        c.line(element.x, element.y, element.x + element.width, element.y + element.height)
    
    c.restoreState()

@router.post("/pdf", response_model=ExportResponse)
async def export_to_pdf(request: ExportRequest):
    """
    Export design to print-ready PDF.
    
    Converts the visual design to a KDP-compliant PDF file.
    
    Args:
        request: Export request with design and options
    """
    try:
        design = request.design
        
        # Generate filename
        filename = f"{design.name.replace(' ', '_')}_{design.id}.pdf"
        output_path = EXPORTS_DIR / filename
        
        # Calculate page size with bleed
        if request.include_bleed:
            page_width = design.page_width + (2 * request.bleed_pt)
            page_height = design.page_height + (2 * request.bleed_pt)
            offset_x = request.bleed_pt
            offset_y = request.bleed_pt
        else:
            page_width = design.page_width
            page_height = design.page_height
            offset_x = 0
            offset_y = 0
        
        # Create PDF
        c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
        
        # Render each page
        for page in design.pages:
            # Sort elements by z_index
            sorted_elements = sorted(page.elements, key=lambda e: e.z_index)
            
            # Render each element
            for element in sorted_elements:
                # Adjust position for bleed
                adjusted_element = element.copy()
                adjusted_element.x += offset_x
                adjusted_element.y += offset_y
                
                _render_element(c, adjusted_element)
            
            # Next page (if not last)
            if page.page_number < len(design.pages):
                c.showPage()
        
        # Save PDF
        c.save()
        
        return ExportResponse(
            success=True,
            message="PDF exported successfully",
            file_path=str(output_path),
            download_url=f"/api/export/download/{filename}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_pdf(filename: str):
    """
    Download exported PDF.
    
    Args:
        filename: PDF filename
    """
    file_path = EXPORTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )
