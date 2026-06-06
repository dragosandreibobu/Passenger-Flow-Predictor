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
)
from app.models.zone import Zone

# Load YOLO model once
model = YOLO(YOLO_MODEL_NAME)

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

def detect_people_and_count_zones(image_np, camera_id, return_metadata=False):
    """Core detection logic reused by both image upload and camera snapshot endpoints."""
    original_height, original_width = image_np.shape[:2]
    analysis_np, zone_scale = resize_for_analysis(image_np)
    input_height, input_width = analysis_np.shape[:2]

    start = time.perf_counter()
    results = run_model(analysis_np)
    inference_ms = (time.perf_counter() - start) * 1000

    detections = []
    counts = {}
    for zone in ZONES:
        if zone.camera_id == camera_id:
            counts[zone.id] = 0
    counts["outside"] = 0
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
                counts[zone_id] += 1
            else:
                zone_id = "outside"
                zone_name = None
                zone_type = None
                counts[zone_id] += 1
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
