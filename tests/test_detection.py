from types import SimpleNamespace
import pytest
from src.detection import is_open_palm


def _lm(coords: list[tuple[float, float]]) -> list:
    """Build a 21-landmark list from (x, y) pairs (z defaults to 0)."""
    return [SimpleNamespace(x=x, y=y, z=0.0) for x, y in coords]


def _palm_landmarks(handedness: str = "Right"):
    """
    Minimal landmark set for an open palm:
      - all four finger tips above their PIPs
      - thumb tip to the left of index MCP (right hand)
    """
    coords = [(0.5, 0.9)] * 21  # wrist at index 0
    # index: mcp=5, pip=6, tip=8
    coords[5]  = (0.55, 0.7)
    coords[6]  = (0.55, 0.5)
    coords[8]  = (0.55, 0.2)   # tip above pip ✓
    # middle: mcp=9, pip=10, tip=12
    coords[9]  = (0.5, 0.7)
    coords[10] = (0.5, 0.5)
    coords[12] = (0.5, 0.2)    # tip above pip ✓
    # ring: mcp=13, pip=14, tip=16
    coords[13] = (0.45, 0.7)
    coords[14] = (0.45, 0.5)
    coords[16] = (0.45, 0.2)   # tip above pip ✓
    # pinky: mcp=17, pip=18, tip=20
    coords[17] = (0.4, 0.7)
    coords[18] = (0.4, 0.5)
    coords[20] = (0.4, 0.2)    # tip above pip ✓
    # thumb: tip=4, index_mcp=5
    coords[4]  = (0.65, 0.6)   # thumb tip to the RIGHT of index MCP x
    if handedness == "Right":
        coords[4] = (0.40, 0.6)  # thumb tip to the LEFT of index MCP ✓
    return _lm(coords)


def test_open_palm_right_hand():
    assert is_open_palm(_palm_landmarks("Right"), "Right") is True


def test_open_palm_left_hand():
    lm = _palm_landmarks("Left")
    lm[4] = SimpleNamespace(x=0.70, y=0.6, z=0.0)  # thumb right of index MCP
    assert is_open_palm(lm, "Left") is True


def test_closed_fist_not_detected():
    coords = [(0.5, 0.9)] * 21
    # fingers curled: tip y > pip y
    for tip, pip in [(8,6), (12,10), (16,14), (20,18)]:
        coords[pip] = (0.5, 0.4)
        coords[tip] = (0.5, 0.6)   # tip BELOW pip (curled)
    assert is_open_palm(_lm(coords), "Right") is False
