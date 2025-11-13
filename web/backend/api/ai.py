"""
AI API endpoints

AI-powered layout suggestions and pattern learning.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..main import STORAGE_DIR
from ..services.pattern_db import pattern_db
from ..services.ai_service import ai_service
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

router = APIRouter(prefix="/api/ai", tags=["ai"])
from web.backend.services.ai_service import ai_service
from web.backend.services.pattern_db import pattern_db
from kdp_builder.analysis.pdf_analyzer import PDFDesignAnalyzer

router = APIRouter()

class LayoutRequest(BaseModel):
    """Request for layout generation"""
    prompt: str
    page_width: float = 432.0
    page_height: float = 648.0
    rag: bool = True

class LayoutResponse(BaseModel):
    """Response with generated layout"""
    success: bool
    elements: List[Dict[str, Any]] = []
    context_patterns: List[str] = []
    model: str = ""
    error: Optional[str] = None

class ImprovementRequest(BaseModel):
    """Request for design improvements"""
    design: Dict[str, Any]

class ImprovementResponse(BaseModel):
    """Response with improvement suggestions"""
    success: bool
    suggestions: List[str]

class PatternResponse(BaseModel):
    """Response with pattern data"""
    success: bool
    patterns: List[Dict[str, Any]]
    total: int

@router.post("/suggest", response_model=LayoutResponse)
async def suggest_layout(request: LayoutRequest):
    """
    Generate AI layout suggestions.
    
    Uses Ollama (Qwen2.5:7b) to generate layout based on learned patterns.
    
    Args:
        request: Layout request with prompt and dimensions
    """
    try:
        result = ai_service.generate_layout(
            prompt=request.prompt,
            page_width=request.page_width,
            page_height=request.page_height,
            context_patterns=pattern_db.search_patterns(request.prompt, n_results=3) if request.rag else None
        )
        
        return LayoutResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improve", response_model=ImprovementResponse)
async def improve_design(request: ImprovementRequest):
    """
    Get AI suggestions for improving a design.
    
    Args:
        request: Current design data
    """
    try:
        suggestions = ai_service.suggest_improvements(request.design)
        
        return ImprovementResponse(
            success=True,
            suggestions=suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learn")
async def learn_from_pdf(
    file: UploadFile = File(...),
    ai_detect: bool = Query(True, description="Enable AI detection"),
    ai_model: str = Query("both", description="AI model: doclayout, ollama_vl, both"),
    imgsz: int = Query(1536, description="YOLO inference size"),
    tile_size: int = Query(640, description="SAHI tile size"),
    tile_overlap: int = Query(160, description="SAHI tile overlap"),
    use_openrouter: bool = Query(False, description="Use OpenRouter (Claude+Grok) instead of local models"),
):
    """
    Learn design patterns from uploaded PDF.
    
    Analyzes a professional Etsy PDF, extracts blocks with AI, and stores the pattern.
    Returns pattern_id so the UI can load the extracted blocks on canvas.
    
    Args:
        file: PDF file to analyze
        ai_detect: Enable AI vision detection
        ai_model: AI model to use
        imgsz: YOLO inference image size
        tile_size: SAHI tile size
        tile_overlap: SAHI tile overlap
    """
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        import uuid
        import shutil
        from pathlib import Path
        from fastapi import Query

        # Generate a pattern ID and directories
        pattern_id = str(uuid.uuid4())
        from ..main import STORAGE_DIR
        pattern_dir = STORAGE_DIR / pattern_id
        pattern_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded PDF as original.pdf
        pdf_path = pattern_dir / "original.pdf"
        content = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(content)

        # Step 1: Choose extraction method
        if use_openrouter:
            # OpenRouter: Claude analyzes, Grok generates patterns
            print("=== Using OpenRouter (Claude Sonnet 4.5 + Grok Vision) ===")
            try:
                from ..openrouter_client import analyze_with_claude, generate_pattern_with_grok, CLAUDE_EXTRACT_PROMPT, GROK_PATTERN_PROMPT
                from ..extract_utils import pdf_to_pngs
                
                # Rasterize first page for Claude
                raster_dir = pattern_dir / "raster"
                pngs = pdf_to_pngs(str(pdf_path), str(raster_dir), dpi=300)
                print(f"=== Rasterized {len(pngs)} pages ===")
                
                # Analyze with Claude
                print("=== Analyzing with Claude Sonnet 4.5 ===")
                claude_result = await analyze_with_claude(pngs[0], CLAUDE_EXTRACT_PROMPT, timeout_s=90)
                if not claude_result["success"]:
                    raise Exception(f"Claude analysis failed: {claude_result.get('error')}")
                
                analysis = claude_result["content"]
                print(f"=== Claude analysis: {len(analysis)} chars ===")
                
                # Generate pattern with Grok
                print("=== Generating pattern with Grok ===")
                grok_result = await generate_pattern_with_grok(analysis, GROK_PATTERN_PROMPT, timeout_s=60)
                if not grok_result["success"]:
                    raise Exception(f"Grok generation failed: {grok_result.get('error')}")
                
                pattern_json = grok_result["content"]
                print(f"=== Grok pattern: {len(pattern_json)} chars ===")
                
                # Parse blocks from Claude's analysis (JSON extraction)
                import json
                import re
                
                # Try multiple extraction methods
                blocks = []
                try:
                    # Method 1: Look for ```json code block (with optional leading space)
                    json_match = re.search(r'```json\s*(.*?)\s*```', analysis, re.DOTALL | re.IGNORECASE)
                    if json_match:
                        json_str = json_match.group(1).strip()
                        blocks = json.loads(json_str)
                        print(f"✅ Extracted JSON from ```json block")
                    else:
                        # Method 2: Look for any code block
                        json_match = re.search(r'```\s*(.*?)\s*```', analysis, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1).strip()
                            # Remove any language identifier (json, javascript, etc)
                            if json_str.startswith(('json', 'javascript', 'js')):
                                json_str = '\n'.join(json_str.split('\n')[1:])
                            blocks = json.loads(json_str)
                            print(f"✅ Extracted JSON from ``` block")
                        else:
                            # Method 3: Look for JSON array pattern
                            json_match = re.search(r'\[\s*\{.*?\}\s*\]', analysis, re.DOTALL)
                            if json_match:
                                blocks = json.loads(json_match.group(0))
                                print(f"✅ Extracted JSON from array pattern")
                            else:
                                # Method 4: Try entire response
                                blocks = json.loads(analysis.strip())
                                print(f"✅ Parsed entire response as JSON")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parse error: {e}")
                    print(f"Claude response preview: {analysis[:500]}")
                    # Create fallback blocks from text analysis
                    blocks = []
                
                elements = []
                print(f"=== Extracted {len(blocks)} blocks from Claude ===")
                
            except Exception as e:
                import traceback
                print("=== OpenRouter extraction failed ===")
                traceback.print_exc()
                raise Exception(f"OpenRouter extraction failed: {e}")
        else:
            # Mac-safe raster + geometry extraction
            try:
                from ..config import PROFILES, Profile
                from ..extract_utils import pdf_to_pngs, detect_doclayout_boxes_pt, pt_to_px, draw_overlay_and_thumb, crop_rois
                from ..vlm_client import vlm_label_roi

                # Use safe profile by default
                profile: Profile = PROFILES.get("safe_mac_vlm")
                if not profile:
                    raise Exception("Missing safe_mac_vlm profile")
                print(f"=== Using Mac-safe profile: ai_model={profile.ai_model}, crop_mode={profile.crop_mode} ===")

                # Rasterize PDF to PNGs at 300 DPI
                raster_dir = pattern_dir / "raster"
                pngs = pdf_to_pngs(str(pdf_path), str(raster_dir), dpi=300)
                print(f"=== Rasterized {len(pngs)} pages ===")

                # Extract geometry via PyMuPDF (no heavy models)
                all_boxes = []
                # Get page dimensions for thumbnail rendering
                import fitz
                doc = fitz.open(str(pdf_path))
                page = doc[0]
                page_width_pt = page.rect.width
                page_height_pt = page.rect.height
                page_width_px = page_width_pt * 300 / 72
                page_height_px = page_height_pt * 300 / 72
                print(f"=== Page size: {page_width_pt}x{page_height_pt} pt, {page_width_px}x{page_height_px} px ===")
                
                for i, png in enumerate(pngs):
                    boxes_pt = detect_doclayout_boxes_pt(str(pdf_path), i)
                    boxes_px = [pt_to_px(b, dpi=300) for b in boxes_pt]
                    all_boxes.extend(boxes_px)
                    # Save overlay/thumbnail for UI
                    overlay_path = pattern_dir / f"page_{i+1}_overlay.png"
                    thumb_path = pattern_dir / f"page_{i+1}_thumb.png"
                    draw_overlay_and_thumb(png, boxes_px, str(overlay_path), str(thumb_path))
                print(f"=== Detected {len(all_boxes)} geometry boxes ===")

                # Step 2: ROI-only VLM labeling (single-flight)
                blocks = []
                elements = []
                for i, png in enumerate(pngs):
                    boxes_pt = detect_doclayout_boxes_pt(str(pdf_path), i)
                    boxes_px = [pt_to_px(b, dpi=300) for b in boxes_pt]
                    if profile.crop_mode == "boxes_only" and boxes_px:
                        rois = crop_rois(png, boxes_px)
                        for (roi_bgr, (x, y, w, h)) in rois:
                            try:
                                label = await asyncio.wait_for(vlm_label_roi(roi_bgr, model=profile.vlm, timeout_s=profile.timeout_s), timeout=profile.timeout_s + 5)
                            except Exception as e:
                                label = "unknown"
                            blocks.append({"type": label, "x": x, "y": y, "width": w, "height": h, "page": i + 1})
                    else:
                        # No boxes -> no VLM calls
                        pass
                print(f"=== Labeled {len(blocks)} blocks via VLM ===")
            except Exception as e:
                import traceback
                print("=== Mac-safe extraction failed ===")
                traceback.print_exc()
                raise Exception(f"Mac-safe extraction failed: {e}")

        # Step 3: Store in pattern DB for learning
        try:
            print(f"=== Storing pattern: {len(blocks)} blocks, {len(elements)} elements ===")
            style_tokens = {
                "block_types": list({b.get("type") for b in blocks}),
                "element_types": list({e.get("type") for e in elements}),
                "num_blocks": len(blocks),
                "num_elements": len(elements),
            }
            description = ai_service.analyze_pdf_pattern({"blocks": blocks, "elements": elements})
            print(f"=== AI description: {description[:100]}... ===")
            
            # Determine ai_model and profile name
            if use_openrouter:
                ai_model_name = "openrouter"
                profile_name = "openrouter_claude_grok"
            else:
                ai_model_name = profile.ai_model
                profile_name = "safe_mac_vlm"
            
            # Build metadata without None values
            metadata = {
                "source": "upload",
                "ai_model": ai_model_name,
                "profile": profile_name,
                "filename": file.filename,
            }
            # Add page dimensions if available
            if 'page_width_px' in locals() and page_width_px is not None:
                metadata["page_width_px"] = page_width_px
            if 'page_height_px' in locals() and page_height_px is not None:
                metadata["page_height_px"] = page_height_px
            if 'page_width_pt' in locals() and page_width_pt is not None:
                metadata["page_width_pt"] = page_width_pt
            if 'page_height_pt' in locals() and page_height_pt is not None:
                metadata["page_height_pt"] = page_height_pt
            
            stored_pattern_id = pattern_db.add_extracted_pattern(
                pattern_id=pattern_id,
                description=description,
                blocks=blocks,
                elements=elements,
                style_tokens=style_tokens,
                metadata=metadata,
            )
            print(f"=== Pattern stored with ID: {stored_pattern_id} ===")
        except Exception as e:
            import traceback
            print("=== Pattern storage FAILED ===")
            traceback.print_exc()
            raise Exception(f"Pattern storage failed: {e}")

        # Step 4: Generate thumbnail
        try:
            print(f"=== Generating thumbnail for pattern {pattern_id} ===")
            from ..services.thumbnail_generator import generate_thumbnail_for_pattern
            ok = generate_thumbnail_for_pattern(pattern_id)
            print(f"=== Thumbnail generation result: {ok} ===")
        except Exception as e:
            raise Exception(f"Thumbnail generation failed: {e}")

        return {
            "success": True,
            "pattern_id": pattern_id,
            "filename": file.filename,
            "blocks": len(blocks),
            "elements": len(elements),
            "description": description,
            "db_stored": stored_pattern_id is not None,
        }

    except Exception as e:
        import traceback
        print("=== /api/ai/learn EXCEPTION ===")
        traceback.print_exc()
        # Cleanup on failure if pattern_dir exists
        try:
            import shutil
            if 'pattern_dir' in locals():
                shutil.rmtree(pattern_dir, ignore_errors=True)
        except Exception:
            pass
        # Force error as JSON response
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )

@router.get("/patterns", response_model=PatternResponse)
async def get_patterns(query: Optional[str] = None, limit: int = 10):
    """
    Get learned patterns.
    
    Args:
        query: Optional search query
        limit: Maximum number of patterns to return
    """
    try:
        if query:
            patterns = pattern_db.search_patterns(query, n_results=limit)
        else:
            patterns = pattern_db.get_all_patterns(limit=limit)
        
        return PatternResponse(
            success=True,
            patterns=patterns,
            total=len(patterns)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: str):
    """
    Get a specific pattern by ID.
    
    Args:
        pattern_id: Pattern ID
    """
    pattern = pattern_db.get_pattern(pattern_id)
    
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return {
        "success": True,
        "pattern": pattern
    }

@router.delete("/patterns/{pattern_id}")
async def delete_pattern(pattern_id: str):
    """
    Delete a learned pattern.
    
    Args:
        pattern_id: Pattern ID
    """
    success = pattern_db.delete_pattern(pattern_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return {
        "success": True,
        "message": "Pattern deleted successfully"
    }

@router.get("/stats")
def get_stats():
    """Get AI service statistics"""
    db_stats = pattern_db.get_stats()
    
    return {
        "success": True,
        "model": ai_service.model,
        "database": db_stats
    }

# === Mac-safe extraction + ROI labeling routes ===

class ExtractResponse(BaseModel):
    pages: int
    overlays: list[str]
    thumbs: list[str]
    boxes_pt: list[list[float]]
    boxes_px: list[list[float]]

class LabelRequest(BaseModel):
    profile: Optional[str] = "safe_mac_vlm"
    vlm: Optional[str] = None
    pdf_path: Optional[str] = None
    pattern_id: Optional[str] = None

class LabeledBox(BaseModel):
    page: int
    bbox_px: list[float]
    label: str

class LabelResponse(BaseModel):
    items: list[LabeledBox]

@router.post("/patterns/{pattern_id}/extract", response_model=ExtractResponse)
async def extract(
    pattern_id: str,
    ai_detect: bool = True,
    ai_model: str = Query("doclayout"),
    imgsz: int = Query(1024), tile_size: int = Query(512), tile_overlap: int = Query(64),
    profile: Optional[str] = None,
    pdf_path: Optional[str] = None,
):
    from ..config import PROFILES, Profile
    from ..extract_utils import pdf_to_pngs, detect_doclayout_boxes_pt, pt_to_px, draw_overlay_and_thumb

    # Apply profile if present
    if profile:
        pf: Profile = PROFILES.get(profile)
        if not pf: raise HTTPException(400, f"Unknown profile: {profile}")
        ai_model = pf.ai_model
        imgsz, tile_size, tile_overlap = pf.imgsz, pf.tile_size, pf.tile_overlap

    if not pdf_path:
        pdf_path = str(STORAGE_DIR / pattern_id / "original.pdf")
    if not Path(pdf_path).exists():
        raise HTTPException(404, f"PDF not found: {pdf_path}")

    # 1) Rasterize
    raster_dir = STORAGE_DIR / pattern_id / "raster"
    pngs = pdf_to_pngs(pdf_path, str(raster_dir), dpi=300)

    overlays, thumbs = [], []
    all_boxes_pt, all_boxes_px = [], []

    for i, png in enumerate(pngs):
        boxes_pt = detect_doclayout_boxes_pt(pdf_path, i) if ai_detect and ai_model in ("doclayout","both") else []
        boxes_px = [pt_to_px(b, dpi=300) for b in boxes_pt]

        overlay_path = str(STORAGE_DIR / pattern_id / f"page_{i+1}_overlay.png")
        thumb_path = str(STORAGE_DIR / pattern_id / f"page_{i+1}_thumb.png")
        draw_overlay_and_thumb(png, boxes_px, overlay_path, thumb_path)

        overlays.append(overlay_path); thumbs.append(thumb_path)
        all_boxes_pt.extend([list(b) for b in boxes_pt])
        all_boxes_px.extend([list(b) for b in boxes_px])

    return ExtractResponse(
        pages=len(pngs),
        overlays=overlays, thumbs=thumbs,
        boxes_pt=all_boxes_pt, boxes_px=all_boxes_px
    )

@router.post("/patterns/{pattern_id}/label", response_model=LabelResponse)
async def label(pattern_id: str, body: LabelRequest):
    import asyncio
    from ..config import PROFILES, Profile
    from ..extract_utils import pdf_to_pngs, detect_doclayout_boxes_pt, pt_to_px, crop_rois
    from ..vlm_client import vlm_label_roi

    pf = PROFILES.get(body.profile or "safe_mac_vlm")
    if not pf: raise HTTPException(400, "Bad profile")
    model = body.vlm or pf.vlm

    pdf_path = body.pdf_path or str(STORAGE_DIR / pattern_id / "original.pdf")
    if not Path(pdf_path).exists():
        raise HTTPException(404, f"PDF not found: {pdf_path}")

    # Reuse raster outputs
    raster_dir = STORAGE_DIR / pattern_id / "raster"
    pngs = sorted(raster_dir.glob("*.png"))
    if not pngs:
        # silently rasterize if not present
        pngs = pdf_to_pngs(pdf_path, str(raster_dir), dpi=300)
        pngs = [Path(p) for p in pngs]

    results: list[LabeledBox] = []

    for i, png in enumerate(pngs):
        boxes_pt = detect_doclayout_boxes_pt(pdf_path, i)
        boxes_px = [pt_to_px(b, dpi=300) for b in boxes_pt]

        if pf.crop_mode == "boxes_only" and boxes_px:
            rois = crop_rois(str(png), boxes_px)
            for (roi_bgr, (x,y,w,h)) in rois:
                try:
                    label = await asyncio.wait_for(vlm_label_roi(roi_bgr, model=model, timeout_s=pf.timeout_s), timeout=pf.timeout_s+5)
                except Exception as e:
                    label = "unknown"
                results.append(LabeledBox(page=i+1, bbox_px=[float(x),float(y),float(w),float(h)], label=label))
        else:
            pass

    return LabelResponse(items=results)
