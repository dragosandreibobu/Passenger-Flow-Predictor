import argparse
import shutil
import subprocess
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def resolve_path(raw_path):
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    path = Path(raw_path)

    if path.is_absolute():
        return path

    candidates = [
        Path.cwd() / path,
        script_dir / path,
        project_root / path,
    ]

    parts = path.parts
    if parts and parts[0].lower() == "backend":
        candidates.append(script_dir / Path(*parts[1:]))

    if parts and parts[0] == "test_assets":
        candidates.append(script_dir / path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if parts and parts[0].lower() == "backend":
        return script_dir / Path(*parts[1:])
    if parts and parts[0] == "test_assets":
        return script_dir / path
    return Path.cwd() / path


def format_size(num_bytes):
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def find_first_video(folder):
    files = sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)
    return files[0] if files else None


def build_ffmpeg_command(ffmpeg_path, source, output, max_seconds, speed, width, crf, use_speed=True):
    # Use -1 instead of -2 for compatibility with older ffmpeg builds.
    filters = [f"scale={width}:-1"]
    if use_speed and speed and speed > 1:
        filters.append(f"setpts={1 / speed:.6f}*PTS")

    return [
        ffmpeg_path,
        "-y",
        "-i",
        str(source),
        "-t",
        str(max_seconds),
        "-vf",
        ",".join(filters),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        str(output),
    ]


def run_ffmpeg(command):
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def compress_video(ffmpeg_path, source, output, args):
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(
        ffmpeg_path,
        source,
        output,
        args.max_seconds,
        args.speed,
        args.width,
        args.crf,
        use_speed=True,
    )
    result = run_ffmpeg(command)
    if result.returncode == 0:
        return True, "speed"

    if args.speed and args.speed > 1:
        fallback = build_ffmpeg_command(
            ffmpeg_path,
            source,
            output,
            args.max_seconds,
            args.speed,
            args.width,
            args.crf,
            use_speed=False,
        )
        fallback_result = run_ffmpeg(fallback)
        if fallback_result.returncode == 0:
            return True, "no-speed-fallback"
        return False, fallback_result.stderr.strip()[-1200:]

    return False, result.stderr.strip()[-1200:]


def collect_camera_folders(source_root):
    return sorted(folder for folder in source_root.iterdir() if folder.is_dir())


def main():
    parser = argparse.ArgumentParser(description="Create compressed deployment copies of local camera videos.")
    parser.add_argument("--max-seconds", type=int, default=45, help="Maximum source duration to include per video.")
    parser.add_argument("--speed", type=float, default=2, help="Playback speed-up factor. Use 1 to disable.")
    parser.add_argument("--width", type=int, default=960, help="Maximum output width.")
    parser.add_argument("--crf", type=int, default=30, help="H.264 CRF quality value.")
    parser.add_argument("--source", default="test_assets/cameras", help="Original camera video root.")
    parser.add_argument("--output", default="test_assets/cameras_deploy", help="Compressed deployment video root.")
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
        print("Refusing to write deploy videos into the original source folder.")
        return 1

    print(f"Source: {source_root}")
    print(f"Output: {output_root}")
    print(f"Settings: max_seconds={args.max_seconds}, speed={args.speed}x, width={args.width}, crf={args.crf}")
    print()

    total_original = 0
    total_deploy = 0
    processed = 0

    for folder in collect_camera_folders(source_root):
        source_video = find_first_video(folder)
        relative_folder = folder.relative_to(source_root)
        output_folder = output_root / relative_folder

        if not source_video:
            print(f"SKIP {relative_folder}: no video file found")
            continue

        output_video = output_folder / f"{source_video.stem}_deploy.mp4"
        ok, mode = compress_video(ffmpeg_path, source_video, output_video, args)
        if not ok:
            print(f"FAIL {relative_folder}: {mode}")
            continue

        original_size = source_video.stat().st_size
        deploy_size = output_video.stat().st_size
        reduction = 100 - ((deploy_size / original_size) * 100) if original_size else 0

        total_original += original_size
        total_deploy += deploy_size
        processed += 1

        print(f"OK {relative_folder}")
        print(f"  input : {source_video.name} ({format_size(original_size)})")
        print(f"  output: {output_video.name} ({format_size(deploy_size)})")
        print(f"  reduction: {reduction:.1f}% ({mode})")

    print()
    print(f"Processed videos: {processed}")
    print(f"Original total: {format_size(total_original)}")
    print(f"Deploy total: {format_size(total_deploy)}")
    if total_original:
        print(f"Total reduction: {100 - ((total_deploy / total_original) * 100):.1f}%")

    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
