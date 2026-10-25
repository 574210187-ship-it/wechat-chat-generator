#!/usr/bin/env python3
"""Fail a public release if likely private assets or presets are tracked."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORBIDDEN_PATH_PARTS = ("runs/", "assets/private/", "assets/source/", ".env", ".pem", ".key")
FORBIDDEN_SUFFIXES = (".mp4", ".mov", ".zip", ".psd", ".heic")
PRIVATE_MARKERS = ("姜律师", "jiangpic", "wechat-dialog-generator-private")


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        return [ROOT / item for item in result.stdout.splitlines() if item]
    return [item for item in ROOT.rglob("*") if item.is_file() and ".git" not in item.parts]


def main() -> int:
    failures: list[str] = []
    for file_path in tracked_files():
        relative = file_path.relative_to(ROOT).as_posix()
        lower = relative.lower()
        if any(part in lower for part in FORBIDDEN_PATH_PARTS) or lower.endswith(FORBIDDEN_SUFFIXES):
            failures.append(f"forbidden public path: {relative}")
            continue
        if file_path.stat().st_size > 5_000_000:
            failures.append(f"oversized tracked file (>5 MB): {relative}")
            continue
        if relative == "release_audit.py":
            # This file contains the detection signatures themselves.
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in PRIVATE_MARKERS:
            if marker.lower() in content.lower():
                failures.append(f"private marker '{marker}' in: {relative}")
    if failures:
        print("RELEASE AUDIT FAILED", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("RELEASE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
