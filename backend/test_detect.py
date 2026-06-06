import sys
import requests

if len(sys.argv) < 2:
    print("Usage: python test_detect.py <image_path>")
    sys.exit(1)

image_path = sys.argv[1]
url = "http://localhost:8000/api/detect"

with open(image_path, "rb") as f:
    files = {"file": (image_path, f, "image/jpeg")}
    data = {"camera_id": "cam_checkin_01"}
    resp = requests.post(url, files=files, data=data)

print("Status code:", resp.status_code)
try:
    result = resp.json()
    print("Counts:", result.get("counts"))
    print("Number of detections:", len(result.get("detections", [])))
    if "annotated_image_url" in result:
        print("Annotated image URL:", result["annotated_image_url"])
    if "annotated_output_path" in result:
        print("Annotated output path:", result["annotated_output_path"])
    if "annotation_error" in result:
        print("Annotation error:", result["annotation_error"])
except Exception as e:
    print("Error parsing response:", e)
