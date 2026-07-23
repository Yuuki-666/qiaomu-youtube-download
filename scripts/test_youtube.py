#!/usr/bin/env python3
"""Unit tests for qiaomu-youtube-download."""

from __future__ import annotations

SCRIPT_INTERFACE = "internal-module"

import importlib.util
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
