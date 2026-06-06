# Passenger Flow Predictor - DEMO RUNBOOK

**Last Updated:** June 6, 2026, 19:45 UTC  
**Status:** Ready for demonstration

---

## QUICK START (60 seconds)

### 1. Activate Virtual Environment
```bash
cd backend
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

### 2. Start the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for output:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Open Dashboard
```
http://localhost:8000/dashboard
```

You should see:
- ✅ Airport map image
- ✅ 6 bright green circular camera buttons numbered 1-6
- ✅ Camera names list below map
- ✅ Timestamp input (default: 0)
- ✅ Analyze button (initially disabled)
- ✅ Debug panel showing "JS Loaded ✓, Cameras: 6"

### 4. Run Smoke Test
```bash
# In a new terminal
cd backend
python smoke_test.py
```

Expected output:
```
PASS /api/health
PASS GET /api/cameras (returns 6 cameras)
PASS GET /api/cameras/cam_checkin
PASS POST analyze-snapshot (detections_count=17)
PASS Airport map image
PASS Dashboard HTML
PASS Dashboard JS
PASS Camera 1-6 videos found
✅ ALL TESTS PASSED - DEMO IS READY
```

---

## ENDPOINT REFERENCE

### Health Check
```bash
curl http://localhost:8000/api/health
```
Response: `{"status": "ok"}`

### List All Cameras
```bash
curl http://localhost:8000/api/cameras
```
Response: Array of 6 cameras with `id`, `name`, `map_position`, `video_found`

### Get Single Camera
```bash
curl http://localhost:8000/api/cameras/cam_checkin
```

### Analyze Snapshot
```bash
curl -X POST "http://localhost:8000/api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0"
```

Response:
```json
{
  "camera_id": "cam_checkin",
  "camera_name": "1. Check-in",
  "counts": {
    "checkin": 0,
    "bag_drop": 2,
    "boarding": 1,
    "outside": 14
  },
  "detections_count": 17,
  "annotated_frame_url": "/static/annotated/cameras/cam_checkin_0.jpg",
  "status": {
    "risk_level": "medium",
    "total_people": 17,
    "summary": "..."
  }
}
```

---

## DEMO CAMERAS

| Num | ID | Name | Location |
|-----|----|----|----------|
| 1 | cam_checkin | Check-in | Map: 22%, 65% |
| 2 | cam_access | Control acces | Map: 35%, 58% |
| 3 | cam_security | Control de securitate | Map: 48%, 48% |
| 4 | cam_to_t4 | Spre sala de pasageri T4 | Map: 60%, 42% |
| 5 | cam_boarding_gate | Sala pasageri + poarta imbarcare | Map: 75%, 40% |
| 6 | cam_jetbridge | Interior burduf | Map: 86%, 34% |

---

## DEMO WORKFLOW (5 minutes)

### Setup Phase
1. Open http://localhost:8000/dashboard in browser
2. Verify all 6 green buttons appear on map
3. Verify camera list below map shows all names
4. Open browser console (F12) to see debug info

### Interaction Phase
1. **Click Camera 1 (Check-in)**
   - Button turns WHITE (selected)
   - Right panel shows "1. Check-in"
   - Analyze button turns GREEN (enabled)

2. **Click Analyze Button**
   - Loading spinner appears
   - After 2-3 seconds: Annotated frame displays
   - Zone counts appear: checkin, bag_drop, boarding, outside
   - Risk level displays (GREEN/YELLOW/RED)
   - Total people count: 17

3. **Change Timestamp**
   - Enter: 5
   - Click Analyze again
   - Frame changes, people may be at different positions

4. **Click Camera 3 (Security)**
   - Previous selection un-highlights
   - Camera 3 selected (turns WHITE)
   - Analyze button stays GREEN
   - Click Analyze to see security checkpoint

5. **Try All 6 Cameras**
   - Quickly demonstrate each camera's detection
   - Narrate: "Each camera shows real-time people detection using YOLO vision model"

### Conclusion Phase
- Explain future stages:
  - Stage 2: Flight data integration for staff recommendations
  - Stage 3: Historical tracking and heatmaps
  - Stage 4: Live RTSP stream integration
  - Stage 5: Anonymous route tracking and dwell time analysis

---

## TROUBLESHOOTING

### Issue: Dashboard shows "Cameras: 0"

**Causes:**
- API not responding
- Browser cache problem
- JavaScript error

**Fix:**
1. Hard refresh browser: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Clear browser cache and reload
3. Check browser console (F12) for error messages
4. Verify API is working: `curl http://localhost:8000/api/cameras`
5. If API returns empty array, restart server
6. Last resort: Delete `.copilot_cache`, reload page

**Fallback:**
- Dashboard has hardcoded fallback cameras
- Even if API fails, you'll see all 6 cameras
- Debug panel will show "Using fallback: ..."

### Issue: No camera buttons appear on map

**Causes:**
- Map image failed to load
- CSS not loading
- JavaScript error

**Fix:**
1. Verify CSS loads: Check browser DevTools → Network tab
2. Check console (F12) for errors
3. Verify pointer-events: auto in camera-overlay
4. Try fallback list (below map) - should work even if map fails
5. Hard refresh: `Ctrl+Shift+R`

### Issue: Analyze button doesn't work

**Causes:**
- No camera selected (button should be disabled)
- API endpoint not running
- Video file missing

**Fix:**
1. Click a camera first (button should enable)
2. Verify API: `curl -X POST "http://localhost:8000/api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0"`
3. Check server logs for errors
4. If video missing: Verify files in `backend/test_assets/cameras/1.check-in/`

### Issue: YOLO detection is slow (5+ seconds per frame)

