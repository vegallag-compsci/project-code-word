import numpy as np
import pytest
from src.buffer import RollingBuffer


def make_frame(val: int) -> np.ndarray:
    return np.full((360, 640, 3), val, dtype=np.uint8)


def test_buffer_maxlen_evicts_oldest():
    buf = RollingBuffer(maxlen=3)
    for i in range(5):
        buf.append(make_frame(i))
    snap = buf.snapshot()
    assert len(snap) == 3
    assert snap[0][0, 0, 0] == 2  # oldest kept is frame 2


def test_snapshot_is_copy():
    buf = RollingBuffer(maxlen=5)
    buf.append(make_frame(0))
    snap = buf.snapshot()
    snap.clear()
    assert len(buf) == 1


def test_empty_buffer_snapshot():
    buf = RollingBuffer(maxlen=10)
    assert buf.snapshot() == []
    assert len(buf) == 0
