import json
import os
import glob
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
import cv2
from PIL import Image
import numpy as np
from app.core.config import ANNOTATED_DIR, CAMERA_VIDEO_ROOT
from app.services.vision import detect_people_and_count_zones, draw_annotations

router = APIRouter()

CAMERAS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cameras.json")
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_cameras():
    with open(CAMERAS_PATH, "r") as f:
        return json.load(f)["cameras"]

def get_camera_folder_name(camera):
    """Return camera subfolder name while supporting older full folder paths."""
    folder_name = camera.get("folder_name")
    if folder_name:
        return folder_name

    folder = camera.get("folder", "")
    normalized = folder.replace("\\", "/").strip("/")
    for marker in ("test_assets/cameras/", "test_assets/cameras_deploy/"):
        if normalized.startswith(marker):
            return normalized[len(marker):]
    return os.path.basename(normalized)

def get_video_root():
    return CAMERA_VIDEO_ROOT if os.path.isabs(CAMERA_VIDEO_ROOT) else os.path.join(BACKEND_DIR, CAMERA_VIDEO_ROOT)

def get_camera_folder(camera):
    folder_name = get_camera_folder_name(camera)
    if not folder_name:
        return None
    return os.path.join(get_video_root(), folder_name)

def get_video_path(camera):
    """Auto-detect first video file in camera folder."""
    folder_path = get_camera_folder(camera)
    if not folder_path:
        return None
    video_patterns = ["*.mp4", "*.avi", "*.mov", "*.mkv"]
    for pattern in video_patterns:
        files = glob.glob(os.path.join(folder_path, pattern))
        if files:
            return files[0]
    return None

def get_risk_level(counts):
    """Determine risk level based on total people count."""
    total = sum(counts.values())
    if total > 20:
        return "high"
    elif total > 10:
        return "medium"
    else:
        return "low"

@router.get("/cameras")
def list_cameras():
    cameras = load_cameras()
    result = []
    for cam in cameras:
        video_path = get_video_path(cam)
        result.append({
            **cam,
            "folder_name": get_camera_folder_name(cam),
            "video_found": video_path is not None,
            "video_url": f"/api/cameras/{cam['id']}/video"
        })
    return result

@router.get("/cameras/{camera_id}")
def get_camera(camera_id: str):
    cameras = load_cameras()
    for cam in cameras:
        if cam["id"] == camera_id:
            video_path = get_video_path(cam)
            return {
                **cam,
                "folder_name": get_camera_folder_name(cam),
                "video_found": video_path is not None,
                "video_url": f"/api/cameras/{camera_id}/video"
            }
    raise HTTPException(status_code=404, detail="Camera not found")

@router.get("/cameras/{camera_id}/video")
def get_video(camera_id: str):
    """Serve video file for streaming in dashboard"""
    cameras = load_cameras()
    camera = None
    for cam in cameras:
        if cam["id"] == camera_id:
            camera = cam
            break
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    video_path = get_video_path(camera)
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Return video file with streaming support
    return FileResponse(video_path, media_type="video/mp4")

# Global cache for video capture objects
_cap_cache = {}

@router.post("/cameras/{camera_id}/analyze-snapshot")
def analyze_snapshot(camera_id: str, timestamp_seconds: float = Query(0), demo: bool = Query(False)):
    cameras = load_cameras()
    camera = None
    for cam in cameras:
        if cam["id"] == camera_id:
            camera = cam
            break
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    video_path = get_video_path(camera)
    if not video_path:
        raise HTTPException(status_code=400, detail="No video file found for this camera")
    
    try:
        # Use cached capture object or open new one
        if camera_id not in _cap_cache:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"Could not open video file: {video_path}")
            _cap_cache[camera_id] = cap
        else:
            cap = _cap_cache[camera_id]
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25.0
            
        frame_number = int(timestamp_seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        # If read fails, try to reset the capture
        if not ret or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret or frame is None:
                raise Exception(f"Failed to read frame at {timestamp_seconds}s from {video_path}")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Run detection on a resized analysis frame for fast demo refresh.
        detections, counts, metadata = detect_people_and_count_zones(
            frame_rgb,
            camera["zone_camera_id"],
            return_metadata=True,
            force_demo=demo
        )
        
        # Draw annotations
        pil_image = Image.fromarray(metadata["analysis_image"])
        annotated = draw_annotations(
            pil_image,
            detections,
            camera["zone_camera_id"],
            metadata["zone_scale"],
        )
        
        # Save annotated frame
        os.makedirs(os.path.join(ANNOTATED_DIR, "cameras"), exist_ok=True)
        fname = f"{camera_id}_{int(timestamp_seconds)}.jpg"
        out_path = os.path.join(ANNOTATED_DIR, "cameras", fname)
        annotated = annotated.convert("RGB")
        annotated.save(out_path, format="JPEG")
        
        # Compute status
        total_count = sum(counts.values())
        risk_level = get_risk_level(counts)
        summary = {
            "low": "Low occupancy, normal operations.",
            "medium": "Moderate occupancy, monitor zones.",
            "high": "High occupancy, consider staff allocation."
        }.get(risk_level, "Unknown status")
        
        return {
            "camera_id": camera_id,
            "camera_name": camera["name"],
            "timestamp_seconds": timestamp_seconds,
            "counts": counts,
            "detections_count": len(detections),
            "annotated_frame_url": f"/static/annotated/cameras/{fname}",
            "status": {
                "risk_level": risk_level,
                "summary": summary,
                "total_people": total_count
            },
            "performance": metadata["performance"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
