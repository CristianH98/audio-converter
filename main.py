import argparse
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VIDEO_DIR = PROJECT_ROOT / "video"
AUDIO_DIR = PROJECT_ROOT / "audio"

REQUIRED_TOOLS = ("ffmpeg", "ffprobe")
DEFAULT_EXT = "mp3"

# Extra ffmpeg arguments per output extension (lowercase, no leading dot).
CODEC_ARGS = {
    "mp3": ["-q:a", "2"],
}


class ConversionError(Exception):
    """A user-facing failure; the message is shown as-is."""


def ensure_tools():
    missing = [name for name in REQUIRED_TOOLS if shutil.which(name) is None]
    if missing:
        missing_list = ", ".join(missing)
        raise ConversionError(f"Missing tools: {missing_list}. Install ffmpeg and try again.")


def is_candidate(path):
    """Whether the path is a regular, non-hidden file worth probing."""
    return path.is_file() and not path.name.startswith(".")


def has_video_stream(path):
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


def is_video_file(path):
    return is_candidate(path) and has_video_stream(path)


def validate_input(path):
    if not path.exists():
        raise ConversionError(f"Input file not found: {path}")
    if not is_video_file(path):
        raise ConversionError(f"Input is not a video file: {path}")
    return path


def find_first_video(video_dir):
    if not video_dir.exists():
        raise ConversionError(f"Missing folder: {video_dir}")
    print(f"Scanning for video files in: {video_dir}")
    for path in sorted(video_dir.iterdir()):
        if is_video_file(path):
            return path
    raise ConversionError(f"No video files found in: {video_dir}")


def output_path_for(input_path, audio_dir, ext):
    return audio_dir / f"{input_path.stem}.{ext.lstrip('.')}"


def build_ffmpeg_command(input_path, output_path):
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vn"]
    cmd += CODEC_ARGS.get(output_path.suffix.lower().lstrip("."), [])
    cmd.append(str(output_path))
    return cmd


def convert(input_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("Running ffmpeg...")
    try:
        subprocess.run(build_ffmpeg_command(input_path, output_path), check=True)
    except subprocess.CalledProcessError as err:
        raise ConversionError(
            f"ffmpeg failed (exit code {err.returncode}) while converting {input_path}"
        ) from err


def parse_args(argv=None):
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
        default=DEFAULT_EXT,
        help=f"Audio extension to use (default: {DEFAULT_EXT}).",
    )
    return parser.parse_args(argv)


def run(args):
    ensure_tools()
    if args.input:
        input_path = validate_input(args.input)
        print(f"Using input file: {input_path}")
    else:
        input_path = find_first_video(VIDEO_DIR)
        print(f"Selected input file: {input_path}")

    output_path = output_path_for(input_path, AUDIO_DIR, args.ext)
    print(f"Saving audio to: {output_path}")
    convert(input_path, output_path)
    print(f"Saved audio to: {output_path}")


def main(argv=None):
    args = parse_args(argv)
    try:
        run(args)
    except ConversionError as err:
        raise SystemExit(str(err))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
