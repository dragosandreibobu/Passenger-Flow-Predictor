import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
CAMERAS_PATH = BACKEND_DIR / "app" / "data" / "cameras.json"
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

sys.path.insert(0, str(BACKEND_DIR))
from app.services.vision import detect_people_and_count_zones, draw_annotations, resize_for_analysis  # noqa: E402


def resolve_path(raw_path):
    path = Path(raw_path)
    if path.is_absolute():
        return path

    candidates = [
        Path.cwd() / path,
        BACKEND_DIR / path,
        PROJECT_ROOT / path,
    ]

    parts = path.parts
    if parts and parts[0].lower() == "backend":
        candidates.append(BACKEND_DIR / Path(*parts[1:]))
    if parts and parts[0] == "test_assets":
        candidates.append(BACKEND_DIR / path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if parts and parts[0].lower() == "backend":
        return BACKEND_DIR / Path(*parts[1:])
    if parts and parts[0] == "test_assets":
        return BACKEND_DIR / path
    return Path.cwd() / path


def format_size(num_bytes):
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def load_cameras():
    with CAMERAS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)["cameras"]


def find_first_video(folder):
    if not folder.exists():
        return None
    files = sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)
    return files[0] if files else None


def safe_fps(cap):
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    return fps if math.isfinite(fps) and fps > 1 else 25.0


def risk_from_total(total):
    if total >= 16:
        return "HIGH", (255, 59, 48)
    if total >= 6:
        return "MED", (255, 176, 32)
    return "LOW", (31, 227, 124)


def draw_demo_overlay(image, camera, counts, detections, timestamp_seconds, mode_label):
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    font = ImageFont.load_default()
    total = int(sum(int(value or 0) for value in counts.values()))
    risk, risk_color = risk_from_total(total)

    draw.rectangle((0, 0, width, 76), fill=(2, 8, 18, 198))
    draw.rectangle((0, height - 48, width, height), fill=(2, 8, 18, 190))
    draw.rectangle((12, 12, 170, 56), outline=(0, 255, 102, 210), width=2)
    draw.text((22, 20), f"CAM {camera.get('name', camera['id'])}", fill=(230, 255, 246, 255), font=font)
    draw.text((22, 38), mode_label, fill=(0, 255, 102, 255), font=font)

    right_x = max(220, width - 240)
    draw.text((right_x, 18), f"People {total}", fill=(255, 255, 255, 255), font=font)
    draw.text((right_x, 38), f"Risk {risk}", fill=risk_color + (255,), font=font)
    draw.text((right_x, 58), f"t={timestamp_seconds:05.1f}s", fill=(142, 212, 255, 255), font=font)

    x = 14
    for zone, value in list(counts.items())[:6]:
        text = f"{zone} {value}"
        chip_width = max(74, 8 * len(text) + 20)
        draw.rounded_rectangle((x, height - 36, x + chip_width, height - 12), radius=8, fill=(5, 18, 32, 220), outline=(0, 255, 102, 130), width=1)
        draw.text((x + 10, height - 29), text, fill=(230, 255, 246, 255), font=font)
        x += chip_width + 8

    draw.text((width - 168, height - 29), f"boxes {len(detections)}", fill=(142, 212, 255, 255), font=font)
    return Image.alpha_composite(image, overlay).convert("RGB")


def analyze_frame(frame_bgr, camera, use_demo, bucket):
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    if use_demo:
        random.seed(f"{camera['id']}:{bucket}")

    detections, counts, metadata = detect_people_and_count_zones(
        frame_rgb,
        camera["zone_camera_id"],
        return_metadata=True,
        force_demo=use_demo,
    )
    return {
        "detections": detections,
        "counts": counts,
        "zone_scale": metadata["zone_scale"],
    }


def render_frame(frame_bgr, camera, frame_index, fps, analysis, use_demo):
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    analysis_image, current_zone_scale = resize_for_analysis(frame_rgb)
    detections = analysis["detections"]
    counts = analysis["counts"]
    zone_scale = analysis.get("zone_scale", current_zone_scale)

    annotated = Image.fromarray(analysis_image)
    annotated = draw_annotations(annotated, detections, camera["zone_camera_id"], zone_scale)
    annotated = draw_demo_overlay(
        annotated,
        camera,
        counts,
        detections,
        frame_index / fps if fps else 0,
        "PREPROCESSED AI FEED" if use_demo else "YOLO PREPROCESSED FEED",
    )
    return cv2.cvtColor(np.array(annotated), cv2.COLOR_RGB2BGR)


def annotate_frame(frame_bgr, camera, frame_index, fps, detection_hold_frames, use_demo, cached_analysis=None):
    bucket = frame_index // max(1, detection_hold_frames)
    analysis = cached_analysis or analyze_frame(frame_bgr, camera, use_demo, bucket)
    return render_frame(frame_bgr, camera, frame_index, fps, analysis, use_demo), analysis

