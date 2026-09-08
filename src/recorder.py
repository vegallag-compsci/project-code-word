from datetime import datetime
from pathlib import Path
from typing import List

import cv2
import numpy as np

from config.settings import FRAME_HEIGHT, FRAME_WIDTH, RECORD_DIR, TARGET_FPS


def save_clip(frames: List[np.ndarray]) -> str:
    """Write a list of BGR frames to an mp4 file; returns the file path."""
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = str(RECORD_DIR / f"codeword_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, TARGET_FPS, (FRAME_WIDTH, FRAME_HEIGHT))

    if not writer.isOpened():
        raise RuntimeError(f"VideoWriter could not open: {filepath}")

    try:
        for frame in frames:
            if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            writer.write(frame)
    finally:
        writer.release()

    return filepath
