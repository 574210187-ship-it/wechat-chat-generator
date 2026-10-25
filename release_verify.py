#!/usr/bin/env python3
"""Verify bundle_manifest.json against the checked-out public source."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    manifest_path = ROOT / "bundle_manifest.json"
    if not manifest_path.exists():
        print("Missing bundle_manifest.json", file=sys.stderr)
        return 1
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for item in expected.get("files", []):
        path = ROOT / item["path"]
        if not path.exists():
            failures.append(f"missing: {item['path']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            failures.append(f"changed: {item['path']}")
    if failures:
        print("MANIFEST VERIFY FAILED", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"MANIFEST VERIFIED ({expected.get('file_count', 0)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
