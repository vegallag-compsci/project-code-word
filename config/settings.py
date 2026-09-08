from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

MODEL_PATH = str(BASE_DIR / "models" / "hand_landmarker.task")

# Camera
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
TARGET_FPS = 15

# Rolling buffer: 20 seconds @ 15fps = 300 frames (~200MB at 640x360)
BUFFER_SECONDS = 20

# Gesture detection — tune these empirically
CONSECUTIVE_FRAMES_REQUIRED = 12  # ~0.8s at 15fps before trigger fires
COOLDOWN_SECONDS = 10             # minimum gap between saves

# Recording output directory
RECORD_DIR = Path.home() / "Videos" / "code_word"

# Server
HOST = "127.0.0.1"
PORT = 8765
