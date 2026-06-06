import io
import json
import os
import time
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ultralytics import YOLO
import cv2
from app.core.config import (
    ZONES_PATH,
    ANNOTATED_DIR,
    YOLO_MODEL_NAME,
    PERSON_CONFIDENCE_THRESHOLD,
    INFERENCE_IMAGE_SIZE,
    YOLO_DEVICE,
    MAX_ANALYSIS_WIDTH,
    DEMO_MODE,
)
from app.models.zone import Zone

# Global model cache for lazy loading
_model_cache = None

def get_model():
    """Lazy load YOLO model to save memory on startup."""
    global _model_cache
    if _model_cache is None and not DEMO_MODE:
        _model_cache = YOLO(YOLO_MODEL_NAME)
    return _model_cache

# Load zones config
with open(ZONES_PATH, "r") as f:
    zones_data = json.load(f)["zones"]
    ZONES = [Zone(**z) for z in zones_data]

def point_in_polygon(point, polygon):
    # Ray casting algorithm
    x, y = point
    inside = False
    n = len(polygon)
    px, py = polygon[0]
    for i in range(1, n+1):
        nx, ny = polygon[i % n]
        if min(py, ny) < y <= max(py, ny) and x <= max(px, nx):
            if py != ny:
                xinters = (y - py) * (nx - px) / (ny - py) + px
            if px == nx or x <= xinters:
                inside = not inside
        px, py = nx, ny
    return inside

def scaled_polygon(polygon, scale):
    return [[int(x * scale), int(y * scale)] for x, y in polygon]

def assign_zone(center, camera_id, zone_scale=1.0):
    for zone in ZONES:
        polygon = scaled_polygon(zone.polygon, zone_scale)
        if zone.camera_id == camera_id and point_in_polygon(center, polygon):
            return zone
    return None

def draw_annotations(image, detections, camera_id, zone_scale=1.0):
    draw = ImageDraw.Draw(image)
    # Draw zones
    for zone in ZONES:
        if zone.camera_id == camera_id:
            polygon = scaled_polygon(zone.polygon, zone_scale)
            draw.polygon([tuple(pt) for pt in polygon], outline="cyan", width=2)
            draw.text(tuple(polygon[0]), zone.id, fill="cyan")
    # Draw detections
    for det in detections:
        bbox = det["bbox"]
        zone_color = "green" if det["zone_id"] != "outside" else "red"
        draw.rectangle(bbox, outline=zone_color, width=2)
        draw.text((bbox[0], bbox[1]), f"{det['zone_id']} {det['confidence']:.2f}", fill=zone_color)
    return image

def resize_for_analysis(image_np):
    """Resize large frames before inference while preserving aspect ratio."""
    height, width = image_np.shape[:2]
    if width <= MAX_ANALYSIS_WIDTH:
        return image_np, 1.0

    scale = MAX_ANALYSIS_WIDTH / float(width)
    resized_height = max(1, int(height * scale))
    resized = cv2.resize(image_np, (MAX_ANALYSIS_WIDTH, resized_height), interpolation=cv2.INTER_AREA)
    return resized, scale

def run_model(image_np):
    model = get_model()
    if model is None:
        return []

    kwargs = {
        "imgsz": INFERENCE_IMAGE_SIZE,
        "verbose": False,
    }
    if YOLO_DEVICE and YOLO_DEVICE.lower() != "auto":
        kwargs["device"] = YOLO_DEVICE

    try:
        return model(image_np, **kwargs)
    except TypeError:
        kwargs.pop("verbose", None)
        return model(image_np, **kwargs)

