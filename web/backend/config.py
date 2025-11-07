from pydantic import BaseModel
from typing import Optional, Literal, Dict

AIModel = Literal["doclayout", "ollama_vl", "both"]

class Profile(BaseModel):
    ai_model: AIModel
    imgsz: int = 1024
    tile_size: int = 512
    tile_overlap: int = 64
    vlm: str = "llava:7b"
    concurrency: int = 1
    crop_mode: Literal["none", "boxes_only"] = "none"
    timeout_s: int = 60

SAFE_MAC = Profile(ai_model="doclayout", imgsz=1024, tile_size=512, tile_overlap=64, concurrency=1)
SAFE_MAC_VLM = Profile(ai_model="ollama_vl", vlm="llava:13b", crop_mode="boxes_only", concurrency=1, timeout_s=60)

PROFILES: Dict[str, Profile] = {
    "safe_mac": SAFE_MAC,
    "safe_mac_vlm": SAFE_MAC_VLM,
}
