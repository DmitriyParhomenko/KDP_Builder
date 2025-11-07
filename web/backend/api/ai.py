"""
AI API endpoints

AI-powered layout suggestions and pattern learning.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

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
    ai_detect: bool = Query(True, description="Run AI vision detection"),
    ai_model: str = Query("both", description="AI model: doclayout, ollama_vl, both"),
    imgsz: int = Query(1536, description="YOLO inference size"),
    tile_size: int = Query(640, description="SAHI tile size"),
    tile_overlap: int = Query(160, description="SAHI tile overlap"),
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
        analysis_dir = pattern_dir / "analysis"
        extracted_dir = pattern_dir / "extracted"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded PDF as original.pdf (expected by analyze_pdf)
        pdf_path = pattern_dir / "original.pdf"
        content = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(content)

        # Step 1: Analyze PDF (vector extraction + PNG rendering)
        try:
            from ..services.pdf_parser import analyze_pdf
            result = analyze_pdf(pattern_dir, ocr=False)
            if not result.get("success"):
                raise Exception(result.get("error", "PDF analysis returned failure"))
        except Exception as e:
            raise Exception(f"PDF analysis failed: {e}")

        # Step 2: Extract blocks with AI
        try:
            from ..services.block_extractor import extract_blocks
            extract_result = extract_blocks(
                pattern_dir,
                ai_detect=ai_detect,
                ai_model=ai_model,
                imgsz=imgsz,
                tile_size=tile_size,
                tile_overlap=tile_overlap,
            )
        except Exception as e:
            raise Exception(f"Block extraction failed: {e}")

        if not extract_result.get("success"):
            raise Exception(extract_result.get("error", "Extraction failed"))

        # Step 3: Store in pattern DB for learning
        try:
            blocks = extract_result.get("blocks", [])
            elements = extract_result.get("elements", [])
            style_tokens = {
                "block_types": list({b.get("type") for b in blocks}),
                "element_types": list({e.get("type") for e in elements}),
                "num_blocks": len(blocks),
                "num_elements": len(elements),
            }
            description = ai_service.analyze_pdf_pattern({"blocks": blocks, "elements": elements})
            stored_pattern_id = pattern_db.add_pattern(
                pattern_id=pattern_id,
                description=description,
                metadata={
                    "source": "upload",
                    "ai_model": ai_model,
                    "filename": file.filename,
                    "blocks": blocks,
                    "elements": elements,
                    "style_tokens": style_tokens,
                },
            )
        except Exception as e:
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
async def get_ai_stats():
    """Get AI service statistics"""
    db_stats = pattern_db.get_stats()
    
    return {
        "success": True,
        "model": ai_service.model,
        "database": db_stats
    }
