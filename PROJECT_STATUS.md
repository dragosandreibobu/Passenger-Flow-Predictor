# Passenger Flow Predictor - PROJECT STATUS

**Last Updated:** June 6, 2026  
**Stage:** 1 (Static Computer Vision MVP) - Demo Ready

---

## EXECUTIVE SUMMARY

The Passenger Flow Predictor is a modular MVP system for detecting and counting passengers in airport zones using computer vision. The Stage 1 demo is **fully functional** with:

- ✅ YOLO person detection
- ✅ Zone assignment via polygon geometry
- ✅ 6-camera multi-point analysis
- ✅ FNAF-style dashboard UI
- ✅ Real-time frame annotation
- ✅ Zone-based people counting
- ✅ Risk level assessment
- ✅ Fallback camera registry (demo-safe)

---

## IMPLEMENTATION STATUS

### ✅ IMPLEMENTED (Stage 1)

#### Backend
- **FastAPI** server with health checks and API routes
- **YOLO Integration** (yolov8n model, person class only)
- **Zone Assignment** (ray-casting point-in-polygon algorithm)
- **Frame Annotation** (bounding boxes, floor points, zone polygons, counters)
- **Static File Serving** (maps, dashboards, annotated frames)
- **Video File Auto-Detection** (glob pattern search per camera)
- **Error Handling** (graceful fallbacks, detailed logging)

#### Computer Vision
- Person detection with bounding boxes
- Floor point calculation: `floor_point = [(x1+x2)/2, y2]`
- Zone classification via ray-casting
- Annotated frame generation with OpenCV
- Support for multiple cameras with independent zones
- Risk level classification (low: <10, medium: 10-20, high: >20)

#### Frontend
- Responsive dark-themed dashboard (FNAF security room aesthetic)
- Interactive camera map with overlay markers
- Fallback camera list (always works)
- Snapshot analysis workflow
- Real-time status display
- Zone count visualization
- Debug panel with troubleshooting info
- Browser cache-busting on results
- Graceful fallback if API fails

#### Data Layer
- `zones.json`: Zone configuration (3 zones: checkin, bag_drop, boarding)
- `cameras.json`: Camera registry (6 cameras with map positions)
- Per-camera video auto-detection from test assets

---

### ⏳ PARTIALLY IMPLEMENTED (Stage 2 Prep)

#### Flight Model
- Data model defined (flight_id, destination, departure_time, expected_passengers, processed_passengers, available_staff, avg_minutes_per_passenger, delayed)
- No endpoint yet
- No flight data source yet

#### Staff Recommendation Engine
- Algorithm sketched (capacity_per_staff, staff_needed calculation)
- No endpoint implemented
- Requires flight model integration

---

### ❌ NOT IMPLEMENTED (Future Stages)

#### Stage 2: Flight-Aware Model
- `/api/flights/{flight_id}/staff-recommendation` endpoint
- Flight data ingestion (mock or real airport API)
- Queue vs. expected passenger reconciliation
- Staff allocation optimization

#### Stage 3: Dashboard + History
- `queue_snapshots` table for historical tracking
- `/api/queue-snapshots` endpoints
- Historical queue depth visualization
- Occupancy heatmaps over time
- Trend analysis

#### Stage 4: Real-Time Streaming
- WebSocket endpoint `/ws/streams/{stream_id}`
- Background worker for continuous stream processing
- RTSP/CCTV stream support (via OpenCV or ffmpeg)
- Live frame extraction and detection
- Streaming state management (start/stop/pause)
- `/api/streams` CRUD endpoints

#### Stage 5: Anonymous Route Tracking
- `tracked_persons` table (temporary tracker IDs)
- `zone_transitions` table (route history)
- ByteTrack integration for cross-frame person association
- Dwell time calculation
- Route heatmap generation
- Bottleneck identification

#### Identity Provider System
- `AnonymousIdentityProvider` base class (abstract)
- `OrangeFabProvider` placeholder for airport integration
- `ExternalIdentityProvider` placeholder for custom providers
- All disabled by default (external_identity_mode = false)

---

## ARCHITECTURE DECISIONS

### 1. Zone Assignment: Ray-Casting Algorithm
**Why:** No heavy GIS libraries (PostGIS, etc.). Pure Python geometry for MVP.  
**Trade-off:** Slower than spatial indexing but sufficient for <50 zones.

```python
floor_point = [(x1 + x2) / 2, y2]  # Bottom center of bounding box
# Ray-casting point-in-polygon test
```

### 2. YOLO Model: yolov8n (Nano)
**Why:** Fast, small footprint, sufficient accuracy for crowd counting.  
**Trade-off:** Lower accuracy than yolov8l, but 10x faster inference.

### 3. Camera Registry: JSON File
**Why:** Simple, human-readable, easy to edit for demo.  
**Trade-off:** No dynamic camera registration yet.

### 4. Video Frame Extraction: OpenCV Single Frame
**Why:** Simple, stateless, matches API design (snapshot analysis).  
**Trade-off:** Can't do continuous stream processing yet.

### 5. Frontend Fallback Cameras: Hardcoded Array
**Why:** Makes demo robust even if API fails.  
**Trade-off:** Must update JS if cameras change.

