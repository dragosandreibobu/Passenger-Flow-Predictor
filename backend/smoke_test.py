#!/usr/bin/env python3
"""
Smoke Test for Passenger Flow Predictor Demo
Tests critical endpoints and functionality
"""

import requests
import json
import sys
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
RESULTS = []

def test(name, url, method="GET", expected_keys=None):
    """Run a single test"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, timeout=10)
        
        status = "PASS" if response.status_code in [200, 201] else "FAIL"
        
        # Parse JSON if available
        try:
            data = response.json()
            if expected_keys and isinstance(data, dict):
                missing = [k for k in expected_keys if k not in data]
                if missing:
                    status = "FAIL"
                    details = f"Missing keys: {missing}"
                else:
                    details = f"Response: {json.dumps(data, indent=2)[:200]}"
            elif isinstance(data, list):
                details = f"Array with {len(data)} items"
            else:
                details = str(data)[:200]
        except:
            details = f"Status {response.status_code}"
        
        RESULTS.append((status, name, details))
        print(f"{status:4} {name:40} {details}")
        
        return status == "PASS"
    except Exception as e:
        RESULTS.append(("FAIL", name, str(e)))
        print(f"FAIL {name:40} {str(e)}")
        return False

def check_file_exists(path, name):
    """Check if a file exists"""
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"PASS {name:40} Exists ({size_mb:.1f} MB)")
        RESULTS.append(("PASS", name, f"File exists ({size_mb:.1f} MB)"))
        return True
    else:
        print(f"FAIL {name:40} File not found")
        RESULTS.append(("FAIL", name, "File not found"))
        return False

def main():
    print("\n" + "="*80)
    print("PASSENGER FLOW PREDICTOR - SMOKE TEST")
    print("="*80 + "\n")
    
    # 1. Health check
    print("1. Server Health")
    print("-" * 80)
    test("/api/health", f"{BASE_URL}/api/health", expected_keys=["status"])
    print()
    
    # 2. Camera API
    print("2. Camera API")
    print("-" * 80)
    cameras_ok = test("GET /api/cameras", f"{BASE_URL}/api/cameras")
    print()
    
    # 3. Single camera config
    print("3. Single Camera")
    print("-" * 80)
    test("GET /api/cameras/cam_checkin", f"{BASE_URL}/api/cameras/cam_checkin", 
         expected_keys=["id", "name", "video_found"])
    print()
    
    # 4. Snapshot analysis
    print("4. Snapshot Analysis")
    print("-" * 80)
    analysis_ok = test("POST /api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0", 
                       f"{BASE_URL}/api/cameras/cam_checkin/analyze-snapshot?timestamp_seconds=0",
                       method="POST",
                       expected_keys=["camera_id", "counts", "detections_count"])
    print()
    
    # 5. Static files
    print("5. Static Files")
    print("-" * 80)
    check_file_exists("/mnt/c/Users/Dragos/OneDrive/Coding Python/Passenger-Flow-Predictor/backend/app/static/map/airport_map.jpg", 
                     "Airport map image")
    check_file_exists("/mnt/c/Users/Dragos/OneDrive/Coding Python/Passenger-Flow-Predictor/backend/app/static/dashboard/index.html",
                     "Dashboard HTML")
    check_file_exists("/mnt/c/Users/Dragos/OneDrive/Coding Python/Passenger-Flow-Predictor/backend/app/static/dashboard/app.js",
                     "Dashboard JS")
    print()
    
    # 6. Video files
    print("6. Video Files")
    print("-" * 80)
    cameras_dir = Path("/mnt/c/Users/Dragos/OneDrive/Coding Python/Passenger-Flow-Predictor/backend/test_assets/cameras")
    for i in range(1, 7):
        videos = list(cameras_dir.glob(f"{i}.*/*.mp4")) + \
                 list(cameras_dir.glob(f"{i}.*/*.avi")) + \
                 list(cameras_dir.glob(f"{i}.*/*.mov")) + \
                 list(cameras_dir.glob(f"{i}.*/*.mkv"))
        if videos:
            size_mb = videos[0].stat().st_size / (1024 * 1024)
            print(f"PASS Camera {i:1} video found              {videos[0].name} ({size_mb:.1f} MB)")
            RESULTS.append(("PASS", f"Camera {i} video", f"{videos[0].name} ({size_mb:.1f} MB)"))
        else:
            print(f"FAIL Camera {i:1} video found              No video file")
            RESULTS.append(("FAIL", f"Camera {i} video", "Not found"))
    print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    passes = sum(1 for status, _, _ in RESULTS if status == "PASS")
    fails = sum(1 for status, _, _ in RESULTS if status == "FAIL")
    print(f"\nTotal: {len(RESULTS)} | PASS: {passes} | FAIL: {fails}\n")
    
    if fails == 0:
        print("✅ ALL TESTS PASSED - DEMO IS READY")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - CHECK ABOVE")
        return 1

if __name__ == "__main__":
    sys.exit(main())
