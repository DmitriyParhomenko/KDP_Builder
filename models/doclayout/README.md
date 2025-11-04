# DocLayNet model weights

Place your DocLayNet YOLOv8 weights file here and name it `yolov8_doclaynet.pt`.

Example:
- Download or copy your `yolov8_doclaynet.pt` into this folder.
- Restart the API server.
- The system will automatically load the local weights via `DOCLAYOUT_WEIGHTS` set in the startup script or environment.

If you use a different filename or path, set the environment variable before starting the server:
```bash
export DOCLAYOUT_WEIGHTS=/absolute/path/to/your_weights.pt
uvicorn web.backend.main:app --reload --port 8000
```
