# Passenger Flow Predictor - Stage 1 (Static Computer Vision MVP)

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Open Swagger UI for testing:

- Go to http://localhost:8000/docs

5. Test with curl:

```bash
curl -X POST "http://localhost:8000/api/detect" -F "file=@your_image.jpg" -F "camera_id=cam_checkin_01"
```

## How zone assignment works
- Each detected person’s bbox center is checked against each zone polygon for the given camera.
- The first matching zone is assigned; if none match, zone_id is "outside".
- Point-in-polygon uses a simple ray-casting algorithm (no heavy GIS libs).

## Common errors and fixes
- **ultralytics not found**: `pip install ultralytics`
- **opencv-python not found**: `pip install opencv-python`
- **python-multipart not found**: `pip install python-multipart`
- **torch not found**: `pip install torch`
- **YOLO model download fails**: Ensure internet access for first run.
- **FileNotFoundError for zones.json**: Check `backend/app/data/zones.json` exists.
- **PermissionError saving annotated images**: Ensure `backend/app/static/annotated/` is writable.