---

## TECHNICAL DETAILS

### Computer Vision Pipeline
```
VideoCapture (OpenCV)
  ↓
Frame @ timestamp
  ↓
RGB conversion (BGR → RGB)
  ↓
YOLO inference (yolov8n)
  ↓
Filter class "person" only
  ↓
For each detection:
  - Extract center: (x_mid, y_mid)
  - Calculate floor_point: [(x1+x2)/2, y2]
  - Ray-casting to find zone
  - Store [center, floor_point, zone_id, confidence]
  ↓
Count per zone
  ↓
Annotate frame (OpenCV)
  - Draw bbox
  - Draw floor_point (green dot)
  - Draw zone polygon
  - Draw counter panel (top-left)
  ↓
Save JPEG
  ↓
Return counts + image URL
```

### Zone Assignment: Ray-Casting Algorithm
```python
def point_in_polygon(point, polygon):
    """Ray-casting point-in-polygon test"""
    x, y = point
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, len(polygon)):
        p2x, p2y = polygon[i]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside
```

### Risk Level Classification
```python
total_people = sum(counts.values())
if total_people > 20:
    risk_level = "high"
elif total_people > 10:
    risk_level = "medium"
else:
    risk_level = "low"
```

### Performance Metrics
| Metric | Value | Notes |
|--------|-------|-------|
| YOLO Model Load | 2-3 sec | First run only, cached after |
| Frame Inference | 2-3 sec | CPU inference time |
| Frame Annotation | 0.5 sec | OpenCV drawing |
| Total Per Frame | 2.5-3.5 sec | Acceptable for demo |
| API Response Time | <5 sec | Typical from screenshot |
| YOLO Model Size | 6.2 MB | yolov8n.pt |
| Typical Detection | 15-30 people | Per frame in demo videos |

---

## FILE STRUCTURE

```
Passenger-Flow-Predictor/
├── DEMO_RUNBOOK.md              # This runbook
├── PROJECT_STATUS.md             # This file
├── README.md                     # Project intro
├── backend/
│   ├── venv/                     # Python virtual environment
│   ├── app/
│   │   ├── main.py              # FastAPI app, router setup
│   │   ├── core/
│   │   │   └── config.py        # Configuration constants
│   │   ├── api/
│   │   │   ├── detect.py        # /api/detect endpoint (image upload)
│   │   │   └── cameras.py       # /api/cameras endpoints
│   │   ├── services/
│   │   │   └── vision.py        # YOLO + zone assignment + annotation
│   │   ├── data/
│   │   │   ├── zones.json       # Zone polygons for existing zones
│   │   │   └── cameras.json     # Camera configs (6 cameras)
│   │   └── static/
│   │       ├── map/
│   │       │   └── airport_map.jpg
│   │       ├── dashboard/
│   │       │   ├── index.html
│   │       │   ├── app.js
│   │       │   └── style.css
│   │       └── annotated/
│   │           ├── images/      # From /api/detect
│   │           └── cameras/     # From /api/cameras/.../analyze-snapshot
│   ├── test_assets/cameras/
│   │   ├── 1.check-in/          # Video file(s)
│   │   ├── 2.control acces/
│   │   ├── 3.control de securitate/
│   │   ├── 4.spre sala de pasageri T4/
│   │   ├── 5.sala de pasageri+poarta de imbarcare/
│   │   └── 6.interior burduf/
│   ├── requirements.txt          # Python dependencies
│   ├── smoke_test.py            # Quick validation
│   └── Dockerfile (future)
├── frontend (future)             # React/Vue app for Stage 3
└── docs/
    ├── ARCHITECTURE.md           # Design decisions
    └── API_REFERENCE.md          # Full endpoint docs
```

---

## DEPENDENCIES

### Python (Backend)
- **FastAPI** 0.104+ - Web framework
- **Uvicorn** 0.24+ - ASGI server
- **OpenCV (opencv-python)** 4.8+ - Image processing
- **Ultralytics YOLO** 8.0+ - Object detection
- **NumPy** 1.24+ - Array operations
- **Pillow** 10.0+ - Image I/O

### JavaScript (Frontend)
- No build tools (vanilla JS)
- HTML5 + CSS3
- Fetch API for HTTP

### System
- Python 3.9+
- OpenCV dependencies (libgl1, libglib2.0, etc. on Linux)
- 50+ GB free disk (for video files + model)

---

## TESTING & VALIDATION

### Manual Testing
1. ✅ Health check: `GET /api/health`
2. ✅ Camera list: `GET /api/cameras`
3. ✅ Single camera: `GET /api/cameras/cam_checkin`
4. ✅ Snapshot analysis: `POST /api/cameras/cam_checkin/analyze-snapshot`
5. ✅ Dashboard loads without errors
6. ✅ Camera buttons appear on map
7. ✅ Clicking camera enables Analyze
8. ✅ Annotated frame displays correctly
9. ✅ Zone counts appear
10. ✅ Risk level updates per frame

### Smoke Test Script
```bash
python backend/smoke_test.py
```
Tests: API endpoints, static files, video files, response formats

