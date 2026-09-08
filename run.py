"""
code_word — entry point.

Starts the FastAPI/uvicorn server, opens the PyWebView window, and wires
the camera + gesture detection to the WebSocket broadcast.
"""
import logging
import threading
import time
from pathlib import Path

import uvicorn
import webview

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

import src.server as server_module
from src.camera import CameraSource
from src.recorder import save_clip

logger = logging.getLogger(__name__)


def on_gesture_trigger() -> None:
    """
    Called from a daemon thread when the open-palm gesture is confirmed.
    Snapshots the buffer, saves to disk, and queues UI events.
    """
    if server_module.camera_source is None:
        return

    frames = server_module.camera_source.buffer_snapshot()
    if not frames:
        return

    server_module.event_queue.put({"type": "gesture_detected"})

    try:
        filepath = save_clip(frames)
        filename = Path(filepath).name
        server_module.event_queue.put({"type": "saved", "filename": filename, "path": filepath})
        logger.info("Saved clip: %s", filepath)
    except Exception as exc:
        server_module.event_queue.put({"type": "error", "message": str(exc)})
        logger.error("Save failed: %s", exc)


def _start_server() -> None:
    uvicorn.run(
        server_module.app,
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )


if __name__ == "__main__":
    # 1. Start camera + gesture detector
    cam = CameraSource(on_trigger=on_gesture_trigger)
    server_module.camera_source = cam
    cam.start()

    # 2. Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # 3. Wait for server to be ready
    time.sleep(1.5)

    # 4. Open the native desktop window (Edge WebView2 on Windows 11)
    window = webview.create_window(
        title="code_word",
        url="http://127.0.0.1:8765",
        width=960,
        height=680,
        min_size=(640, 480),
        background_color="#F8F9FA",
        frameless=False,
    )
    webview.start()

    # 5. Clean up after window closes
    cam.stop()
