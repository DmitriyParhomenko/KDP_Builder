from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import json
import uuid
import shutil
from typing import Dict, Any, Optional, List
from uuid import uuid4
import os

router = APIRouter()

# Config approved by user
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB per file
MAX_FILES_PER_UPLOAD = 20
STORAGE_DIR = Path(__file__).resolve().parents[3] / "data" / "patterns"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _is_pdf(file: UploadFile) -> bool:
    name_ok = file.filename.lower().endswith(".pdf") if file.filename else False
    type_ok = (file.content_type or "").lower() in {"application/pdf", "application/x-pdf", "application/octet-stream"}
    return name_ok or type_ok


@router.post("/upload")
async def upload_patterns(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"Too many files. Max {MAX_FILES_PER_UPLOAD}")

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for file in files:
        if not _is_pdf(file):
            errors.append(f"{file.filename}: not a PDF")
            continue

        pattern_id = str(uuid4())
        out_dir = STORAGE_DIR / pattern_id
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / "original.pdf"
        meta_path = out_dir / "metadata.json"

        # Stream to disk and enforce 50MB size cap
        size = 0
        try:
            with pdf_path.open("wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_FILE_SIZE_BYTES:
                        f.close()
                        pdf_path.unlink(missing_ok=True)
                        errors.append(f"{file.filename}: exceeds 50MB limit")
                        # Drain remaining to release the request body
                        while await file.read(1024 * 1024):
                            pass
                        break
                    f.write(chunk)
        finally:
            await file.close()

        if not pdf_path.exists():
            # file rejected due to size or other error already recorded
            continue

        # Write metadata
        metadata = {
            "pattern_id": pattern_id,
            "original_filename": file.filename,
            "size_bytes": size,
            "path": str(pdf_path),
        }
        with meta_path.open("w", encoding="utf-8") as mf:
            json.dump(metadata, mf, ensure_ascii=False, indent=2)

        results.append({"pattern_id": pattern_id, "filename": file.filename, "size_bytes": size})

    return {"success": len(results) > 0, "uploaded": results, "errors": errors}


@router.get("")
def list_patterns() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for child in STORAGE_DIR.iterdir():
        if not child.is_dir():
            continue
        meta = child / "metadata.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                items.append({
                    "pattern_id": data.get("pattern_id", child.name),
                    "original_filename": data.get("original_filename"),
                    "size_bytes": data.get("size_bytes"),
                })
            except Exception:
                items.append({"pattern_id": child.name})
        else:
            items.append({"pattern_id": child.name})
    return {"patterns": items}


@router.post("/{pattern_id}/analyze")
def analyze_pattern(pattern_id: str, ocr: bool = Query(False)) -> Dict[str, Any]:
    pattern_dir = STORAGE_DIR / pattern_id
    if not pattern_dir.exists():
        raise HTTPException(status_code=404, detail="pattern not found")
    try:
        from web.backend.services.pdf_parser import analyze_pdf  # lazy import
    except Exception as e:
        return {"success": False, "error": f"parser not available: {e}"}
    result = analyze_pdf(pattern_dir, ocr=ocr)
    return result


@router.get("/{pattern_id}/analysis")
def get_analysis(pattern_id: str) -> Dict[str, Any]:
    pattern_dir = STORAGE_DIR / pattern_id / "analysis"
    index = pattern_dir / "index.json"
    if not index.exists():
        raise HTTPException(status_code=404, detail="analysis not found")
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read analysis: {e}")
    return {"success": True, "index": data}


