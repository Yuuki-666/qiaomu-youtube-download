#!/usr/bin/env python3
"""Safe yt-dlp wrapper for qiaomu-youtube-download."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlsplit, urlunsplit


VERSION = "1.1.0"
ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4a", ".mp3", ".opus", ".ogg", ".wav"}
SUBTITLE_SUFFIXES = {".srt", ".vtt", ".ass", ".lrc", ".txt"}
DATA_API_BASE = "https://www.googleapis.com/youtube/v3"
YT_DLP_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YT_DLP_RELEASE_LATEST = "https://github.com/yt-dlp/yt-dlp/releases/latest"
BROWSER_APPLICATIONS = {
    "chrome": ("/Applications/Google Chrome.app", "~/Applications/Google Chrome.app"),
    "edge": ("/Applications/Microsoft Edge.app", "~/Applications/Microsoft Edge.app"),
    "firefox": ("/Applications/Firefox.app", "~/Applications/Firefox.app"),
    "safari": ("/Applications/Safari.app",),
}
QUALITY_FORMATS = {
    "best": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
    "1080p": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b[height<=720]",
    "480p": "bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/bv*[height<=480]+ba/b[height<=480]",
}


class SkillError(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SkillError("dependency", f"{name} not found")
    return path


def executable_version(executable: str) -> str:
    completed = run_command([executable, "--version"], "dependency", 30)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise SkillError("dependency", f"{Path(executable).name} returned no version")
    return lines[0]


def version_key(value: str) -> tuple[int, ...]:
    numbers = tuple(int(part) for part in re.findall(r"\d+", value))
    return numbers or (0,)


def latest_ytdlp_version(timeout: int) -> str:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"qiaomu-youtube-download/{VERSION}"}
    request = urllib.request.Request(YT_DLP_RELEASE_API, headers=headers)
    api_error: Exception | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        api_error = exc
        payload = {}
    latest = str(payload.get("tag_name") or "").lstrip("v")
    if not latest:
        redirect_request = urllib.request.Request(
            YT_DLP_RELEASE_LATEST,
            headers={"User-Agent": f"qiaomu-youtube-download/{VERSION}"},
        )
        try:
            with urllib.request.urlopen(redirect_request, timeout=timeout) as response:
                final_url = response.geturl()
            latest = urllib.parse.unquote(final_url.rstrip("/").rsplit("/", 1)[-1]).lstrip("v")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise SkillError(
                "update-check",
                f"could not read the official yt-dlp release (API: {api_error}; redirect: {exc})",
            ) from exc
    if not re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,2}(?:\.\d+)?", latest):
        raise SkillError("update-check", "official yt-dlp release returned an unexpected version")
    return latest


def detect_ytdlp_manager(yt_dlp: str) -> tuple[str, list[str]]:
    brew = shutil.which("brew")
    resolved = str(Path(yt_dlp).resolve())
    if brew:
        formula = subprocess.run(
            [brew, "--prefix", "yt-dlp"], check=False, capture_output=True, text=True, timeout=30
        )
        prefix = formula.stdout.strip()
        if formula.returncode == 0 and prefix and resolved.startswith(str(Path(prefix).resolve())):
            return "homebrew", [brew, "upgrade", "yt-dlp"]
    return "self-update", [yt_dlp, "-U"]


def upgrade_ytdlp(command: list[str], manager: str, timeout: int) -> None:
    env = dict(os.environ)
    if manager == "homebrew":
        env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillError("upgrade", f"yt-dlp upgrade timed out after {timeout}s") from exc
    if completed.returncode != 0:
        raise SkillError("upgrade", error_summary(completed))


def optional_tool_version(name: str) -> str | None:
    executable = shutil.which(name)
    if not executable:
        return None
    completed = subprocess.run(
        [executable, "-version"], check=False, capture_output=True, text=True, timeout=30
    )
    first_line = (completed.stdout or completed.stderr).splitlines()
    return first_line[0].strip() if completed.returncode == 0 and first_line else None


def doctor(upgrade: bool, timeout: int) -> dict[str, Any]:
    yt_dlp = require_tool("yt-dlp")
    installed = executable_version(yt_dlp)
    manager, upgrade_command = detect_ytdlp_manager(yt_dlp)
    warnings: list[str] = []
    try:
        latest = latest_ytdlp_version(min(timeout, 60))
    except SkillError as exc:
        latest = None
        warnings.append(str(exc))
    outdated = bool(latest and version_key(installed) < version_key(latest))
    upgraded = False
    if upgrade and outdated:
        upgrade_ytdlp(upgrade_command, manager, timeout)
        updated = executable_version(yt_dlp)
        if version_key(updated) <= version_key(installed):
            raise SkillError("upgrade", f"yt-dlp version did not advance ({installed} -> {updated})")
        installed = updated
        outdated = bool(latest and version_key(installed) < version_key(latest))
        upgraded = True
    return {
        "ok": True,
        "command": "doctor",
        "yt_dlp": {
            "executable": str(Path(yt_dlp).resolve()),
            "installed_version": installed,
            "latest_stable_version": latest,
            "outdated": outdated,
            "manager": manager,
            "upgrade_requested": upgrade,
            "upgraded": upgraded,
        },
        "ffmpeg_version": optional_tool_version("ffmpeg"),
        "ffprobe_version": optional_tool_version("ffprobe"),
        "warnings": warnings,
    }


def normalize_youtube_url(raw: str) -> str:
    value = raw.strip().strip("<>[](){}\"'")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https":
        raise SkillError("validate", "YouTube URL must use HTTPS")
    if parsed.username or parsed.password or parsed.port:
        raise SkillError("validate", "YouTube URL must not contain credentials or a custom port")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise SkillError("validate", f"unsupported host: {host or '(missing)'}")
    path = parsed.path.rstrip("/")
    valid = False
    if host == "youtu.be":
        valid = bool(re.fullmatch(r"/[A-Za-z0-9_-]{11}", path))
    elif path == "/watch":
        valid = bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", (parse_qs(parsed.query).get("v") or [""])[0]))
    else:
        valid = bool(re.fullmatch(r"/(?:shorts|live|embed)/[A-Za-z0-9_-]{11}", path))
    if not valid:
        raise SkillError("validate", "expected a single YouTube watch, Shorts, Live, embed, or youtu.be video URL")
    return urlunsplit(("https", host, parsed.path, parsed.query, ""))


def cookie_args(browser: str | None) -> list[str]:
    return ["--cookies-from-browser", browser] if browser else []


def without_cookie_args(command: list[str]) -> list[str]:
    output = list(command)
    try:
        index = output.index("--cookies-from-browser")
    except ValueError:
        return output
    del output[index:index + 2]
    return output


def detect_cookie_browser(mode: str) -> str | None:
    if mode == "none":
        return None
    if mode != "auto":
        return mode
    for browser in ("chrome", "edge", "firefox", "safari"):
        if any(Path(path).expanduser().exists() for path in BROWSER_APPLICATIONS[browser]):
            return browser
    return None


def error_summary(completed: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(part for part in (completed.stderr, completed.stdout) if part).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[-8:])[:1600] or f"yt-dlp exited with {completed.returncode}"


def run_command(args: list[str], stage: str, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SkillError(stage, f"command timed out after {timeout}s") from exc
    if completed.returncode != 0:
        raise SkillError(stage, error_summary(completed))
    return completed


def load_metadata_once(url: str, browser: str | None, timeout: int = 90) -> dict[str, Any]:
    yt_dlp = require_tool("yt-dlp")
    command = [
        yt_dlp,
        "--dump-single-json",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        *cookie_args(browser),
        url,
    ]
    completed = run_command(command, "metadata", timeout)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SkillError("metadata", "yt-dlp returned invalid JSON") from exc
    if not payload.get("id"):
        raise SkillError("metadata", "yt-dlp metadata is missing video ID")
    return payload


def load_metadata(url: str, cookie_mode: str, timeout: int = 90) -> tuple[dict[str, Any], str | None, list[str]]:
    browser = detect_cookie_browser(cookie_mode)
    warnings: list[str] = []
    if browser:
        try:
            return load_metadata_once(url, browser, timeout), browser, warnings
        except SkillError as exc:
            if cookie_mode != "auto":
                raise
            warnings.append(f"{browser} cookie path failed; retried without cookies: {exc}")
    return load_metadata_once(url, None, timeout), None, warnings


def data_api_key() -> str | None:
    return os.environ.get("YT_BROWSE_API_KEY") or os.environ.get("YOUTUBE_API_KEY")


def data_api_get(endpoint: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    key = data_api_key()
    if not key:
        raise SkillError("api", "YouTube Data API key is not configured")
    query = dict(params)
    query["key"] = key
    request = urllib.request.Request(
        f"{DATA_API_BASE}/{endpoint}?{urllib.parse.urlencode(query)}",
        headers={"User-Agent": f"qiaomu-youtube-download/{VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = f"YouTube Data API HTTP {exc.code}"
        try:
            payload = json.loads(exc.read(4096).decode("utf-8", errors="replace"))
            message = str((payload.get("error") or {}).get("message") or message)
        except Exception:
            pass
        raise SkillError("api", message) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SkillError("api", str(exc)) from exc


def data_api_video(video_id: str, timeout: int) -> dict[str, Any]:
    if not data_api_key():
        return {}
    payload = data_api_get(
        "videos",
        {"part": "snippet,statistics,contentDetails", "id": video_id},
        timeout,
    )
    items = payload.get("items") or []
    if not items:
        return {}
    item = items[0]
    snippet = item.get("snippet") or {}
    statistics = item.get("statistics") or {}
    return {
        "published_at": snippet.get("publishedAt"),
        "view_count": int(statistics.get("viewCount") or 0),
        "like_count": int(statistics.get("likeCount") or 0),
        "data_api_used": True,
    }


def iso_duration_seconds(value: str) -> int:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    return int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + int(match.group(3) or 0)


def metadata_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "title": payload.get("title"),
        "channel": payload.get("channel") or payload.get("uploader"),
        "duration_seconds": payload.get("duration"),
        "width": payload.get("width"),
        "height": payload.get("height"),
        "availability": payload.get("availability"),
        "webpage_url": payload.get("webpage_url"),
    }


def enriched_summary(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    summary = metadata_summary(payload)
    try:
        summary.update(data_api_video(str(payload.get("id") or ""), timeout))
    except SkillError as exc:
        summary["data_api_warning"] = str(exc)
        summary["data_api_used"] = False
    if "data_api_used" not in summary:
        summary["data_api_used"] = False
    return summary


def output_template(output_dir: Path) -> str:
    return str(output_dir / "%(title).160B [%(id)s].%(ext)s")


def matching_files(output_dir: Path, video_id: str, suffixes: set[str]) -> list[Path]:
    return sorted(
        path for path in output_dir.iterdir()
        if path.is_file()
        and f"[{video_id}]" in path.name
        and path.suffix.lower() in suffixes
        and not path.name.endswith((".part", ".ytdl"))
    )


def probe_media(path: Path, expect: str) -> dict[str, Any]:
    ffprobe = require_tool("ffprobe")
    command = [
        ffprobe,
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height",
        "-show_entries", "format=format_name,duration,size",
        "-of", "json",
        str(path),
    ]
    completed = run_command(command, "verify", 60)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SkillError("verify", f"ffprobe returned invalid JSON for {path.name}") from exc
    streams = payload.get("streams") or []
    expected_type = "audio" if expect == "audio" else "video"
    if not any(stream.get("codec_type") == expected_type for stream in streams):
        raise SkillError("verify", f"{path.name} has no {expected_type} stream")
    duration = float((payload.get("format") or {}).get("duration") or 0)
    if duration <= 0 or path.stat().st_size <= 0:
        raise SkillError("verify", f"{path.name} has invalid duration or size")
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "container": (payload.get("format") or {}).get("format_name"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "duration_seconds": round(duration, 3),
    }


def prepare_output_dir(value: str | None) -> Path:
    default = os.environ.get("QIAOMU_YOUTUBE_OUTPUT") or str(Path.home() / "Downloads")
    output_dir = Path(value or default).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def download_media(
    url: str,
    output_dir: Path,
    quality: str,
    cookie_mode: str,
    audio_only: bool,
    timeout: int,
) -> dict[str, Any]:
    yt_dlp = require_tool("yt-dlp")
    require_tool("ffmpeg")
    metadata, browser, warnings = load_metadata(url, cookie_mode)
    video_id = str(metadata["id"])
    before = {path.resolve() for path in matching_files(output_dir, video_id, MEDIA_SUFFIXES)}
    command = [
        yt_dlp,
        "--no-playlist",
        "--no-overwrites",
        "--newline",
        *cookie_args(browser),
    ]
    if audio_only:
        command += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        command += ["-f", QUALITY_FORMATS[quality], "--merge-output-format", "mp4"]
    command += ["-o", output_template(output_dir), url]
    try:
        run_command(command, "download", timeout)
    except SkillError as exc:
        if not browser or cookie_mode != "auto":
            raise
        warnings.append(f"{browser} cookie download failed; retried without cookies: {exc}")
        browser = None
        command = without_cookie_args(command)
        run_command(command, "download", timeout)
    files = matching_files(output_dir, video_id, MEDIA_SUFFIXES)
    if not files:
        raise SkillError("download", "yt-dlp completed but no media file containing the video ID was found")
    verified = [probe_media(path, "audio" if audio_only else "video") for path in files]
    for item in verified:
        item["created"] = Path(item["path"]).resolve() not in before
    return {
        "ok": True,
        "command": "audio" if audio_only else "download",
        **enriched_summary(metadata, min(timeout, 60)),
        "quality": "mp3-best" if audio_only else quality,
        "files": verified,
        "cookies_from_browser": browser,
        "warnings": warnings,
    }


def srt_to_timestamped_txt(srt_path: Path) -> Path:
    text = srt_path.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r"(?m)^\d+\s*$\n?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    txt_path = srt_path.with_suffix(".txt")
    if not txt_path.exists():
        txt_path.write_text(text, encoding="utf-8")
    return txt_path


def download_subtitles(
    url: str,
    output_dir: Path,
    langs: str,
    cookie_mode: str,
    timeout: int,
) -> dict[str, Any]:
    yt_dlp = require_tool("yt-dlp")
    require_tool("ffmpeg")
    metadata, browser, warnings = load_metadata(url, cookie_mode)
    video_id = str(metadata["id"])
    command = [
        yt_dlp,
        "--no-playlist",
        "--no-overwrites",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", langs,
        "--convert-subs", "srt",
        "--skip-download",
        *cookie_args(browser),
        "-o", output_template(output_dir),
        url,
    ]
    try:
        run_command(command, "download", timeout)
    except SkillError as exc:
        if not browser or cookie_mode != "auto":
            raise
        warnings.append(f"{browser} cookie subtitle path failed; retried without cookies: {exc}")
        browser = None
        command = without_cookie_args(command)
        run_command(command, "download", timeout)
    subtitles = [path for path in matching_files(output_dir, video_id, SUBTITLE_SUFFIXES) if path.suffix.lower() == ".srt"]
    if not subtitles:
        raise SkillError("download", f"no SRT subtitle matched requested languages: {langs}")
    text_files = [srt_to_timestamped_txt(path) for path in subtitles]
    files = subtitles + text_files
    return {
        "ok": True,
        "command": "subtitles",
        **enriched_summary(metadata, min(timeout, 60)),
        "languages": langs,
        "files": [{"path": str(path.resolve()), "bytes": path.stat().st_size} for path in files],
        "cookies_from_browser": browser,
        "warnings": warnings,
    }


def search_with_data_api(query: str, maximum: int, order: str, after: str | None, before: str | None, timeout: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "part": "id,snippet",
        "type": "video",
        "maxResults": maximum,
        "order": order,
        "q": query,
    }
    if after:
        params["publishedAfter"] = f"{after}T00:00:00Z"
    if before:
        params["publishedBefore"] = f"{before}T23:59:59Z"
    payload = data_api_get("search", params, timeout)
    ordered_ids: list[str] = []
    search_items: dict[str, dict[str, Any]] = {}
    for item in payload.get("items") or []:
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        ordered_ids.append(video_id)
        search_items[video_id] = {
            "id": video_id,
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
    details: dict[str, dict[str, Any]] = {}
    if ordered_ids:
        detail_payload = data_api_get(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(ordered_ids)},
            timeout,
        )
        for item in detail_payload.get("items") or []:
            video_id = item.get("id")
            statistics = item.get("statistics") or {}
            content = item.get("contentDetails") or {}
            if video_id:
                details[video_id] = {
                    "duration_seconds": iso_duration_seconds(str(content.get("duration") or "")),
                    "view_count": int(statistics.get("viewCount") or 0),
                    "like_count": int(statistics.get("likeCount") or 0),
                }
    results = []
    for video_id in ordered_ids:
        result = dict(search_items[video_id])
        result.update(details.get(video_id, {}))
        results.append(result)
    return {"ok": True, "command": "search", "query": query, "data_source": "youtube-data-api-v3", "results": results}


def search_youtube(query: str, maximum: int, order: str, after: str | None, before: str | None, timeout: int) -> dict[str, Any]:
    maximum = max(1, min(maximum, 25))
    if data_api_key():
        try:
            return search_with_data_api(query, maximum, order, after, before, timeout)
        except SkillError as exc:
            api_warning = str(exc)
    else:
        api_warning = "YouTube Data API key not configured; used yt-dlp search fallback"
    yt_dlp = require_tool("yt-dlp")
    command = [
        yt_dlp,
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        f"ytsearch{maximum}:{query}",
    ]
    completed = run_command(command, "search", timeout)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SkillError("search", "yt-dlp returned invalid search JSON") from exc
    results = []
    for entry in payload.get("entries") or []:
        video_id = entry.get("id")
        if not video_id:
            continue
        results.append({
            "id": video_id,
            "title": entry.get("title"),
            "channel": entry.get("channel") or entry.get("uploader"),
            "duration_seconds": entry.get("duration"),
            "view_count": entry.get("view_count"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return {
        "ok": True,
        "command": "search",
        "query": query,
        "data_source": "yt-dlp-search",
        "warning": api_warning,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Qiaomu YouTube download, audio, subtitle, info, search, and dependency tool.")
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    dependency = subparsers.add_parser("doctor", help="Check yt-dlp against the official latest stable release")
    dependency.add_argument("--upgrade", action="store_true", help="Upgrade yt-dlp when an official newer stable release exists")
    dependency.add_argument("--timeout", type=int, default=300)

    def add_url_args(subparser: argparse.ArgumentParser, include_dir: bool = False) -> None:
        subparser.add_argument("url", help="Single YouTube watch, Shorts, Live, embed, or youtu.be URL")
        if include_dir:
            subparser.add_argument("--dir", dest="output_dir", help="Output directory; defaults to ~/Downloads")
        subparser.add_argument(
            "--cookies-from-browser",
            choices=("auto", "none", "chrome", "firefox", "safari", "edge"),
            default="auto",
            help="Cookie source; auto detects a local browser and falls back to no cookies",
        )
        subparser.add_argument("--timeout", type=int, default=600)

    info = subparsers.add_parser("info", help="Read public video metadata")
    add_url_args(info)

    download = subparsers.add_parser("download", help="Download and verify one video")
    add_url_args(download, include_dir=True)
    download.add_argument("--quality", choices=tuple(QUALITY_FORMATS), default="best")

    audio = subparsers.add_parser("audio", help="Extract and verify MP3 audio")
    add_url_args(audio, include_dir=True)

    subtitles = subparsers.add_parser("subtitles", help="Download SRT and create timestamped TXT")
    add_url_args(subtitles, include_dir=True)
    subtitles.add_argument("--langs", default="en,zh-Hans", help="yt-dlp subtitle language expression")

    search = subparsers.add_parser("search", help="Basic YouTube search without an API key")
    search.add_argument("query")
    search.add_argument("--max", type=int, default=10)
    search.add_argument("--order", choices=("relevance", "date", "viewCount", "rating"), default="relevance")
    search.add_argument("--after", help="Data API published-after date: YYYY-MM-DD")
    search.add_argument("--before", help="Data API published-before date: YYYY-MM-DD")
    search.add_argument("--timeout", type=int, default=120)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "doctor":
            result = doctor(args.upgrade, args.timeout)
        elif args.command == "search":
            result = search_youtube(args.query, args.max, args.order, args.after, args.before, args.timeout)
        else:
            url = normalize_youtube_url(args.url)
            cookie_mode = args.cookies_from_browser
            if args.command == "info":
                metadata, browser, warnings = load_metadata(url, cookie_mode, args.timeout)
                result = {
                    "ok": True,
                    "command": "info",
                    **enriched_summary(metadata, min(args.timeout, 60)),
                    "cookies_from_browser": browser,
                    "warnings": warnings,
                }
            elif args.command == "download":
                result = download_media(
                    url, prepare_output_dir(args.output_dir), args.quality, cookie_mode, False, args.timeout
                )
            elif args.command == "audio":
                result = download_media(
                    url, prepare_output_dir(args.output_dir), "best", cookie_mode, True, args.timeout
                )
            else:
                result = download_subtitles(
                    url, prepare_output_dir(args.output_dir), args.langs, cookie_mode, args.timeout
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except SkillError as exc:
        print(json.dumps({"ok": False, "stage": exc.stage, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "stage": "interrupted", "error": "operation interrupted"}, ensure_ascii=False, indent=2))
        raise SystemExit(130)


if __name__ == "__main__":
    main()
