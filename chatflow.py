#!/usr/bin/env python3
"""Stateful, reproducible WeChat-style chat capture workflow.

This is deliberately a local renderer. It does not log in to WeChat, scrape
accounts, or claim that its output is a real product screenshot.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RENDERER = ROOT / "tools" / "render_wechat_capture.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Project must be a JSON object: {path}")
    return value


def read_message_lines(path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Each message line needs LEFT: or RIGHT:, got: {raw}")
        prefix, text = line.split(":", 1)
        side = prefix.strip().lower()
        if side in {"l", "left", "对方", "客户"}:
            side = "left"
        elif side in {"r", "right", "我", "me"}:
            side = "right"
        elif side in {"system", "系统"}:
            messages.append({"type": "system", "text": text.strip()})
            continue
        else:
            raise ValueError(f"Unknown side '{prefix}'. Use LEFT: or RIGHT:.")
        messages.append({"side": side, "type": "text", "text": text.strip()})
    return messages


def blank_project() -> dict[str, Any]:
    return {
        "title": "聊天",
        "theme": "light",
        "chrome": "full",
        "participants": {
            "left": {"name": "对方", "avatar": None},
            "right": {"name": "我", "avatar": None},
        },
        "messages": [],
    }


def deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def normalize_project(raw: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    project = deep_merge(blank_project(), raw)
    if args.messages:
        project["messages"] = read_message_lines(Path(args.messages))
    if not isinstance(project.get("messages"), list):
        raise ValueError("messages must be an array")
    participants = project.setdefault("participants", {})
    for side in ("left", "right"):
        if not isinstance(participants.get(side), dict):
            participants[side] = {"name": "对方" if side == "left" else "我", "avatar": None}
        participants[side].setdefault("name", "对方" if side == "left" else "我")
        participants[side].setdefault("avatar", None)
    overrides = {
        "right_name": ("right", "name"),
        "left_name": ("left", "name"),
        "right_avatar": ("right", "avatar"),
        "left_avatar": ("left", "avatar"),
    }
    for option, (side, field) in overrides.items():
        value = getattr(args, option, None)
        if value:
            participants[side][field] = value
    if args.title:
        project["title"] = args.title
    if args.theme:
        project["theme"] = args.theme
    if args.chrome:
        project["chrome"] = args.chrome
    if args.reference:
        project["reference"] = str(Path(args.reference).resolve())
    replacements: list[tuple[str, str]] = []
    for rule in args.replace or []:
        if "=" not in rule:
            raise ValueError("--replace must be FROM=TO")
        before, after = rule.split("=", 1)
        if not before:
            raise ValueError("--replace source cannot be empty")
        replacements.append((before, after))
    if replacements:
        for message in project["messages"]:
            for key in ("text", "caption", "note", "amount"):
                if isinstance(message.get(key), str):
                    for before, after in replacements:
                        message[key] = message[key].replace(before, after)
        for side in ("left", "right"):
            value = str(participants[side].get("name", ""))
            for before, after in replacements:
                value = value.replace(before, after)
            participants[side]["name"] = value
        project["replacements"] = [{"from": before, "to": after} for before, after in replacements]
    for index, message in enumerate(project["messages"]):
        if not isinstance(message, dict):
            raise ValueError(f"messages[{index}] must be an object")
        message.setdefault("type", "text")
        if message["type"] != "system":
            message.setdefault("side", "left")
            if message["side"] not in {"left", "right"}:
                raise ValueError(f"messages[{index}].side must be left or right")
        if message["type"] in {"text", "system", "call"} and not str(message.get("text", "")).strip():
            raise ValueError(f"messages[{index}] ({message['type']}) needs text")
    if project["theme"] not in {"light", "dark"}:
        raise ValueError("theme must be light or dark")
    if project["chrome"] not in {"full", "content"}:
        raise ValueError("chrome must be full or content")
    return project


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initial_state(project: dict[str, Any], mode: str, reference: str | None) -> dict[str, Any]:
    kinds = sorted({str(item.get("type", "text")) for item in project["messages"]})
    return {
        "tool": "wechat-chat-generator",
        "version": "1.2.0",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "mode": mode,
        "status": "ANALYZED",
        "current_stage": "00_analysis",
        "route": "CHAT_SCROLL_CAPTURE" if "video" in kinds else "CHAT_IMAGE_CAPTURE",
        "reference": reference,
        "message_count": len(project["messages"]),
        "message_types": kinds,
        "gates": {"00_analysis": "passed", "01_render": "pending", "02_acceptance": "pending"},
        "history": [{"at": utc_now(), "stage": "00_analysis", "event": "analysis_complete"}],
    }


def stage_ok(mode: str, approve: str, stage: str) -> bool:
    return mode == "AUTO" or approve == "all" or approve == stage


def run_renderer(project_path: Path, run_dir: Path, args: argparse.Namespace) -> list[str]:
    command = [sys.executable, str(RENDERER), "--project", str(project_path), "--output-dir", str(run_dir)]
    if args.scroll:
        command.append("--scroll")
        command.extend(["--duration", str(args.duration)])
    if args.font:
        command.extend(["--font", args.font])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (run_dir / "renderer.stdout.log").write_text(result.stdout, encoding="utf-8")
    (run_dir / "renderer.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError("Renderer failed. See renderer.stderr.log")
    manifest = read_json(run_dir / "render-manifest.json")
    return [str(item) for item in manifest.get("outputs", [])]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--project", help="Project JSON file")
    source.add_argument("--messages", help="Plain-text conversation file (LEFT: / RIGHT: lines)")
    parser.add_argument("--run-dir", default="runs/latest", help="Run state/output directory")
    parser.add_argument("--mode", choices=["AUTO", "REVIEW"], default="AUTO")
    parser.add_argument("--approve", choices=["analysis", "render", "all"], help="Release a REVIEW-mode stage")
    parser.add_argument("--resume", action="store_true", help="Resume a prior REVIEW run from --run-dir")
    parser.add_argument("--rerender", action="store_true", help="Rebuild the current render stage after local edits")
    parser.add_argument("--title")
    parser.add_argument("--theme", choices=["light", "dark"])
    parser.add_argument("--chrome", choices=["full", "content"])
    parser.add_argument("--left-name")
    parser.add_argument("--right-name")
    parser.add_argument("--left-avatar", "--client-avatar", dest="left_avatar")
    parser.add_argument("--right-avatar", "--avatar", dest="right_avatar")
    parser.add_argument("--replace", action="append", default=[], metavar="FROM=TO")
    parser.add_argument("--reference", help="Optional reference image path; recorded only, never OCRed")
    parser.add_argument("--scroll", action="store_true", help="Also create a natural downward 9:16 scroll video")
    parser.add_argument("--duration", type=float, default=3.0, help="Scroll video duration in seconds")
    parser.add_argument("--font", help="Optional .ttf/.otf/.ttc font path")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / "state.json"
    try:
        if args.project:
            raw = read_json(Path(args.project))
        elif args.messages:
            raw = {"messages": read_message_lines(Path(args.messages))}
        elif args.resume and (run_dir / "normalized-project.json").exists():
            raw = read_json(run_dir / "normalized-project.json")
        else:
            raise ValueError("Provide --project or --messages (or --resume with an existing run)")
        project = normalize_project(raw, args)
        write_json(run_dir / "normalized-project.json", project)
        previous: dict[str, Any] | None = None
        if args.resume and state_path.exists():
            previous = read_json(state_path)
        state = initial_state(project, args.mode, project.get("reference"))
        if previous:
            state["history"] = list(previous.get("history", [])) + state["history"]
            if isinstance(previous.get("gates"), dict):
                state["gates"].update(previous["gates"])
        write_json(run_dir / "analysis.json", {
            "message_count": len(project["messages"]),
            "message_types": state["message_types"],
            "participants": project["participants"],
            "reference_contract": "Reference assets are not OCRed or auto-inferred; inspect and encode needed values explicitly.",
            "replacement_rules": project.get("replacements", []),
        })
        resume_at_render = bool(previous and previous.get("current_stage") == "01_render" and previous.get("status") == "WAITING_FOR_REVIEW")
        if not resume_at_render and not stage_ok(args.mode, args.approve or "", "analysis"):
            state.update({"status": "WAITING_FOR_REVIEW", "current_stage": "00_analysis"})
            state["history"].append({"at": utc_now(), "stage": "00_analysis", "event": "waiting_for_human_approval"})
            write_json(state_path, state)
            print(f"REVIEW waiting at 00_analysis: {run_dir}")
            return 0
        if args.dry_run:
            state.update({"status": "DRY_RUN_COMPLETE", "current_stage": "01_render"})
            write_json(state_path, state)
            print(json.dumps(state, ensure_ascii=False, indent=2))
            return 0
        outputs: list[str]
        if resume_at_render and not args.rerender:
            outputs = [str(item) for item in previous.get("outputs", [])]
            if not outputs:
                manifest_path = run_dir / "render-manifest.json"
                if manifest_path.exists():
                    outputs = [str(item) for item in read_json(manifest_path).get("outputs", [])]
            if not outputs:
                raise RuntimeError("Cannot resume render acceptance: no prior render outputs. Use --rerender.")
            state["gates"]["01_render"] = "passed"
            state["history"].append({"at": utc_now(), "stage": "01_render", "event": "reused_render_for_acceptance", "outputs": outputs})
        else:
            outputs = run_renderer(run_dir / "normalized-project.json", run_dir, args)
            state["gates"]["01_render"] = "passed"
            state["history"].append({"at": utc_now(), "stage": "01_render", "event": "render_complete", "outputs": outputs})
        if not stage_ok(args.mode, args.approve or "", "render"):
            state.update({"status": "WAITING_FOR_REVIEW", "current_stage": "01_render", "outputs": outputs})
            write_json(state_path, state)
            print(f"REVIEW waiting at 01_render: {run_dir}")
            return 0
        required = [run_dir / name for name in outputs]
        missing = [str(path.name) for path in required if not path.exists() or path.stat().st_size == 0]
        if missing:
            raise RuntimeError(f"Acceptance failed, missing outputs: {', '.join(missing)}")
        state["gates"]["02_acceptance"] = "passed"
        state.update({"status": "COMPLETED", "current_stage": "02_acceptance", "outputs": outputs, "updated_at": utc_now()})
        state["history"].append({"at": utc_now(), "stage": "02_acceptance", "event": "accepted"})
        write_json(state_path, state)
        print(f"COMPLETED: {run_dir}")
        return 0
    except Exception as error:  # preserve the failure gate and do not advance
        failed = {
            "tool": "wechat-chat-generator",
            "version": "1.2.0",
            "status": "FAILED",
            "current_stage": "01_render",
            "updated_at": utc_now(),
            "error": str(error),
        }
        if state_path.exists():
            try:
                failed["previous"] = read_json(state_path)
            except Exception:
                pass
        write_json(state_path, failed)
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
