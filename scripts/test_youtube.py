#!/usr/bin/env python3
"""Unit tests for qiaomu-youtube-download."""

from __future__ import annotations

SCRIPT_INTERFACE = "internal-module"

import importlib.util
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("youtube.py")
SPEC = importlib.util.spec_from_file_location("qiaomu_youtube_download", MODULE_PATH)
assert SPEC and SPEC.loader
youtube = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(youtube)


class YoutubeSkillTests(unittest.TestCase):
    def test_version_key_handles_stable_and_patch_releases(self) -> None:
        self.assertLess(youtube.version_key("2026.7.4"), youtube.version_key("2026.07.23"))
        self.assertGreater(youtube.version_key("2026.07.23.1"), youtube.version_key("2026.07.23"))

    def test_url_validation_rejects_lookalike_domain(self) -> None:
        with self.assertRaises(youtube.SkillError):
            youtube.normalize_youtube_url("https://youtube.com.example/shorts/e7aThXxCbMM")

    def test_cookie_arguments_can_be_removed_for_fallback(self) -> None:
        command = ["yt-dlp", "--cookies-from-browser", "chrome", "--no-playlist", "URL"]
        self.assertEqual(
            youtube.without_cookie_args(command),
            ["yt-dlp", "--no-playlist", "URL"],
        )

    def test_matching_files_excludes_format_fragments_and_wrong_output_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_id = "EXAMPLE1234"
            final_video = root / f"Title [{video_id}].mp4"
            video_fragment = root / f"Title [{video_id}].f399.mp4"
            audio_fragment = root / f"Title [{video_id}].f140-7.m4a"
            final_audio = root / f"Title [{video_id}].mp3"
            partial = root / f"Title [{video_id}].mp4.part"
            for path in (final_video, video_fragment, audio_fragment, final_audio, partial):
                path.write_bytes(b"fixture")
            self.assertEqual(
                youtube.matching_files(root, video_id, youtube.VIDEO_OUTPUT_SUFFIXES),
                [final_video],
            )
            self.assertEqual(
                youtube.matching_files(root, video_id, youtube.AUDIO_OUTPUT_SUFFIXES),
                [final_audio],
            )

    def test_cleanup_removes_only_new_format_fragments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_id = "EXAMPLE1234"
            old_fragment = root / f"Title [{video_id}].f140.m4a"
            new_fragment = root / f"Title [{video_id}].f140-7.m4a"
            final_video = root / f"Title [{video_id}].mp4"
            for path in (old_fragment, new_fragment, final_video):
                path.write_bytes(b"fixture")
            removed = youtube.cleanup_new_format_fragments(root, video_id, {old_fragment.resolve()})
            self.assertEqual(removed, [str(new_fragment.resolve())])
            self.assertTrue(old_fragment.exists())
            self.assertFalse(new_fragment.exists())
            self.assertTrue(final_video.exists())

    @unittest.skipUnless(sys.platform != "win32", "POSIX lock inheritance is tested here")
    def test_download_lock_rejects_duplicate_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            holder_code = (
                "import importlib.util,pathlib,sys,time;"
                "s=importlib.util.spec_from_file_location('yt',sys.argv[1]);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "c=m.download_lock(pathlib.Path(sys.argv[2]),'EXAMPLE1234','video');"
                "c.__enter__();print('locked',flush=True);time.sleep(30)"
            )
            holder = subprocess.Popen(
                [sys.executable, "-c", holder_code, str(MODULE_PATH), temp_dir],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                assert holder.stdout is not None
                self.assertEqual(holder.stdout.readline().strip(), "locked")
                with self.assertRaises(youtube.SkillError):
                    with youtube.download_lock(Path(temp_dir), "EXAMPLE1234", "video"):
                        pass
            finally:
                holder.terminate()
                holder.wait(timeout=5)
                if holder.stdout is not None:
                    holder.stdout.close()

    @unittest.skipUnless(sys.platform != "win32", "POSIX inherited lock is tested here")
    def test_download_lock_survives_wrapper_exit_while_child_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            holder_code = (
                "import importlib.util,os,pathlib,subprocess,sys;"
                "s=importlib.util.spec_from_file_location('yt',sys.argv[1]);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "c=m.download_lock(pathlib.Path(sys.argv[2]),'EXAMPLE1234','video');"
                "h=c.__enter__();"
                "g=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],pass_fds=(h.fileno(),));"
                "print(g.pid,flush=True);os._exit(0)"
            )
            holder = subprocess.Popen(
                [sys.executable, "-c", holder_code, str(MODULE_PATH), temp_dir],
                stdout=subprocess.PIPE,
                text=True,
            )
            assert holder.stdout is not None
            child_pid = int(holder.stdout.readline().strip())
            holder.wait(timeout=5)
            holder.stdout.close()
            try:
                with self.assertRaises(youtube.SkillError):
                    with youtube.download_lock(Path(temp_dir), "EXAMPLE1234", "video"):
                        pass
            finally:
                os.kill(child_pid, signal.SIGTERM)
            for _attempt in range(50):
                try:
                    with youtube.download_lock(Path(temp_dir), "EXAMPLE1234", "video"):
                        break
                except youtube.SkillError:
                    time.sleep(0.02)
            else:
                self.fail("inherited download lock was not released after child exit")

    def test_streaming_command_returns_progress_output(self) -> None:
        completed = youtube.run_command(
            [sys.executable, "-c", "print('progress-line', flush=True)"],
            "download",
            5,
            stream=True,
        )
        self.assertIn("progress-line", completed.stdout)

    def test_streaming_command_terminates_on_timeout(self) -> None:
        with self.assertRaises(youtube.SkillError):
            youtube.run_command(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                "download",
                1,
                stream=True,
            )

    @patch.object(youtube, "optional_tool_version", return_value="available")
    @patch.object(youtube, "upgrade_ytdlp")
    @patch.object(youtube, "detect_ytdlp_manager", return_value=("homebrew", ["brew", "upgrade", "yt-dlp"]))
    @patch.object(youtube, "latest_ytdlp_version", return_value="2026.07.23")
    @patch.object(youtube, "executable_version", side_effect=["2026.07.04", "2026.07.23"])
    @patch.object(youtube, "require_tool", return_value="/opt/homebrew/bin/yt-dlp")
    def test_doctor_upgrades_only_when_outdated(
        self,
        _require_tool,
        _executable_version,
        _latest_version,
        _detect_manager,
        upgrade_ytdlp,
        _optional_version,
    ) -> None:
        result = youtube.doctor(upgrade=True, timeout=30)
        upgrade_ytdlp.assert_called_once_with(["brew", "upgrade", "yt-dlp"], "homebrew", 30)
        self.assertTrue(result["yt_dlp"]["upgraded"])
        self.assertFalse(result["yt_dlp"]["outdated"])
        self.assertEqual(result["yt_dlp"]["installed_version"], "2026.07.23")


if __name__ == "__main__":
    unittest.main(verbosity=2)
