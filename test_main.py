import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def touch(self, name):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        return path


class OutputPathTest(unittest.TestCase):
    def test_valid_extensions(self):
        cases = {
            "mp3": "audio/clip.mp3",
            ".mp3": "audio/clip.mp3",
            "m4a": "audio/clip.m4a",
            "wav": "audio/clip.wav",
        }
        for ext, expected in cases.items():
            with self.subTest(ext=ext):
                path = main.output_path_for(Path("video/clip.mp4"), Path("audio"), ext)
                self.assertEqual(path, Path(expected))

    def test_invalid_extensions(self):
        for ext in ("", ".", "mp3/../../x", "..\\x"):
            with self.subTest(ext=ext):
                with self.assertRaisesRegex(main.ConversionError, "Invalid audio extension"):
                    main.output_path_for(Path("clip.mp4"), Path("audio"), ext)


class BuildCommandTest(unittest.TestCase):
    def test_extra_args_per_format(self):
        cases = {
            "out.mp3": ["-q:a", "2"],
            "out.MP3": ["-q:a", "2"],
            "out.m4a": [],
            "out.wav": [],
            "out.flac": [],
        }
        for name, extra in cases.items():
            with self.subTest(output=name):
                cmd = main.build_ffmpeg_command(Path("in.mp4"), Path(name))
                self.assertEqual(cmd, ["ffmpeg", "-y", "-i", "in.mp4", "-vn", *extra, name])


class EnsureToolsTest(unittest.TestCase):
    def test_reports_missing_tools(self):
        with mock.patch("main.shutil.which", return_value=None):
            with self.assertRaisesRegex(main.ConversionError, "ffmpeg, ffprobe"):
                main.ensure_tools()

    def test_passes_when_all_present(self):
        with mock.patch("main.shutil.which", return_value="/usr/bin/tool"):
            main.ensure_tools()


def probe(format_name, codec_type="video", attached_pic=0):
    """ffprobe's JSON output for a file whose first video stream has these properties."""
    streams = []
    if codec_type:
        streams.append({"codec_type": codec_type, "disposition": {"attached_pic": attached_pic}})
    return {"streams": streams, "format": {"format_name": format_name}}


class HasVideoStreamTest(unittest.TestCase):
    def test_real_video_detection(self):
        # Shapes taken from real ffprobe output for each kind of file.
        cases = {
            "mp4 video": (probe("mov,mp4,m4a,3gp,3g2,mj2"), True),
            "animated gif": (probe("gif"), True),
            "png image": (probe("png_pipe"), False),
            "jpeg image": (probe("image2"), False),
            "mp3 with cover art": (probe("mp3", attached_pic=1), False),
            "mp3 without cover art": (probe("mp3", codec_type=None), False),
        }
        for name, (output, expected) in cases.items():
            with self.subTest(file=name):
                result = subprocess.CompletedProcess([], 0, stdout=json.dumps(output))
                with mock.patch("main.subprocess.run", return_value=result):
                    self.assertIs(main.has_video_stream(Path("file")), expected)

    def test_ffprobe_failure_is_not_video(self):
        result = subprocess.CompletedProcess([], 1, stdout="")
        with mock.patch("main.subprocess.run", return_value=result):
            self.assertFalse(main.has_video_stream(Path("broken.mp4")))

    def test_unreadable_output_is_not_video(self):
        result = subprocess.CompletedProcess([], 0, stdout="not json")
        with mock.patch("main.subprocess.run", return_value=result):
            self.assertFalse(main.has_video_stream(Path("odd.mp4")))