**Causes:**
- First run downloads YOLO model (~100 MB)
- CPU-intensive inference on large image
- Low system resources

**Fix:**
1. Wait for model download (only happens once)
2. Subsequent frames are faster (~2-3 seconds)
3. Close other applications to free CPU
4. Can reduce image resolution by editing zones.json (future)

### Issue: Video file errors

**Causes:**
- Video file not in expected location
- Video file corrupted
- OpenCV codec issue

**Fix:**
1. Verify video exists: `ls -lah backend/test_assets/cameras/1.check-in/`
2. Check file size (should be > 10 MB)
3. Try another camera
4. If all fail, re-copy videos:
   ```bash
   cd backend
   python -c "from scripts.copy_videos import main; main()"
   ```

### Issue: "Cache limit exceeded" or memory errors

**Causes:**
- Browser cache full
- Too many analysis frames cached

**Fix:**
1. Clear browser cache (DevTools → Application → Clear Storage)
2. Restart browser
3. Limit to 1-2 cameras during demo

---

## BROWSER CONSOLE DEBUGGING

Open browser console (F12) and look for:

### On Page Load
```
Dashboard JS loaded v_final
Fetching cameras from API...
Raw /api/cameras response: [...]
Parsed cameras: (6) [...]
Rendering 6 cameras
Rendering 6 camera markers...
Created marker 1 at 22%, 65%
...
Rendering 6 camera list buttons...
Dashboard initialization complete
```

### On Camera Selection
```
Selecting camera: cam_checkin
Analyzing camera: cam_checkin...
API URL: /api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0
Analysis result: {...}
```

### Error Messages
```
Camera loading failed, using fallback cameras: Error: ...
```

If you see these errors, check:
1. Server is running
2. API endpoint is accessible
3. Video file exists
4. YOLO model is loaded (check server logs)

---

## FILE LOCATIONS

```
backend/
├── app.main:app              # FastAPI app entry point
├── app/data/cameras.json     # Camera configuration
├── app/static/dashboard/     # Dashboard UI
│   ├── index.html            # HTML structure
│   ├── app.js                # Logic (with fallback cameras)
│   └── style.css             # Styling (FNAF dark theme)
├── app/static/map/
│   └── airport_map.jpg       # Airport floorplan (background image)
├── app/static/annotated/
│   └── cameras/              # Saved annotated frames (temporary)
├── test_assets/cameras/      # Real video files
│   ├── 1.check-in/
│   ├── 2.control acces/
│   ├── 3.control de securitate/
│   ├── 4.spre sala de pasageri T4/
│   ├── 5.sala de pasageri+poarta de imbarcare/
│   └── 6.interior burduf/
└── smoke_test.py            # Quick validation script
```

---

## PRESENTATION SCRIPT (60 seconds)

> *"Welcome to the Passenger Flow Predictor demo. This system uses computer vision to automatically detect and count passengers in airport zones in real-time.*
>
> *Here we have an interactive map of the airport with 6 camera feeds positioned at key checkpoints: check-in, security, boarding gates, and jetbridges.*
>
> *When we click on a camera—[click camera 1]—the system loads video from that checkpoint. Clicking 'Analyze' runs our YOLO detection model, which identifies every passenger and assigns them to specific zones.*
>
> *As you can see, we detected 17 people total: 2 at bag drop, 1 at the gate, and 14 in the general area. The system classifies this as medium risk, meaning reasonable wait times.*
>
> *This instant feedback helps airport staff respond faster to congestion. Let me show you another zone—[click camera 3]—security checkpoint. Different patterns here.*
>
> *In future versions, we'll integrate flight data to predict staff needs before queues build up, track passenger routes for bottleneck identification, and provide real-time alerts on a large display.*
>
> *Thank you."*

---

## KNOWN LIMITATIONS

### Current (Demo Only)
- Single frame analysis (no continuous streaming)
- No database persistence
- No authentication or multi-user support
- No real-time RTSP/CCTV feed support
- No passenger route tracking
- No staff allocation recommendations
- No heatmaps or historical analysis

### Performance
- YOLO inference: 2-3 seconds per frame (CPU)
- First run downloads model: ~2-3 minutes
- Supports up to 30 FPS if GPU available

### Accuracy
- Uses lightweight YOLO model (yolov8n) for speed
- May miss people in shadows or crowded areas
- Zone assignment assumes flat airport floor (no stairs)

---

## NEXT STEPS (Future Stages)

| Stage | Focus | Timeline |
|-------|-------|----------|
| 1 | Static CV MVP ✅ | Complete |
| 2 | Flight data + staff recs | 1-2 weeks |
| 3 | Dashboard + history | 2-3 weeks |
| 4 | Real-time streams | 3-4 weeks |
| 5 | Route tracking + heatmaps | 4-6 weeks |

---

## SUPPORT

For issues:
1. Check **TROUBLESHOOTING** section above
2. Run `python smoke_test.py` to identify problem
3. Check browser console (F12) for JavaScript errors
4. Review server logs for API errors
5. Verify all video files exist and are > 10 MB

For questions about architecture:
- See `PROJECT_STATUS.md` for implementation details
- See `backend/app/data/zones.json` for zone definitions
- See `backend/app/services/vision.py` for detection logic

---

## SAFETY CHECKS BEFORE DEMO

- [ ] Server running and responding to `/api/health`
- [ ] All 6 cameras visible on dashboard
- [ ] Browser console shows no red errors
- [ ] Smoke test passes all checks
- [ ] At least 1 camera analysis produces visible results
- [ ] Map image loads (or fallback placeholder shows)
- [ ] Analyze button enables after clicking camera
- [ ] Zone counts display on analysis result
- [ ] No YOLO model download messages (if first run, allow 5 minutes)