def run_mock_detection(camera_id, zone_scale):
    """Generate simulated detections for demo purposes without using AI models."""
    import random
    detections = []
    relevant_zones = [z for z in ZONES if z.camera_id == camera_id]
    
    # Simulate 3-8 people
    num_people = random.randint(3, 8)
    for _ in range(num_people):
        # Pick a random zone or "outside"
        if random.random() < 0.8 and relevant_zones:
            zone = random.choice(relevant_zones)
            poly = scaled_polygon(zone.polygon, zone_scale)
            # Find a point inside the polygon (simplified: just use one of the vertices or center)
            # For a mock, just pick a point near the first vertex
            x = poly[0][0] + random.randint(-20, 20)
            y = poly[0][1] + random.randint(-20, 20)
            zone_id, zone_name, zone_type = zone.id, zone.name, zone.type
        else:
            x, y = random.randint(100, 800), random.randint(100, 500)
            zone_id, zone_name, zone_type = "outside", None, None

        detections.append({
            "class": "person",
            "confidence": random.uniform(0.7, 0.95),
            "bbox": [x-20, y-50, x+20, y+10],
            "center": [x, y-20],
            "floor_point": [x, y],
            "zone_id": zone_id,
            "zone_name": zone_name,
            "zone_type": zone_type
        })
    return detections

def detect_people_and_count_zones(image_np, camera_id, return_metadata=False):
    """Core detection logic reused by both image upload and camera snapshot endpoints."""
    original_height, original_width = image_np.shape[:2]
    analysis_np, zone_scale = resize_for_analysis(image_np)
    input_height, input_width = analysis_np.shape[:2]

    start = time.perf_counter()
    
    if DEMO_MODE:
        # Skip inference and return simulated data
        detections = run_mock_detection(camera_id, zone_scale)
        inference_ms = 10.0 # Simulated speed
    else:
        results = run_model(analysis_np)
        inference_ms = (time.perf_counter() - start) * 1000

        detections = []
        model = get_model()
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                name = model.names[cls]
                if name != "person":
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                if conf < PERSON_CONFIDENCE_THRESHOLD:
                    continue
                center = [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                floor_point = [int((x1 + x2) / 2), y2]
                zone = assign_zone(floor_point, camera_id, zone_scale)
                if zone:
                    zone_id = zone.id
                    zone_name = zone.name
                    zone_type = zone.type
                else:
                    zone_id = "outside"
                    zone_name = None
                    zone_type = None
                
                detections.append({
                    "class": "person",
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "center": center,
                    "floor_point": floor_point,
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "zone_type": zone_type
                })

    # Aggregate counts
    counts = {}
    for zone in ZONES:
        if zone.camera_id == camera_id:
            counts[zone.id] = 0
    counts["outside"] = 0
    
    for det in detections:
        zone_id = det["zone_id"]
        if zone_id in counts:
            counts[zone_id] += 1
        else:
            counts["outside"] += 1

    if return_metadata:
        performance = {
            "inference_ms": round(inference_ms, 1),
            "model_name": YOLO_MODEL_NAME,
            "image_size": INFERENCE_IMAGE_SIZE,
            "effective_fps": round(1000 / inference_ms, 2) if inference_ms > 0 else None,
            "input_width": input_width,
            "input_height": input_height,
            "original_width": original_width,
            "original_height": original_height,
            "max_analysis_width": MAX_ANALYSIS_WIDTH,
        }
        metadata = {
            "analysis_image": analysis_np,
            "zone_scale": zone_scale,
            "performance": performance,
        }
        return detections, counts, metadata

    return detections, counts

async def process_image(file, camera_id):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    img_np = np.array(image)
    detections, counts, metadata = detect_people_and_count_zones(img_np, camera_id, return_metadata=True)
    
    # Annotate image
    annotated_url = None
    annotated_output_path = None
    annotation_error = None
    try:
        os.makedirs(ANNOTATED_DIR, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file.filename))[0]
        fname = f"{base_name}_annotated.jpg"
        out_path = os.path.join(ANNOTATED_DIR, fname)
        annotated = Image.fromarray(metadata["analysis_image"])
        annotated = draw_annotations(annotated, detections, camera_id, metadata["zone_scale"])
        annotated = annotated.convert("RGB")
        annotated.save(out_path, format="JPEG")
        annotated_url = f"/static/annotated/{fname}"
        annotated_output_path = out_path
    except Exception as e:
        annotation_error = str(e)
    result = {
        "camera_id": camera_id,
        "counts": counts,
        "detections": detections
    }
    if annotated_url:
        result["annotated_image_url"] = annotated_url
    if annotated_output_path:
        result["annotated_output_path"] = annotated_output_path
    if annotation_error:
        result["annotation_error"] = annotation_error
    return result
