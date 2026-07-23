#!/usr/bin/env python3
"""Smoke-test qiaomu-youtube-download routing examples and description terms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PLATFORM = ("youtube", "油管", "youtu.be", "yt 视频")
ACTION = ("下载", "保存", "mp3", "音频", "字幕", "转录", "文字", "视频信息", "查看", "搜索", "download", "save")
NEGATIVE = ("不要下载", "notebooklm", "上传到 youtube", "频道写", "制作一条", "推荐算法", "已经有字幕")
DESCRIPTION_REQUIRED_TERMS = ("youtube.com", "youtu.be", "shorts", "下载", "字幕", "audio", "cookies")


def description(root: Path) -> str:
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    lines = text.splitlines()
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return ""
    output: list[str] = []
    collecting = False
    for line in lines[1:end]:
        if line.startswith("description:"):
            collecting = True
            value = line.split(":", 1)[1].strip().strip("|> ")
            if value:
                output.append(value)
        elif collecting and line.startswith((" ", "\t")):
            output.append(line.strip())
        elif collecting:
            break
    return " ".join(output).lower()


def predicts(text: str) -> bool:
    lowered = text.lower()
    return (
        any(token in lowered for token in PLATFORM)
        and any(token in lowered for token in ACTION)
        and not any(token in lowered for token in NEGATIVE)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate qiaomu-youtube-download trigger fixtures.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.skill_dir).resolve()
    cases = json.loads((root / "evals/trigger_cases.json").read_text(encoding="utf-8"))
    desc = description(root)
    missing = [term for term in DESCRIPTION_REQUIRED_TERMS if term not in desc]
    results = []
    for bucket, expected in (("should_trigger", True), ("should_not_trigger", False), ("near_neighbor", False)):
        for case in cases[bucket]:
            text = case["text"] if isinstance(case, dict) else case
            predicted = predicts(text)
            results.append({
                "bucket": bucket,
                "text": text,
                "expected": expected,
                "predicted": predicted,
                "passed": predicted == expected,
            })
    payload = {
        "ok": all(item["passed"] for item in results) and not missing,
        "total": len(results),
        "passed": sum(item["passed"] for item in results),
        "description_required_terms": list(DESCRIPTION_REQUIRED_TERMS),
        "missing_description_terms": missing,
        "results": results,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    if not payload["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