class InputSelectionTest(TempDirTestCase):
    def test_validate_input_missing_file(self):
        with self.assertRaisesRegex(main.ConversionError, "Input file not found"):
            main.validate_input(self.dir / "nope.mp4")

    def test_validate_input_rejects_directory(self):
        with self.assertRaisesRegex(main.ConversionError, "not a video file"):
            main.validate_input(self.dir)

    def test_validate_input_rejects_non_video(self):
        path = self.touch("note.txt")
        with mock.patch("main.has_video_stream", return_value=False):
            with self.assertRaisesRegex(main.ConversionError, "not a video file"):
                main.validate_input(path)

    def test_validate_input_rejects_hidden_file(self):
        path = self.touch(".hidden.mp4")
        with mock.patch("main.has_video_stream", return_value=True):
            with self.assertRaisesRegex(main.ConversionError, "not a video file"):
                main.validate_input(path)

    def test_validate_input_accepts_video(self):
        path = self.touch("clip.mp4")
        with mock.patch("main.has_video_stream", return_value=True):
            self.assertEqual(main.validate_input(path), path)

    def test_find_first_video_missing_folder(self):
        with self.assertRaisesRegex(main.ConversionError, "Missing folder"):
            main.find_first_video(self.dir / "missing")

    def test_find_first_video_empty_folder(self):
        with self.assertRaisesRegex(main.ConversionError, "No video files found"):
            main.find_first_video(self.dir)

    def test_find_first_video_rejects_a_file(self):
        with self.assertRaisesRegex(main.ConversionError, "Missing folder"):
            main.find_first_video(self.touch("video"))

    def test_find_first_video_skips_hidden_and_non_video_in_sorted_order(self):
        self.touch(".a.mp4")
        self.touch("b.txt")
        wanted = self.touch("c.mp4")
        self.touch("d.mp4")
        with mock.patch("main.has_video_stream", side_effect=lambda p: p.suffix == ".mp4"):
            self.assertEqual(main.find_first_video(self.dir), wanted)


class ConvertTest(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.output = self.dir / "audio" / "clip.mp3"

    def test_creates_output_dir_and_runs_ffmpeg(self):
        with mock.patch("main.subprocess.run") as run:
            main.convert(Path("clip.mp4"), self.output)
        self.assertTrue(self.output.parent.is_dir())
        run.assert_called_once_with(
            main.build_ffmpeg_command(Path("clip.mp4"), self.output), check=True
        )

    def test_ffmpeg_failure_becomes_conversion_error(self):
        failure = subprocess.CalledProcessError(1, ["ffmpeg"])
        with mock.patch("main.subprocess.run", side_effect=failure):
            with self.assertRaisesRegex(main.ConversionError, r"ffmpeg failed \(exit code 1\)"):
                main.convert(Path("clip.mp4"), self.output)


class MainTest(TempDirTestCase):
    """End-to-end runs of main() with the tools present and every file treated as video."""

    def setUp(self):
        super().setUp()
        self.video_dir = self.dir / "video"
        self.audio_dir = self.dir / "audio"
        self.video_dir.mkdir()
        for patcher in (
            mock.patch("main.shutil.which", return_value="/usr/bin/tool"),
            mock.patch("main.has_video_stream", return_value=True),
            mock.patch("main.VIDEO_DIR", self.video_dir),
            mock.patch("main.AUDIO_DIR", self.audio_dir),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_default_ext_is_mp3(self):
        self.assertEqual(main.parse_args([]).ext, "mp3")

    def test_default_input_comes_from_video_dir(self):
        clip = self.touch("video/clip.mp4")
        with mock.patch("main.convert") as convert:
            self.assertEqual(main.main([]), 0)
        convert.assert_called_once_with(clip, self.audio_dir / "clip.mp3")

    def test_explicit_input_is_converted(self):
        clip = self.touch("elsewhere/clip.mp4")
        with mock.patch("main.convert") as convert:
            self.assertEqual(main.main(["-i", str(clip), "-e", "wav"]), 0)
        convert.assert_called_once_with(clip, self.audio_dir / "clip.wav")

    def test_conversion_error_becomes_exit_message(self):
        with mock.patch("main.shutil.which", return_value=None):
            with self.assertRaises(SystemExit) as ctx:
                main.main([])
        self.assertIn("Missing tools", str(ctx.exception.code))

    def test_ffmpeg_failure_exits_with_message(self):
        clip = self.touch("video/clip.mp4")
        failure = subprocess.CalledProcessError(1, ["ffmpeg"])
        with mock.patch("main.subprocess.run", side_effect=failure):
            with self.assertRaises(SystemExit) as ctx:
                main.main(["-i", str(clip)])
        self.assertIn("ffmpeg failed (exit code 1)", str(ctx.exception.code))


if __name__ == "__main__":
    unittest.main()