def transcode_to_h264(ffmpeg_path, temp_video, output_video, crf):
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(temp_video),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        str(output_video),
    ]
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def generate_camera_video(camera, source_root, output_root, args, ffmpeg_path):
    folder_name = camera.get("folder_name") or Path(camera.get("folder", "")).name
    source_video = find_first_video(source_root / folder_name)
    if not source_video:
        print(f"SKIP {camera['id']}: no source video in {source_root / folder_name}")
        return False

    output_folder = output_root / folder_name
    output_folder.mkdir(parents=True, exist_ok=True)
    output_video = output_folder / f"{source_video.stem}_preprocessed.mp4"

    if output_video.exists() and not args.force:
        print(f"OK {camera['id']}: exists {output_video.relative_to(output_root)} ({format_size(output_video.stat().st_size)})")
        return True

    cap = cv2.VideoCapture(str(source_video))
    if not cap.isOpened():
        print(f"FAIL {camera['id']}: could not open {source_video}")
        return False

    fps = safe_fps(cap)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    max_frames = frame_count if frame_count > 0 else int(fps * max(1, args.max_seconds))
    if args.max_seconds and args.max_seconds > 0:
        max_frames = min(max_frames, int(fps * args.max_seconds))
    detection_hold_frames = max(1, int(fps / max(1, args.detections_fps)))
    use_demo = not args.real_yolo

    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        print(f"FAIL {camera['id']}: empty source video {source_video}")
        return False

    processed, cached_analysis = annotate_frame(frame, camera, 0, fps, detection_hold_frames, use_demo)
    height, width = processed.shape[:2]
    temp_video = output_folder / f".{source_video.stem}_preprocessed_tmp.avi"
    writer = cv2.VideoWriter(str(temp_video), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        print(f"FAIL {camera['id']}: could not open temp writer {temp_video}")
        return False

    start = time.perf_counter()
    writer.write(processed)
    processed_frames = 1
    inference_frames = 1

    while processed_frames < max_frames:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        if processed_frames % detection_hold_frames == 0:
            cached_analysis = analyze_frame(frame, camera, use_demo, processed_frames // detection_hold_frames)
            inference_frames += 1
        processed = render_frame(frame, camera, processed_frames, fps, cached_analysis, use_demo)
        writer.write(processed)
        processed_frames += 1
        if processed_frames % 250 == 0:
            print(f"  {camera['id']}: {processed_frames}/{max_frames} frames, {inference_frames} inference frames")

    cap.release()
    writer.release()

    result = transcode_to_h264(ffmpeg_path, temp_video, output_video, args.crf)
    try:
        temp_video.unlink(missing_ok=True)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"FAIL {camera['id']}: ffmpeg failed: {result.stderr[-900:]}")
        return False

    elapsed = time.perf_counter() - start
    source_size = source_video.stat().st_size
    output_size = output_video.stat().st_size
    print(f"OK {camera['id']}")
    print(f"  source: {source_video.relative_to(source_root)} ({format_size(source_size)})")
    print(f"  output: {output_video.relative_to(output_root)} ({format_size(output_size)})")
    print(f"  frames: {processed_frames}, inference_frames: {inference_frames}, fps: {fps:.2f}, elapsed: {elapsed:.1f}s")
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate smooth preprocessed AI camera videos.")
    parser.add_argument("--source", default="test_assets/cameras_deploy", help="Camera video root to read from.")
    parser.add_argument("--output", default="test_assets/cameras_preprocessed", help="Processed video root to write to.")
    parser.add_argument("--max-seconds", type=float, default=0, help="Maximum duration per video. 0 means full source video.")
    parser.add_argument("--detections-fps", type=int, default=8, help="How often detections refresh inside the rendered video.")
    parser.add_argument("--crf", type=int, default=28, help="H.264 quality for processed MP4s.")
    parser.add_argument("--real-yolo", action="store_true", help="Use real YOLO instead of fast deterministic demo annotations.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing processed videos.")
    args = parser.parse_args()

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("ffmpeg was not found on PATH. Install ffmpeg and rerun this script.")
        return 1

    source_root = resolve_path(args.source)
    output_root = resolve_path(args.output)
    if not source_root.exists():
        print(f"Source folder not found: {source_root}")
        return 1
    if source_root.resolve() == output_root.resolve():
        print("Refusing to write preprocessed videos into the source folder.")
        return 1

    output_root.mkdir(parents=True, exist_ok=True)
    cameras = load_cameras()
    print(f"Source: {source_root}")
    print(f"Output: {output_root}")
    print(f"Mode: {'real-yolo' if args.real_yolo else 'fast-demo'}, crf={args.crf}, detections_fps={args.detections_fps}")
    print()

    ok_count = 0
    for camera in cameras:
        if generate_camera_video(camera, source_root, output_root, args, ffmpeg_path):
            ok_count += 1

    total_size = sum(path.stat().st_size for path in output_root.rglob("*.mp4"))
    print()
    print(f"Processed videos available: {ok_count}/{len(cameras)}")
    print(f"Preprocessed total size: {format_size(total_size)}")
    return 0 if ok_count == len(cameras) else 1


if __name__ == "__main__":
    raise SystemExit(main())