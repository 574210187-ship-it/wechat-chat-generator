from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "chatflow.py"


def sample_project() -> dict:
    return {
        "title": "Demo",
        "theme": "light",
        "participants": {"left": {"name": "Client"}, "right": {"name": "Advisor"}},
        "messages": [
            {"side": "left", "type": "text", "text": "Can we confirm the time?"},
            {"side": "right", "type": "text", "text": "Yes, 3 PM is fine."},
            {"type": "system", "text": "Today 14:30"},
            {"side": "right", "type": "transfer", "amount": "$0.10", "note": "Test"},
        ],
    }


class ChatFlowTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        source = root / "project.json"
        source.write_text(json.dumps(sample_project()), encoding="utf-8")
        return source

    def test_auto_generates_png_and_complete_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            project = self.make_project(temp)
            run_dir = temp / "run"
            result = subprocess.run([sys.executable, str(FLOW), "--project", str(project), "--run-dir", str(run_dir), "--mode", "AUTO"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "COMPLETED")
            self.assertTrue((run_dir / "chat-capture.png").read_bytes().startswith(b"\x89PNG"))

    def test_review_stops_after_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            project = self.make_project(temp)
            run_dir = temp / "review"
            result = subprocess.run([sys.executable, str(FLOW), "--project", str(project), "--run-dir", str(run_dir), "--mode", "REVIEW"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "WAITING_FOR_REVIEW")
            self.assertEqual(state["current_stage"], "00_analysis")

    def test_review_resume_advances_without_restarting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            project = self.make_project(temp)
            run_dir = temp / "review-resume"
            first = subprocess.run([sys.executable, str(FLOW), "--project", str(project), "--run-dir", str(run_dir), "--mode", "REVIEW"], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            render = subprocess.run([sys.executable, str(FLOW), "--resume", "--run-dir", str(run_dir), "--mode", "REVIEW", "--approve", "analysis"], capture_output=True, text=True)
            self.assertEqual(render.returncode, 0, render.stderr)
            self.assertEqual(json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["current_stage"], "01_render")
            accept = subprocess.run([sys.executable, str(FLOW), "--resume", "--run-dir", str(run_dir), "--mode", "REVIEW", "--approve", "render"], capture_output=True, text=True)
            self.assertEqual(accept.returncode, 0, accept.stderr)
            self.assertEqual(json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["status"], "COMPLETED")

    def test_explicit_replace_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            project = self.make_project(temp)
            data = sample_project()
            data["messages"][0]["text"] = "Legacy name needs replacement"
            project.write_text(json.dumps(data), encoding="utf-8")
            run_dir = temp / "replace"
            result = subprocess.run([sys.executable, str(FLOW), "--project", str(project), "--run-dir", str(run_dir), "--mode", "AUTO", "--replace", "Legacy=Current"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            normalized = json.loads((run_dir / "normalized-project.json").read_text(encoding="utf-8"))
            self.assertIn("Current", normalized["messages"][0]["text"])
            self.assertEqual(normalized["replacements"], [{"from": "Legacy", "to": "Current"}])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_scroll_video_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            project = self.make_project(temp)
            data = sample_project()
            data["messages"] *= 4
            project.write_text(json.dumps(data), encoding="utf-8")
            run_dir = temp / "scroll"
            result = subprocess.run([sys.executable, str(FLOW), "--project", str(project), "--run-dir", str(run_dir), "--mode", "AUTO", "--scroll", "--duration", "0.6"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater((run_dir / "chat-scroll-3s.mp4").stat().st_size, 1000)
            self.assertFalse(list((run_dir / "scroll-frames").glob("*.png")) == [])
            self.assertFalse(any(path.stat().st_size == 0 for path in (run_dir / "scroll-frames").glob("*.png")))
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(run_dir / "chat-scroll-3s.mp4")], capture_output=True, text=True)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertAlmostEqual(float(probe.stdout.strip()), 0.6, places=2)


if __name__ == "__main__":
    unittest.main()
