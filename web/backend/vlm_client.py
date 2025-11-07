import asyncio, httpx, base64
from typing import List

_vlm_lock = asyncio.Lock()

async def vlm_label_roi(img_bgr, model: str, timeout_s: int = 45) -> str:
    # Encode ROI as base64 JPEG
    import cv2
    _, buf = cv2.imencode(".jpg", img_bgr)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    prompt = """Identify this planner/journal element. Choose ONE label from:
- habit_tracker (grid with days/habits)
- calendar (monthly/weekly calendar)
- notes (lined/blank writing area)
- title (header/title text)
- checkbox_list (list with checkboxes)
- goal_tracker (goal setting area)
- water_tracker (water intake tracking)
- mood_tracker (mood/emotion tracking)
- schedule (time-based schedule)
- gratitude (gratitude journal section)
- table (data table/grid)
- decorative (border/decoration)
- text_field (single text input)
- other (if none match)

Return ONLY the label, nothing else."""
    payload = {
        "model": model,  # e.g., "llava:7b"
        "prompt": prompt,
        "images": [f"data:image/jpeg;base64,{b64}"],
        "stream": False
    }

    async with _vlm_lock:  # single VLM inference at a time
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post("http://localhost:11434/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip()
