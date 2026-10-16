# Audio converter

Turn a video into an audio file with one command.

## The problem

iPhone ringtones and alarms have to be audio files, but the sound you want is often inside a video: a screen recording, a clip from your camera roll, a downloaded video. Extracting it by hand means remembering ffmpeg flags every time. This script does it for you: drop the video in a folder, run one command, and get an MP3.

## Quick start

Requires Python 3 and [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg` on macOS). No Python packages are needed.

```bash
cp ~/Movies/clip.mp4 video/
python3 main.py
```

The audio is saved as `audio/clip.mp3`.

To pick a file from anywhere and choose another format:

```bash
python3 main.py --input ~/Movies/clip.mov --ext m4a
```

| Option | Default | Description |
|---|---|---|
| `-i`, `--input PATH` | First video in `video/` | The video to convert. |
| `-e`, `--ext EXT` | `mp3` | The output format. |

## How it works

1. Checks that `ffmpeg` and `ffprobe` are installed.
2. Finds the input video. Without `--input`, it takes the first file in `video/` that `ffprobe` confirms is a real video, so images, audio files with cover art, and hidden files are skipped.
3. Runs `ffmpeg -vn` to drop the video stream and saves the audio to `audio/`.

Every failure, such as a missing tool, a missing file, or an ffmpeg error, prints one clear message and exits with code 1.

## Tests

```bash
python3 -m unittest discover -v
```

The tests mock ffmpeg and ffprobe, so they run without ffmpeg or media files. GitHub Actions runs them on every pull request and on every push to `main`. Pull requests also get an automated Claude code review, configured in [REVIEW.md](REVIEW.md).