@router.post("/{pattern_id}/extract")
async def extract_pattern_blocks(
    pattern_id: str,
    ai_detect: bool = Query(False, description="Enable AI vision detection"),
    ai_model: str = Query("doclayout", description="AI model: doclayout, ollama_vl, both"),
    imgsz: int = Query(1280, description="Inference image size for YOLO models"),
    tile_size: int = Query(640, description="SAHI tile size for slicing inference"),
    tile_overlap: int = Query(100, description="SAHI tile overlap"),
) -> Dict[str, Any]:
    """Extract blocks from analyzed pages; optionally run AI vision detection."""
    pattern_dir = STORAGE_DIR / pattern_id
    if not pattern_dir.exists():
        raise HTTPException(status_code=404, detail="pattern not found")
    try:
        from web.backend.services.block_extractor import extract_blocks as _extract
        from web.backend.services.ai_service import ai_service
        # Extract
        result = _extract(pattern_dir, ai_detect=ai_detect, ai_model=ai_model, imgsz=imgsz, tile_size=tile_size, tile_overlap=tile_overlap)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "extraction failed"))
        # Optional: store blocks+elements in pattern DB for RAG
        try:
            blocks = result.get("blocks", [])
            elements = result.get("elements", [])
            # Simple style token summary
            style_tokens = {
                "block_types": list({b.get("type") for b in blocks}),
                "element_types": list({e.get("type") for e in elements}),
                "num_blocks": len(blocks),
                "num_elements": len(elements)
            }
            # Generate description via AI
            description = ai_service.analyze_pdf_pattern({"blocks": blocks, "elements": elements})
            # Persist to pattern DB (extracted variant)
            from web.backend.services.pattern_db import pattern_db
            pattern_db.add_extracted_pattern(
                pattern_id=pattern_id,
                description=description,
                metadata={"source": "extracted", "pattern_id": pattern_id, "ai_detect": ai_detect},
                blocks=blocks,
                elements=elements,
                style_tokens=style_tokens
            )
        except Exception as e:
            # Non-blocking: extraction still succeeded
            print(f"⚠️  Failed to persist extracted pattern to DB: {e}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pattern_id}/extracted")
def get_extracted(pattern_id: str) -> Dict[str, Any]:
    base = STORAGE_DIR / pattern_id / "extracted"
    blocks_path = base / "blocks.json"
    elements_path = base / "elements.json"
    if not blocks_path.exists() or not elements_path.exists():
        raise HTTPException(status_code=404, detail="extracted data not found")
    try:
        blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
        elements = json.loads(elements_path.read_text(encoding="utf-8"))
        return {"success": True, "blocks": blocks, "elements": elements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_patterns(limit: int = 50) -> Dict[str, Any]:
    """List all patterns with extracted summaries"""
    try:
        from web.backend.services.pattern_db import pattern_db
        patterns = pattern_db.list_patterns_with_extracted(limit=limit)
        return {"success": True, "patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pattern_id}")
def get_pattern_details(pattern_id: str) -> Dict[str, Any]:
    """Get a pattern with its extracted blocks, elements, and style tokens"""
    try:
        from web.backend.services.pattern_db import pattern_db
        pattern = pattern_db.get_pattern_with_extracted(pattern_id)
        if pattern is None:
            raise HTTPException(status_code=404, detail="pattern not found")
        return {"success": True, "pattern": pattern}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{pattern_id}")
def delete_pattern(pattern_id: str) -> Dict[str, Any]:
    """Delete a pattern and its extracted files"""
    try:
        from web.backend.services.pattern_db import pattern_db
        success = pattern_db.delete_pattern(pattern_id)
        if not success:
            raise HTTPException(status_code=404, detail="pattern not found")
        return {"success": True, "message": "Pattern deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_patterns(q: str, limit: int = 10) -> Dict[str, Any]:
    """Search patterns by text query"""
    try:
        from web.backend.services.pattern_db import pattern_db
        results = pattern_db.search_patterns(q, n_results=limit)
        return {"success": True, "patterns": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pattern_id}/thumbnail")
def get_thumbnail(pattern_id: str) -> FileResponse:
    """Serve pattern thumbnail PNG"""
    thumb_path = STORAGE_DIR / pattern_id / "thumbnail.png"
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="thumbnail not found")
    return FileResponse(thumb_path, media_type="image/png")


@router.post("/thumbnails/generate")
def generate_thumbnails() -> Dict[str, Any]:
    """Generate thumbnails for all patterns with extracted data"""
    try:
        from web.backend.services.thumbnail_generator import generate_all_thumbnails
        count = generate_all_thumbnails()
        return {"success": True, "generated": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
