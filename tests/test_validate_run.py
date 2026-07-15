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


def explicit_record() -> dict:
    value = valid_record()
    value["identity"]["worker"]["action_turn_ids"] = ["worker-turn"]
    value["identity"]["worker"]["packet_repair_turn_ids"] = []
    value["identity"]["reviewer"]["action_turn_ids"] = ["review-turn"]
    value["identity"]["reviewer"]["packet_repair_turn_ids"] = []
    value["packet_repairs"] = []
    return value


def packet_repair(
    actor_role: str,
    invalid_turn_id: str,
    repaired_turn_id: str,
) -> dict:
    return {
        "actor_role": actor_role,
        "invalid_turn_id": invalid_turn_id,
        "repaired_turn_id": repaired_turn_id,
        "mode": "format-only",
        "writes": False,
        "reason": "The material response was valid work but not valid packet JSON.",
        "snapshot": {
            "scope": "tracked-index-and-untracked-content",
            "before_sha256": "d" * 64,
            "after_sha256": "d" * 64,
            "matched": True,
        },
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

    def test_legacy_record_without_explicit_accounting_remains_valid(self) -> None:
        value = valid_record()
        self.assertNotIn("packet_repairs", value)
        self.assertNotIn("action_turn_ids", value["identity"]["worker"])
        result = self.run_validator(value)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

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

    def test_pilot_shape_counts_three_actions_not_worker_packet_repair(self) -> None:
        value = explicit_record()
        value["status"] = "needs_human_review"
        value["attempts"] = 3
        value["identity"]["worker"]["turn_ids"] = [
            "worker-preflight",
            "worker-turn-1",
            "worker-packet-repair",
            "worker-turn-2",
            "worker-turn-3",
        ]
        value["identity"]["worker"]["action_turn_ids"] = [
            "worker-turn-1",
            "worker-turn-2",
            "worker-turn-3",
        ]
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        value["identity"]["reviewer"]["turn_ids"] = [
            "review-preflight",
            "review-turn-1",
            "review-turn-2",
            "review-turn-3",
        ]
        value["identity"]["reviewer"]["action_turn_ids"] = [
            "review-turn-1",
            "review-turn-2",
            "review-turn-3",
        ]
        value["packet_repairs"] = [
            packet_repair("worker", "worker-turn-1", "worker-packet-repair")
        ]
        value["review_snapshots"] = [
            {
                "reviewer_turn_id": turn_id,
                "scope": "tracked-index-and-untracked-content",
                "before_sha256": digest * 64,
                "after_sha256": digest * 64,
                "matched": True,
            }
            for turn_id, digest in (
                ("review-turn-1", "a"),
                ("review-turn-2", "b"),
                ("review-turn-3", "c"),
            )
        ]
        value["requirements"][0]["status"] = "fail"
        value["blockers"] = ["Attempt cap reached with unresolved findings."]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_repairs_do_not_count_as_attempts_reviews_or_snapshots(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        value["identity"]["reviewer"]["turn_ids"].append("review-packet-repair")
        value["identity"]["reviewer"]["packet_repair_turn_ids"] = [
            "review-packet-repair"
        ]
        value["packet_repairs"] = [
            packet_repair("worker", "worker-turn", "worker-packet-repair"),
            packet_repair("reviewer", "review-turn", "review-packet-repair"),
        ]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(len(value["review_snapshots"]), 1)

    def test_explicit_accounting_rejects_action_repair_overlap(self) -> None:
        value = explicit_record()
        value["status"] = "needs_human_review"
        value["attempts"] = 2
        value["blockers"] = ["Invalid accounting fixture."]
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["action_turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        value["packet_repairs"] = [
            packet_repair("worker", "worker-turn", "worker-packet-repair")
        ]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot overlap", " ".join(json.loads(result.stdout)["errors"]))

    def test_explicit_accounting_rejects_preflight_or_unobserved_turns(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["action_turn_ids"] = [
            "worker-preflight",
            "worker-unobserved",
        ]
        value["attempts"] = 2

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        errors = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("must exclude preflight", errors)
        self.assertIn("must be observed", errors)

    def test_explicit_accounting_rejects_orphan_repair_turn(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "exactly one packet_repairs record",
            " ".join(json.loads(result.stdout)["errors"]),
        )

    def test_explicit_accounting_rejects_duplicate_repair_record(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        repair = packet_repair("worker", "worker-turn", "worker-packet-repair")
        value["packet_repairs"] = [repair, dict(repair)]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        errors = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("at most one repair", errors)
        self.assertIn("more than once", errors)

    def test_explicit_accounting_rejects_excess_repairs_for_one_action(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].extend(
            ["worker-packet-repair-1", "worker-packet-repair-2"]
        )
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair-1",
            "worker-packet-repair-2",
        ]
        value["packet_repairs"] = [
            packet_repair("worker", "worker-turn", "worker-packet-repair-1"),
            packet_repair("worker", "worker-turn", "worker-packet-repair-2"),
        ]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at most one repair", " ".join(json.loads(result.stdout)["errors"]))

    def test_explicit_accounting_requires_no_write_format_only_repair(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        repair = packet_repair("worker", "worker-turn", "worker-packet-repair")
        repair["mode"] = "content-revision"
        repair["writes"] = True
        value["packet_repairs"] = [repair]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        errors = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("mode must be format-only", errors)
        self.assertIn("writes must be false", errors)

    def test_explicit_accounting_requires_matching_repair_snapshot(self) -> None:
        value = explicit_record()
        value["identity"]["worker"]["turn_ids"].append("worker-packet-repair")
        value["identity"]["worker"]["packet_repair_turn_ids"] = [
            "worker-packet-repair"
        ]
        repair = packet_repair("worker", "worker-turn", "worker-packet-repair")
        repair["snapshot"]["after_sha256"] = "e" * 64
        repair["snapshot"]["matched"] = False
        value["packet_repairs"] = [repair]

        result = self.run_validator(value)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "snapshot must contain matching digests",
            " ".join(json.loads(result.stdout)["errors"]),
        )


if __name__ == "__main__":
    unittest.main()
