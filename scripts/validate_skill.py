#!/usr/bin/env python3
"""Validate qiaomu-youtube-download package and safety contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "agents/interface.yaml",
    "manifest.json",
    "references/workflow.md",
    "references/security.md",
    "evals/trigger_cases.json",
    "evals/output/cases.json",
    "reports/output_quality_scorecard.md",
    "reports/trust-report.md",
    "scripts/youtube.py",
    "scripts/trigger_eval.py",
    "scripts/test_youtube.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate qiaomu-youtube-download package.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.skill_dir).resolve()
    failures: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            failures.append(f"missing: {relative}")
    skill = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").exists() else ""
    script = (root / "scripts/youtube.py").read_text(encoding="utf-8") if (root / "scripts/youtube.py").exists() else ""
    if not skill.startswith("---\n") or "name: qiaomu-youtube-download" not in skill:
        failures.append("invalid SKILL.md frontmatter")
    if "rollback boundary" not in skill.lower() or "trust boundary" not in skill.lower():
        failures.append("governed boundaries missing from SKILL.md")
    for term in (
        "--no-playlist",
        "--no-overwrites",
        "--cookies-from-browser",
        "YT_BROWSE_API_KEY",
        "YOUTUBE_API_KEY",
        "YT_DLP_RELEASE_API",
        "YT_DLP_RELEASE_LATEST",
        "doctor",
        "--upgrade",
        "HOMEBREW_NO_AUTO_UPDATE",
        "download_lock",
        "run_streaming_command",
        "FORMAT_FRAGMENT_RE",
        "cleaned_intermediate_files",
        "ffprobe",
    ):
        if term not in script:
            failures.append(f"scripts/youtube.py missing safety term: {term}")
    if re.search(r"(?:API_KEY|TOKEN|COOKIE)\s*=\s*['\"][^'\"]+['\"]", script):
        failures.append("hard-coded credential-like value in scripts/youtube.py")
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = re.search(r"(?m)^\s*version:\s*([^\s]+)", skill)
        if not version or manifest.get("version") != version.group(1):
            failures.append("SKILL.md and manifest.json versions differ")
    tracked_artifacts = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and path.suffix in {".pyc", ".part", ".ytdl"}]
    if tracked_artifacts:
        failures.append(f"generated artifacts present: {tracked_artifacts}")
    payload = {"ok": not failures, "root": str(root), "failures": failures}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
