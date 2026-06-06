# Deployment Notes

## Camera Video Assets

Original camera videos are preserved locally under:

```text
backend/test_assets/cameras/
```

Do not delete, overwrite, or move these originals. They are intentionally ignored by Git because they are heavy source assets.

Deployment-friendly compressed copies live under:

```text
backend/test_assets/cameras_deploy/
```

The compressed deploy folder preserves the camera subfolders:

```text
1.check-in/
2.control acces/
3.control de securitate/
4.spre sala de pasageri T4/
5.sala de pasageri+poarta de imbarcare/
6.interior burduf/
7.check-in 3-8 ansamblu/
8.e gate 13-14 business/
```

All cameras must remain available in both local and deploy modes. The two newer source videos were originally added as loose files under `backend/test_assets/cameras/`; local app copies were created in camera folders so the same folder-based pipeline works for development and deployment. The loose originals remain untouched.

## Regenerate Deploy Videos

From the backend folder:

```powershell
cd backend
python prepare_deploy_videos.py --max-seconds 45 --speed 2 --width 960 --crf 30
```

The script:

- scans `test_assets/cameras/`
- writes compressed copies to `test_assets/cameras_deploy/`
- preserves camera folder names
- never modifies original videos
- removes audio
- outputs H.264 `.mp4`
- reports original size, compressed size, and total reduction

If the speed filter is unsupported by the installed ffmpeg build, the script falls back to normal-speed compression.

## Switch Video Roots

Local full-quality mode:

```powershell
$env:CAMERA_VIDEO_ROOT="test_assets/cameras"
```

Deployment compressed-video mode:

```powershell
$env:CAMERA_VIDEO_ROOT="test_assets/cameras_deploy"
```

The default is:

```text
CAMERA_VIDEO_ROOT=test_assets/cameras
```

## Render Environment

Set these environment variables on Render for optimal performance:

```text
CAMERA_VIDEO_ROOT=test_assets/cameras_deploy
YOLO_MODEL_NAME=yolov8n.pt
INFERENCE_IMAGE_SIZE=320
MAX_ANALYSIS_WIDTH=640
PERSON_CONFIDENCE_THRESHOLD=0.30
```

## Demo Mode (Preprocessed)

The dashboard now defaults to **Preprocessed** mode. This mode uses simulated detections to provide an instant, smooth experience without taxing the server's CPU. It is highly recommended for public demos on Render Free tier.

To test real AI inference, switch the "Mode" selector to **Live AI Feed**.

## YOLO Tuning Examples

Fastest local/deploy option:

```powershell
$env:INFERENCE_IMAGE_SIZE="320"
$env:MAX_ANALYSIS_WIDTH="720"
$env:PERSON_CONFIDENCE_THRESHOLD="0.30"
```

Better accuracy option:

```powershell
$env:YOLO_MODEL_NAME="yolov8s.pt"
$env:INFERENCE_IMAGE_SIZE="640"
```

Production optimization can later use ONNX Runtime, TensorRT, OpenVINO, or GPU inference. This deployment keeps the current FastAPI snapshot endpoint and local-video fake-live demo.
