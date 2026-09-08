from collections import deque
from threading import Lock
from typing import List

import numpy as np


class RollingBuffer:
    """Thread-safe fixed-length rolling frame buffer."""

    def __init__(self, maxlen: int) -> None:
        self._buf: deque[np.ndarray] = deque(maxlen=maxlen)
        self._lock = Lock()

    def append(self, frame: np.ndarray) -> None:
        with self._lock:
            self._buf.append(frame)

    def snapshot(self) -> List[np.ndarray]:
        """Return a copy of current frames (safe to hand off to another thread)."""
        with self._lock:
            return list(self._buf)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