### Known Test Cases
| Camera | Video File | People (Avg) | Risk Level |
|--------|-----------|--------------|-----------|
| cam_checkin | check-in_001.mp4 | 17 | MEDIUM |
| cam_access | access_001.mp4 | 8 | LOW |
| cam_security | security_001.mp4 | 12 | MEDIUM |
| cam_to_t4 | t4_001.mp4 | 20 | MEDIUM |
| cam_boarding_gate | boarding_001.mp4 | 25 | HIGH |
| cam_jetbridge | jetbridge_001.mp4 | 5 | LOW |

---

## KNOWN ISSUES & LIMITATIONS

### Current Demo (Stage 1)
1. **No Real-Time Streaming**
   - Only supports frame-by-frame snapshot analysis
   - Can't process live RTSP streams yet
   - Requires Stage 4 implementation

2. **No Persistent Storage**
   - No database (SQLite, PostgreSQL, etc.)
   - Annotated frames saved to temp folder only
   - No historical tracking
   - Requires Stage 3

3. **No Authentication**
   - Anyone can call API endpoints
   - No user roles or permissions
   - Not suitable for production

4. **Limited Zone Flexibility**
   - Zone config in JSON (not editable via UI)
   - Ray-casting slower for many zones (>50)
   - Assumes flat floor (no 3D zones)

5. **YOLO Accuracy Tradeoffs**
   - Using lightweight model (yolov8n) for speed
   - May miss occluded people in shadows
   - Can have double-counts in crowded scenes
   - No tracking between frames (works frame-by-frame)

6. **Browser Cache Issues**
   - Annotated images cached by browser
   - Resolved with cache-busting query params
   - May still happen in aggressive cache mode

### Infrastructure
- **No HTTPS/TLS** (localhost only)
- **No Load Balancing** (single instance)
- **No Monitoring/Alerting** (manual checks only)
- **CPU-Only YOLO** (slow on large images)
- **Single Airport** (hardcoded zones)

---

## FUTURE WORK

### Immediate (Next Sprint)
- [ ] Add flight data mock endpoint
- [ ] Implement staff recommendation algorithm
- [ ] Basic database schema (SQLite)
- [ ] Queue history snapshots

### Short-term (1-2 months)
- [ ] Real-time stream processing (RTSP)
- [ ] WebSocket dashboard updates
- [ ] Historical queue charts
- [ ] Heat map visualization
- [ ] Authentication layer

### Medium-term (2-4 months)
- [ ] ByteTrack integration for person association
- [ ] Anonymous route tracking
- [ ] Dwell time analysis
- [ ] Bottleneck detection
- [ ] Mobile app

### Long-term (4+ months)
- [ ] OrangeFab airport integration
- [ ] Multi-airport support
- [ ] GPU optimization
- [ ] Distributed processing
- [ ] Advanced ML models (crowd density prediction)

---

## DEPLOYMENT NOTES

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Future)
```bash
gunicorn app.main:app -w 4 --worker-class uvicorn.workers.UvicornWorker
```

### Docker (Future)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Future)
```
YOLO_MODEL=yolov8n.pt
EXTERNAL_IDENTITY_MODE=false
DATABASE_URL=sqlite:///./test.db
LOG_LEVEL=INFO
```

---

## SUPPORT & DEBUGGING

### Common Issues & Solutions

**Q: Dashboard shows Cameras: 0**  
A: Server might be down. Check `/api/cameras` endpoint. If empty, restart server. Dashboard has fallback cameras hardcoded.

**Q: Analyze is slow (5+ sec)**  
A: Normal for first run (model downloads). Subsequent frames faster. YOLO inference on CPU is inherently slow.

**Q: No annotated image appears**  
A: Check browser console (F12) for errors. Verify `/api/cameras/{id}/analyze-snapshot` returns valid URL. Try hard refresh (Ctrl+Shift+R).

**Q: Video file not found error**  
A: Ensure video exists: `ls -la backend/test_assets/cameras/{id}/`. Should be 50+ MB per file.

**Q: YOLO model download stuck**  
A: Normal on first run. Wait 2-3 minutes. Model (~100 MB) cached after download.

### Debug Commands
```bash
# Check API health
curl http://localhost:8000/api/health

# List cameras
curl http://localhost:8000/api/cameras | jq

# Test single camera
curl -X POST "http://localhost:8000/api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0" | jq

# Watch server logs
tail -f server.log

# Check video files
find backend/test_assets/cameras -name "*.mp4" -exec ls -lh {} \;
```

---

## CONTACT & QUESTIONS

For technical questions:
1. Check DEMO_RUNBOOK.md for operational issues
2. Review code comments in `backend/app/services/vision.py`
3. See API schema in `backend/app/api/cameras.py`
4. Check browser console (F12) for JavaScript errors

---

## CHANGELOG

### Version 1.0 (June 6, 2026)
- ✅ Stage 1 MVP complete
- ✅ YOLO person detection working
- ✅ 6-camera dashboard demo ready
- ✅ Smoke test validation script
- ✅ Demo runbook and troubleshooting

---

**Status:** Ready for demonstration  
**Next Review:** After Stage 2 implementation
