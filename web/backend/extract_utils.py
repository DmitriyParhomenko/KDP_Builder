import fitz, cv2, numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

def pdf_to_pngs(pdf_path: str, out_dir: str, dpi: int = 300) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    outs = []
    for i, p in enumerate(doc, 1):
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = p.get_pixmap(matrix=mat, alpha=False)
        out = Path(out_dir) / f"{Path(pdf_path).stem}_p{i:03d}.png"
        pix.save(out.as_posix()); outs.append(out.as_posix())
    return outs

def draw_overlay_and_thumb(png_path: str, boxes_px: List[Tuple[float,float,float,float]],
                           overlay_path: str, thumb_path: str) -> None:
    img = cv2.imread(png_path, cv2.IMREAD_COLOR)
    overlay = img.copy()
    for (x,y,w,h) in boxes_px:
        cv2.rectangle(overlay, (int(x),int(y)), (int(x+w),int(y+h)), (0,0,255), 1)
    if not boxes_px:
        cv2.rectangle(overlay,(10,10),(420,48),(0,0,0),-1)
        cv2.putText(overlay,"No detections — open Fix Mode",(18,38),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),1,cv2.LINE_AA)
    blended = cv2.addWeighted(overlay, 0.6, img, 0.4, 0)
    Path(overlay_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(overlay_path, blended)
    # thumb
    h,w = img.shape[:2]; tw = 512; th = int(h*(tw/w))
    thumb = cv2.resize(blended,(tw,th), interpolation=cv2.INTER_AREA)
    cv2.imwrite(thumb_path, thumb)

def detect_doclayout_boxes_pt(pdf_path: str, page_index: int) -> list[tuple[float,float,float,float]]:
    # Hybrid detection: vector geometry + text blocks + images
    doc = fitz.open(pdf_path); page = doc[page_index]
    boxes = []
    
    def bbox(pts):
        xs=[p.x for p in pts]; ys=[p.y for p in pts]
        x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys)
        return (x0,y0,(x1-x0),(y1-y0))
    
    # 1. Vector drawings (lines, rectangles)
    for d in page.get_drawings():
        for it in d.get("items", []):
            if it[0]=="l":
                b=bbox([it[1],it[2]])
                if max(b[2],b[3])>=0.2: boxes.append(b)
            elif it[0]=="re":  # rectangles
                rect = it[1]
                boxes.append((rect.x0, rect.y0, rect.width, rect.height))
    
    # 2. Text blocks (captures text fields, labels, checkboxes with text)
    for block in page.get_text("dict")["blocks"]:
        if block["type"] == 0:  # text block
            x0, y0, x1, y1 = block["bbox"]
            w, h = x1 - x0, y1 - y0
            if w > 5 and h > 5:  # filter tiny text
                boxes.append((x0, y0, w, h))
    
    # 3. Images (icons, checkboxes, decorative elements)
    for img in page.get_images():
        try:
            xref = img[0]
            bbox_list = page.get_image_bbox(xref)
            if bbox_list:
                x0, y0, x1, y1 = bbox_list
                w, h = x1 - x0, y1 - y0
                if w > 3 and h > 3:
                    boxes.append((x0, y0, w, h))
        except:
            pass
    
    return boxes

def pt_to_px(b_pt: tuple[float,float,float,float], dpi: int=300) -> tuple[float,float,float,float]:
    s = dpi/72
    return (b_pt[0]*s, b_pt[1]*s, b_pt[2]*s, b_pt[3]*s)

def crop_rois(image_path: str, boxes_px: list[tuple[float,float,float,float]]) -> list[tuple[np.ndarray, tuple]]:
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    rois = []
    h,w = img.shape[:2]
    for (x,y,ww,hh) in boxes_px:
        x0,y0 = max(0,int(x)), max(0,int(y))
        x1,y1 = min(w, int(x+ww)), min(h, int(y+hh))
        if x1-x0>5 and y1-y0>5:
            rois.append((img[y0:y1, x0:x1].copy(), (x0,y0, x1-x0,y1-y0)))
    return rois
