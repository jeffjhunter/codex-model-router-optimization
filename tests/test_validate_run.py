from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "router/.agents/skills/route-codex-work/scripts/validate_run.py"


def valid_record() -> dict:
    return {
        "schema": "cmro.final.v3",
        "run_id": "cmro-test-1",
        "plan_version": 1,
        "status": "complete",
        "attempts": 1,
        "backend": "codex_app_tasks",
        "worker_id": "worker-task",
        "reviewer_id": "review-task",
        "identity": {
            "root": {
                "control_plane_pinned": True,
                "runtime_observed": True,
                "task_id": "root-task",
                "turn_ids": ["root-turn"],
                "value": "gpt-5.6-sol/xhigh",
            },
            "worker": {
                "control_plane_pinned": True,
                "runtime_observed": True,
                "task_id": "worker-task",
                "preflight_turn_id": "worker-preflight",
                "turn_ids": ["worker-preflight", "worker-turn"],
                "value": "gpt-5.6-terra/high",
            },
            "reviewer": {
                "control_plane_pinned": True,
                "runtime_observed": True,
                "task_id": "review-task",
                "preflight_turn_id": "review-preflight",
                "turn_ids": ["review-preflight", "review-turn"],
                "value": "gpt-5.6-sol/xhigh",
            },
        },
        "review_snapshots": [
            {
                "reviewer_turn_id": "review-turn",
                "scope": "tracked-index-and-untracked-content",
                "before_sha256": "a" * 64,
                "after_sha256": "a" * 64,
                "matched": True,
            }
        ],
        "requirements": [{"rq_id": "RQ-001", "ac_ids": ["AC-001"], "status": "pass"}],
        "verification_summary": "Checked.",
        "blockers": [],
    }


class ValidateRunTests(unittest.TestCase):
    def run_validator(self, value: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_complete_record_is_valid(self) -> None:
        result = self.run_validator(valid_record())
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_complete_record_requires_distinct_observed_tasks(self) -> None:
        value = valid_record()
        value["identity"]["reviewer"]["task_id"] = "worker-task"
        value["reviewer_id"] = "worker-task"
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("distinct", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_rejects_unobserved_identity(self) -> None:
        value = valid_record()
        value["identity"]["worker"]["runtime_observed"] = False
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("runtime_observed", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_rejects_wrong_runtime_model(self) -> None:
        value = valid_record()
        value["identity"]["worker"]["value"] = "gpt-5.6-sol/xhigh"
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("stock CMRO route", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_rejects_zero_attempts(self) -> None:
        value = valid_record()
        value["attempts"] = 0
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("1 through 3", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_requires_observed_action_turn(self) -> None:
        value = valid_record()
        value["identity"]["worker"]["turn_ids"] = ["worker-preflight"]
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("action turn", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_requires_observed_root_turn(self) -> None:
        value = valid_record()
        value["identity"]["root"]["turn_ids"] = []
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("coordinator turn", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_requires_one_review_per_attempt(self) -> None:
        value = valid_record()
        value["attempts"] = 2
        value["identity"]["worker"]["turn_ids"].append("worker-turn-2")
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("reviewer action turns", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_rejects_reviewer_snapshot_change(self) -> None:
        value = valid_record()
        value["review_snapshots"][0]["after_sha256"] = "b" * 64
        value["review_snapshots"][0]["matched"] = False
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("matching digests", " ".join(json.loads(result.stdout)["errors"]))

    def test_complete_record_requires_snapshot_for_every_review_turn(self) -> None:
        value = valid_record()
        value["identity"]["reviewer"]["turn_ids"].append("review-turn-2")
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("every reviewer action turn", " ".join(json.loads(result.stdout)["errors"]))

    def test_human_review_requires_blocker_but_not_all_identities(self) -> None:
        value = valid_record()
        value["status"] = "needs_human_review"
        value["identity"]["reviewer"] = {
            "control_plane_pinned": False,
            "runtime_observed": False,
        }
        value["requirements"][0]["status"] = "not_verified"
        value["blockers"] = ["Reviewer identity unavailable"]
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
