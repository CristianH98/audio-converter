import argparse
import shutil
import subprocess
from pathlib import Path


def require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found on PATH. Install ffmpeg and try again.")


def default_video_file(video_dir):
    if not video_dir.exists():
        raise SystemExit(f"Missing folder: {video_dir}")
    files = sorted(p for p in video_dir.iterdir() if p.is_file())
    if not files:
        raise SystemExit(f"No video files found in: {video_dir}")
    return files[0]


def output_path_for(input_path, audio_dir, ext):
    if not ext.startswith("."):
        ext = f".{ext}"
    return audio_dir / f"{input_path.stem}{ext}"


def convert(input_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a video file in ./video to an audio file in ./audio."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Path to the input video file (defaults to the first file in ./video).",
    )
    parser.add_argument(
        "--ext",
        "-e",
        default="mp3",
        help="Audio extension to use (default: mp3).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    video_dir = project_root / "video"
    audio_dir = project_root / "audio"

    input_path = args.input if args.input else default_video_file(video_dir)
    output_path = output_path_for(input_path, audio_dir, args.ext)

    require_ffmpeg()
    convert(input_path, output_path)
    print(f"Saved audio to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
