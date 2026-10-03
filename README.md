# Audio converter

A Python script that extracts the audio track from a video file with ffmpeg. It is handy for making custom iPhone ringtones and alarms from screen recordings or clips.

## Requirements

- Python 3.10 or newer.
- ffmpeg, which includes `ffprobe`. On macOS, install it with `brew install ffmpeg`. On Debian or Ubuntu, use `sudo apt install ffmpeg`.

The script has no Python dependencies outside the standard library.

## Convert a video

1. Copy the video into the `video/` folder.
2. Run the script:

   ```bash
   python3 main.py
   ```

The script picks the first video in `video/`, sorted by file name. It skips hidden files and any file that `ffprobe` doesn't recognize as video. The audio is saved to `audio/` with the same name as the video, for example `video/clip.mp4` becomes `audio/clip.mp3`. An existing file with that name is overwritten.

Git ignores the contents of `video/` and `audio/`, so your media files are never committed.

## Options

| Option | Default | Description |
|---|---|---|
| `--input PATH`, `-i PATH` | First video in `video/` | Convert this file instead. It can be anywhere on disk. |
| `--ext EXT`, `-e EXT` | `mp3` | Output format, as a file extension. ffmpeg picks the codec from it. |

MP3 output uses ffmpeg's variable bitrate quality setting `-q:a 2`. Other formats use ffmpeg's defaults for that format.

To convert a specific file to M4A:

```bash
python3 main.py -i ~/Movies/clip.mov -e m4a
```

## Errors

If something goes wrong, the script prints one of these messages and exits with code 1:

| Message | Cause |
|---|---|
| `Missing tools: NAMES. Install ffmpeg and try again.` | `ffmpeg`, `ffprobe`, or both aren't installed or aren't on your `PATH`. |
| `Input file not found: PATH` | The `--input` path doesn't exist. |
| `Input is not a video file: PATH` | The `--input` file is hidden, is a folder, or has no video stream. |
| `Missing folder: PATH` | The `video/` folder doesn't exist. |
| `No video files found in: PATH` | `video/` has no video files. |
| `ffmpeg failed (exit code N) while converting PATH` | ffmpeg couldn't convert the file. Its own output above the message says why. |

## Run the tests

```bash
python3 -m unittest discover -v
```

The tests mock `ffmpeg` and `ffprobe`, so they need neither ffmpeg nor real media files. GitHub Actions runs them on every pull request and on every push to `main`.

## Pull requests

Every pull request gets an automatic review from Claude, posted as a comment with severe and minor issues and a verdict. Any severe issue fails the required `review` check, which blocks the merge. [REVIEW.md](REVIEW.md) defines what counts as severe and how the comment is formatted.
