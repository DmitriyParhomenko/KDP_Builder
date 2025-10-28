from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
from pathlib import Path
from uuid import uuid4
import shutil
import json
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
def analyze_pattern(pattern_id: str) -> Dict[str, Any]:
    pattern_dir = STORAGE_DIR / pattern_id
    if not pattern_dir.exists():
        raise HTTPException(status_code=404, detail="pattern not found")
    try:
        from web.backend.services.pdf_parser import analyze_pdf  # lazy import
    except Exception as e:
        return {"success": False, "error": f"parser not available: {e}"}
    result = analyze_pdf(pattern_dir)
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
def extract_blocks_api(pattern_id: str) -> Dict[str, Any]:
    pattern_dir = STORAGE_DIR / pattern_id
    if not pattern_dir.exists():
        raise HTTPException(status_code=404, detail="pattern not found")
    try:
        from web.backend.services.block_extractor import extract_blocks  # lazy import
    except Exception as e:
        return {"success": False, "error": f"block extractor not available: {e}"}
    return extract_blocks(pattern_dir)


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read extracted data: {e}")
    return {"success": True, "blocks": blocks, "elements": elements}
