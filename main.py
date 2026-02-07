import argparse
import shutil
import subprocess
from pathlib import Path


def ensure_tools():
    missing = []
    for name in ("ffmpeg", "ffprobe"):
        if shutil.which(name) is None:
            missing.append(name)
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(f"Missing tools: {missing_list}. Install ffmpeg and try again.")


def has_video_stream(path):
    if not path.is_file() or path.name.startswith("."):
        return False
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "video"


def pick_input_path(video_dir, user_input):
    if user_input:
        if not user_input.exists():
            raise SystemExit(f"Input file not found: {user_input}")
        if not has_video_stream(user_input):
            raise SystemExit(f"Input is not a video file: {user_input}")
        print(f"Using input file: {user_input}")
        return user_input

    if not video_dir.exists():
        raise SystemExit(f"Missing folder: {video_dir}")
    print(f"Scanning for video files in: {video_dir}")
    for path in sorted(video_dir.iterdir()):
        if has_video_stream(path):
            print(f"Selected input file: {path}")
            return path
    raise SystemExit(f"No video files found in: {video_dir}")


def convert(input_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vn"]
    if output_path.suffix.lower() == ".mp3":
        cmd += ["-q:a", "2"]
    cmd.append(str(output_path))
    print("Running ffmpeg...")
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

    ensure_tools()
    input_path = pick_input_path(video_dir, args.input)
    ext = args.ext.lstrip(".")
    output_path = audio_dir / f"{input_path.stem}.{ext}"

    print(f"Saving audio to: {output_path}")
    convert(input_path, output_path)
    print(f"Saved audio to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
