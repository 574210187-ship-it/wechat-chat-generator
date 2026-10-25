#!/usr/bin/env python3
"""Write a deterministic inventory of public source files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDED = {".git", "__pycache__", "runs", "bundle_manifest.json"}


def main() -> int:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest = {"format": 1, "file_count": len(files), "files": files}
    (ROOT / "bundle_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote bundle_manifest.json ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
