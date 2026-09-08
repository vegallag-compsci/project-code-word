import threading
import time
from typing import Callable, List

import mediapipe as mp
from mediapipe.tasks.python.components.containers import NormalizedLandmark

from config.settings import (
    CONSECUTIVE_FRAMES_REQUIRED,
    COOLDOWN_SECONDS,
    MODEL_PATH,
)

HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult


def is_open_palm(
    hand_landmarks: List[NormalizedLandmark], handedness: str
) -> bool:
    """
    Return True when 5 fingers are extended and palm faces the camera.

    Landmark indices used (MediaPipe convention):
      Index: tip=8, pip=6, mcp=5
      Middle: tip=12, pip=10, mcp=9
      Ring: tip=16, pip=14, mcp=13
      Pinky: tip=20, pip=18, mcp=17
      Thumb: tip=4, mcp=2, index_mcp=5
    """
    lm = hand_landmarks

    # Four fingers: tip must be above pip (smaller y = higher on screen)
    index_up  = lm[8].y  < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_up   = lm[16].y < lm[14].y
    pinky_up  = lm[20].y < lm[18].y

    # Thumb: extended outward from palm, direction depends on handedness
    if handedness == "Right":
        thumb_out = lm[4].x < lm[5].x  # thumb tip left of index MCP
    else:
        thumb_out = lm[4].x > lm[5].x  # thumb tip right of index MCP

    return index_up and middle_up and ring_up and pinky_up and thumb_out


class GestureDetector:
    """
    Wraps MediaPipe HandLandmarker in LIVE_STREAM mode.
    Calls on_trigger() after CONSECUTIVE_FRAMES_REQUIRED consecutive
    open-palm detections, then enforces a COOLDOWN_SECONDS gap.
    """

    def __init__(self, on_trigger: Callable[[], None]) -> None:
        self._on_trigger = on_trigger
        self._consecutive = 0
        self._last_trigger: float = 0.0
        self._lock = threading.Lock()

        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._result_callback,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    def detect_async(self, mp_image: mp.Image, timestamp_ms: int) -> None:
        self._landmarker.detect_async(mp_image, timestamp_ms)

    def close(self) -> None:
        self._landmarker.close()

    def _result_callback(
        self,
        result: HandLandmarkerResult,
        output_img: mp.Image,
        timestamp_ms: int,
    ) -> None:
        detected = False
        if result.hand_landmarks and result.handedness:
            for hand_lm, hand_side_list in zip(
                result.hand_landmarks, result.handedness
            ):
                side = hand_side_list[0].category_name  # "Left" or "Right"
                if is_open_palm(hand_lm, side):
                    detected = True
                    break

        with self._lock:
            if detected:
                self._consecutive += 1
                if self._consecutive >= CONSECUTIVE_FRAMES_REQUIRED:
                    now = time.monotonic()
                    if now - self._last_trigger >= COOLDOWN_SECONDS:
                        self._last_trigger = now
                        self._consecutive = 0
                        threading.Thread(
                            target=self._on_trigger, daemon=True
                        ).start()
            else:
                self._consecutive = 0
