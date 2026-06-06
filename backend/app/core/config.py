import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONES_PATH = os.path.join(BASE_DIR, "data", "zones.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
ANNOTATED_DIR = os.path.join(STATIC_DIR, "annotated")
CAMERA_VIDEO_ROOT = os.getenv("CAMERA_VIDEO_ROOT", "test_assets/cameras")

YOLO_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
PERSON_CONFIDENCE_THRESHOLD = float(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.30"))
INFERENCE_IMAGE_SIZE = int(os.getenv("INFERENCE_IMAGE_SIZE", "320"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "auto")
MAX_ANALYSIS_WIDTH = int(os.getenv("MAX_ANALYSIS_WIDTH", "640"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

os.makedirs(ANNOTATED_DIR, exist_ok=True)
