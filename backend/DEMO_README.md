# 🎥 Passenger Flow Predictor - Airport Control Room Demo

**Status:** ✅ FULLY FUNCTIONAL

## Quick Start

### 1. Start Server
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Open Dashboard
```
http://localhost:8000/dashboard
```

### 3. Click a Camera & Analyze

- **Left:** 6 airport camera buttons on map
- **Right:** Analysis panel with annotated frame
- **Bottom:** Zone counts and risk assessment

---

## 📍 6 Airport Cameras

| # | Camera | Location | Videos |
|---|--------|----------|--------|
| 1 | Check-in | Counter area | 13 MB |
| 2 | Control Acces | Security entrance | 6.9 MB |
| 3 | Control Securitate | Security scanning | 17 MB |
| 4 | Spre T4 | Corridor to gates | 16 MB |
| 5 | Sala Pasageri | Gate area | 12 MB |
| 6 | Interior Burduf | Jet bridge | 36 MB |

---

## 🎮 Dashboard Controls

- **Camera Buttons:** Click on map to select camera
- **Timestamp:** Enter seconds (default 0)
- **Analyze:** Extract frame and run YOLO detection
- **Results:** Annotated frame + counts + risk level

---

## 🔌 API Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# List all cameras
curl http://localhost:8000/api/cameras

# Get single camera
curl http://localhost:8000/api/cameras/cam_checkin

# Analyze frame at timestamp
curl -X POST "http://localhost:8000/api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0"

# Access dashboard
http://localhost:8000/dashboard
```

---

## 📊 Analysis Response

```json
{
  "camera_id": "cam_checkin",
  "camera_name": "1. Check-in",
  "timestamp_seconds": 0,
  "counts": {
    "checkin": 12,
    "bag_drop": 4,
    "boarding": 1,
    "outside": 3
  },
  "detections_count": 20,
  "annotated_frame_url": "/static/annotated/cameras/cam_checkin_0.jpg",
  "status": {
    "risk_level": "medium",
    "summary": "Moderate occupancy, monitor zones.",
    "total_people": 20
  }
}
```

---

## 🎨 Dashboard Features

✅ Dark FNAF/security room theme (terminal green on black)
✅ Interactive airport map with 6 camera buttons
✅ Real-time YOLO person detection on video frames
✅ Automatic zone assignment (check-in, bag-drop, boarding, outside)
✅ Visual risk indicators (low/medium/high)
✅ Annotated frame display with bounding boxes
✅ Zone count panel
✅ Error handling for missing videos

---

## 🛠 Technical Stack

- **Backend:** FastAPI + Uvicorn
- **CV:** Ultralytics YOLO v8n + OpenCV
- **Frontend:** HTML5 + Vanilla JavaScript
- **Data:** JSON configs (no database)

---

## ⚡ Performance

- Frame extraction: ~1 sec
- YOLO detection: ~1-2 sec
- Total response: ~2-3 sec per frame

---

## 📝 Notes

- All 6 camera videos auto-detected from `fluxuri pasageri 2026/`
- Zones configurable in `app/data/zones.json`
- No authentication required (demo system)
- Runs entirely local (no external APIs)

---

## 🎯 What's NOT Included

- ❌ Live RTSP streaming
- ❌ Real-time WebSocket updates (single frame per request)
- ❌ Database persistence
- ❌ Route tracking / ByteTrack
- ❌ Staff optimization engine
- ❌ OrangeFab integration

---

**Enjoy the demo! 🎮**
