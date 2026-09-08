import logging
import threading
import time
from typing import Callable, Optional

import cv2
import mediapipe as mp
import numpy as np

from config.settings import (
    BUFFER_SECONDS,
    CAMERA_INDEX,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    TARGET_FPS,
)
from src.buffer import RollingBuffer
from src.detection import GestureDetector

logger = logging.getLogger(__name__)


class CameraSource:
    """
    Capture thread: reads frames from the webcam, maintains a rolling
    20-second buffer, feeds MediaPipe for gesture detection, and exposes
    the latest frame for the WebSocket streamer.
    """

    def __init__(self, on_trigger: Callable[[], None]) -> None:
        maxlen = TARGET_FPS * BUFFER_SECONDS
        self._buffer = RollingBuffer(maxlen=maxlen)
        self._detector = GestureDetector(on_trigger=on_trigger)
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._timestamp_ms: int = 0
        self._frame_ms = int(1000 / TARGET_FPS)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._detector.close()
        if self._thread:
            self._thread.join(timeout=3.0)

    def latest_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._latest_frame

    def buffer_snapshot(self):
        return self._buffer.snapshot()

    def _loop(self) -> None:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            logger.error("Could not open camera index %d", CAMERA_INDEX)
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        frame_interval = 1.0 / TARGET_FPS
        last_tick = time.monotonic()
        last_ts_ms: int = 0

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                # Rate-gate to TARGET_FPS
                now = time.monotonic()
                gap = frame_interval - (now - last_tick)
                if gap > 0:
                    time.sleep(gap)
                last_tick = time.monotonic()

                # Mirror horizontally so the feed feels natural
                frame = cv2.flip(frame, 1)

                # Store in rolling buffer and expose for streaming
                self._buffer.append(frame)
                with self._frame_lock:
                    self._latest_frame = frame

                # Use wall-clock ms for MediaPipe timestamps (must be strictly increasing)
                ts_ms = max(last_ts_ms + 1, int(time.monotonic() * 1000))
                last_ts_ms = ts_ms
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                self._detector.detect_async(mp_image, ts_ms)
        finally:
            cap.release()
