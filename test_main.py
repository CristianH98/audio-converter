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

    def test_find_first_video_skips_hidden_and_non_video_in_sorted_order(self):
        self.touch(".a.mp4")
        self.touch("b.txt")
        wanted = self.touch("c.mp4")
        self.touch("d.mp4")
        with mock.patch("main.has_video_stream", side_effect=lambda p: p.suffix == ".mp4"):
            self.assertEqual(main.find_first_video(self.dir), wanted)


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


if __name__ == "__main__":
    unittest.main()
