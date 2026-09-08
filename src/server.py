import asyncio
import json
import logging
import queue as stdlib_queue
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Set

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import TARGET_FPS

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Populated by run.py before server starts
camera_source = None

# Thread-safe queue for events from detection/recorder threads
event_queue: stdlib_queue.Queue = stdlib_queue.Queue()

_clients: Set[WebSocket] = set()
_clients_lock: asyncio.Lock = asyncio.Lock()  # safe to create before event loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_broadcast_loop())
    yield


app = FastAPI(lifespan=lifespan)


async def _broadcast_loop() -> None:
    """Push JPEG frames and queued events to every connected WebSocket client."""
    frame_interval = 1.0 / TARGET_FPS
    while True:
        loop = asyncio.get_running_loop()
        tick_start = loop.time()

        # --- video frame ---
        if camera_source is not None:
            frame = camera_source.latest_frame()
            if frame is not None:
                _, jpeg = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
                )
                await _send_to_all_bytes(jpeg.tobytes())

        # --- queued events ---
        while not event_queue.empty():
            try:
                event = event_queue.get_nowait()
                await _send_to_all_text(json.dumps(event))
            except stdlib_queue.Empty:
                break

        elapsed = asyncio.get_running_loop().time() - tick_start
        await asyncio.sleep(max(0.0, frame_interval - elapsed))


async def _send_to_all_bytes(data: bytes) -> None:
    async with _clients_lock:
        snapshot = set(_clients)

    dead: Set[WebSocket] = set()
    for ws in snapshot:
        try:
            await ws.send_bytes(data)
        except (WebSocketDisconnect, ConnectionResetError):
            dead.add(ws)
        except Exception as exc:
            logger.warning("Unexpected WebSocket send error: %s", exc)
            dead.add(ws)

    if dead:
        async with _clients_lock:
            _clients.difference_update(dead)


async def _send_to_all_text(text: str) -> None:
    async with _clients_lock:
        snapshot = set(_clients)

    dead: Set[WebSocket] = set()
    for ws in snapshot:
        try:
            await ws.send_text(text)
        except (WebSocketDisconnect, ConnectionResetError):
            dead.add(ws)
        except Exception as exc:
            logger.warning("Unexpected WebSocket send error: %s", exc)
            dead.add(ws)

    if dead:
        async with _clients_lock:
            _clients.difference_update(dead)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    async with _clients_lock:
        _clients.add(ws)
    try:
        while True:
            await asyncio.sleep(1)  # keep alive; frames are pushed by broadcast loop
    except WebSocketDisconnect:
        pass
    finally:
        async with _clients_lock:
            _clients.discard(ws)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve built React assets — must come after API routes
if FRONTEND_DIST.exists():
    _assets = FRONTEND_DIST / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(str(FRONTEND_DIST / "index.html"))
