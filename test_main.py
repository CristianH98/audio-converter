import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class OutputPathTest(unittest.TestCase):
    def test_uses_input_stem_and_ext(self):
        path = main.output_path_for(Path("video/clip.mp4"), Path("audio"), "m4a")
        self.assertEqual(path, Path("audio/clip.m4a"))

    def test_strips_leading_dot_from_ext(self):
        path = main.output_path_for(Path("clip.mp4"), Path("audio"), ".mp3")
        self.assertEqual(path, Path("audio/clip.mp3"))

    def test_rejects_ext_with_path_separator(self):
        for ext in ("mp3/../../x", "..\\x"):
            with self.subTest(ext=ext):
                with self.assertRaisesRegex(main.ConversionError, "Invalid audio extension"):
                    main.output_path_for(Path("clip.mp4"), Path("audio"), ext)

    def test_rejects_empty_ext(self):
        for ext in ("", "."):
            with self.subTest(ext=ext):
                with self.assertRaisesRegex(main.ConversionError, "Invalid audio extension"):
                    main.output_path_for(Path("clip.mp4"), Path("audio"), ext)


class BuildCommandTest(unittest.TestCase):
    def test_mp3_adds_quality_flag(self):
        cmd = main.build_ffmpeg_command(Path("in.mp4"), Path("out.mp3"))
        self.assertEqual(cmd, ["ffmpeg", "-y", "-i", "in.mp4", "-vn", "-q:a", "2", "out.mp3"])

    def test_mp3_match_is_case_insensitive(self):
        cmd = main.build_ffmpeg_command(Path("in.mp4"), Path("out.MP3"))
        self.assertIn("-q:a", cmd)

    def test_other_formats_have_no_extra_flags(self):
        cmd = main.build_ffmpeg_command(Path("in.mp4"), Path("out.wav"))
        self.assertEqual(cmd, ["ffmpeg", "-y", "-i", "in.mp4", "-vn", "out.wav"])


class EnsureToolsTest(unittest.TestCase):
    def test_reports_missing_tools(self):
        with mock.patch("main.shutil.which", return_value=None):
            with self.assertRaisesRegex(main.ConversionError, "ffmpeg, ffprobe"):
                main.ensure_tools()

    def test_passes_when_all_present(self):
        with mock.patch("main.shutil.which", return_value="/usr/bin/tool"):
            main.ensure_tools()


class InputSelectionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def touch(self, name):
        path = self.dir / name
        path.write_bytes(b"")
        return path

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


class ConvertTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.output = Path(tmp.name) / "audio" / "clip.mp3"

    def test_creates_output_dir_and_runs_ffmpeg(self):
        with mock.patch("main.subprocess.run") as run:
            main.convert(Path("clip.mp4"), self.output)
        self.assertTrue(self.output.parent.is_dir())
        run.assert_called_once_with(
            main.build_ffmpeg_command(Path("clip.mp4"), self.output), check=True
        )

    def test_ffmpeg_failure_becomes_conversion_error(self):
        failure = main.subprocess.CalledProcessError(1, ["ffmpeg"])
        with mock.patch("main.subprocess.run", side_effect=failure):
            with self.assertRaisesRegex(main.ConversionError, r"ffmpeg failed \(exit code 1\)"):
                main.convert(Path("clip.mp4"), self.output)


class MainTest(unittest.TestCase):
    def test_conversion_error_becomes_exit_message(self):
        with mock.patch("main.shutil.which", return_value=None):
            with self.assertRaises(SystemExit) as ctx:
                main.main([])
        self.assertIn("Missing tools", str(ctx.exception.code))

    def test_default_ext_is_mp3(self):
        self.assertEqual(main.parse_args([]).ext, "mp3")

    def test_explicit_input_is_converted(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "clip.mp4"
            clip.write_bytes(b"")
            with (
                mock.patch("main.shutil.which", return_value="/usr/bin/tool"),
                mock.patch("main.has_video_stream", return_value=True),
                mock.patch("main.convert") as convert,
            ):
                self.assertEqual(main.main(["-i", str(clip), "-e", "wav"]), 0)
        convert.assert_called_once_with(clip, main.AUDIO_DIR / "clip.wav")

    def test_default_input_comes_from_video_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_dir = Path(tmp) / "video"
            audio_dir = Path(tmp) / "audio"
            video_dir.mkdir()
            clip = video_dir / "clip.mp4"
            clip.write_bytes(b"")
            with (
                mock.patch("main.shutil.which", return_value="/usr/bin/tool"),
                mock.patch("main.has_video_stream", return_value=True),
                mock.patch("main.VIDEO_DIR", video_dir),
                mock.patch("main.AUDIO_DIR", audio_dir),
                mock.patch("main.convert") as convert,
            ):
                self.assertEqual(main.main([]), 0)
        convert.assert_called_once_with(clip, audio_dir / "clip.mp3")

    def test_ffmpeg_failure_exits_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "clip.mp4"
            clip.write_bytes(b"")
            failure = main.subprocess.CalledProcessError(1, ["ffmpeg"])
            with (
                mock.patch("main.shutil.which", return_value="/usr/bin/tool"),
                mock.patch("main.has_video_stream", return_value=True),
                mock.patch("main.AUDIO_DIR", Path(tmp) / "audio"),
                mock.patch("main.subprocess.run", side_effect=failure),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    main.main(["-i", str(clip)])
        self.assertIn("ffmpeg failed (exit code 1)", str(ctx.exception.code))


if __name__ == "__main__":
    unittest.main()
