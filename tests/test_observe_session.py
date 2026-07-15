from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "router/.agents/skills/route-codex-work/scripts/observe_session.py"
THREAD_ID = "019f62ef-70fe-7eb2-b94e-dcc249f8cde8"


class ObserveSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.sessions = Path(self.tempdir.name) / "sessions"
        self.sessions.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_probe(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--thread-id",
                THREAD_ID,
                "--sessions-root",
                str(self.sessions),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def write_session(
        self,
        *,
        parent_thread_id: str | None = None,
        session_cwd: str = "/tmp/project",
        turn_cwd: str = "/tmp/project",
    ) -> Path:
        path = self.sessions / "2026/07/14" / f"rollout-{THREAD_ID}.jsonl"
        path.parent.mkdir(parents=True)
        records = [
            {
                "type": "session_meta",
                "payload": {
                    "id": THREAD_ID,
                    "parent_thread_id": parent_thread_id,
                    "cwd": session_cwd,
                },
            },
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "inherited-parent-turn"},
            },
            {
                "type": "turn_context",
                "payload": {
                    "turn_id": "inherited-parent-turn",
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "cwd": turn_cwd,
                },
            },
            {
                "type": "response_item",
                "payload": {"type": "message", "content": "DO-NOT-LEAK"},
            },
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "worker-turn"},
            },
            {
                "type": "turn_context",
                "payload": {
                    "turn_id": "worker-turn",
                    "model": "gpt-5.6-terra",
                    "effort": "high",
                    "cwd": turn_cwd,
                },
            },
        ]
        path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
        return path

    def test_selects_latest_turn_context_without_message_content(self) -> None:
        path = self.write_session()
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-terra",
            "--expect-effort",
            "high",
            "--expect-cwd",
            "/tmp/project",
            "--expect-turn-id",
            "worker-turn",
            "--expect-top-level",
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "verified")
        self.assertEqual(value["expectation_status"], "match")
        self.assertEqual(value["selected_turn_context"]["turn_id"], "worker-turn")
        self.assertEqual(value["selected_turn_context"]["line"], 6)
        self.assertTrue(value["source"]["path"].endswith(path.name))
        self.assertEqual(len(value["turn_contexts"]), 2)
        self.assertNotIn("DO-NOT-LEAK", result.stdout)

    def test_expected_model_mismatch_fails_closed(self) -> None:
        self.write_session()
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-luna",
            "--expect-turn-id",
            "worker-turn",
        )

        self.assertEqual(result.returncode, 3)
        value = json.loads(result.stdout)
        self.assertEqual(value["expectation_status"], "mismatch")
        self.assertIn("model expected", value["mismatches"][0])

    def test_expected_turn_does_not_use_inherited_context(self) -> None:
        self.write_session(parent_thread_id="parent-id")
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-sol",
            "--expect-turn-id",
            "worker-turn",
        )

        self.assertEqual(result.returncode, 3)
        value = json.loads(result.stdout)
        self.assertEqual(value["selected_turn_context"]["turn_id"], "worker-turn")
        self.assertIn("model expected", value["mismatches"][0])

    def test_top_level_expectation_rejects_forked_session(self) -> None:
        self.write_session(parent_thread_id="parent-id")
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-terra",
            "--expect-turn-id",
            "worker-turn",
            "--expect-top-level",
        )

        self.assertEqual(result.returncode, 3)
        value = json.loads(result.stdout)
        self.assertIn("top-level app task", " ".join(value["mismatches"]))

    def test_duplicate_session_candidates_are_ambiguous(self) -> None:
        original = self.write_session()
        duplicate = self.sessions / "duplicate" / original.name
        duplicate.parent.mkdir()
        shutil.copy2(original, duplicate)
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-terra",
            "--expect-turn-id",
            "worker-turn",
        )

        self.assertEqual(result.returncode, 2)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "ambiguous")
        self.assertEqual(value["candidate_count"], 2)

    def test_session_cwd_must_match_even_when_turn_cwd_matches(self) -> None:
        self.write_session(session_cwd="/tmp/other")
        result = self.run_probe(
            "--expect-model",
            "gpt-5.6-terra",
            "--expect-turn-id",
            "worker-turn",
            "--expect-cwd",
            "/tmp/project",
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("session cwd expected", " ".join(json.loads(result.stdout)["mismatches"]))

    def test_missing_session_returns_not_found(self) -> None:
        result = self.run_probe()

        self.assertEqual(result.returncode, 2)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "not_found")

    def test_invalid_thread_id_is_rejected(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--thread-id", "../bad"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid thread id", result.stdout)


if __name__ == "__main__":
    unittest.main()
