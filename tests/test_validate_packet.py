from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "router/.agents/skills/route-codex-work/scripts/validate_packet.py"


def worker_context() -> dict:
    return {
        "run_id": "cmro-test-a1",
        "plan_version": 2,
        "backend": "codex_app_tasks",
        "actor_id": "terra-task-1",
        "route": "terra_worker",
        "configured_model": "gpt-5.6-terra",
        "attempt": 2,
        "allowed_paths": ["src/**", "tests/test_app.py", "docs/"],
        "acceptance_ids": ["AC-001", "AC-002"],
    }


def valid_worker() -> dict:
    return {
        "schema": "cmro.worker.v3",
        "run_id": "cmro-test-a1",
        "plan_version": 2,
        "attempt": 2,
        "worker": {
            "id": "terra-task-1",
            "backend": "codex_app_tasks",
            "route": "terra_worker",
            "configured_model": "gpt-5.6-terra",
        },
        "status": "done",
        "summary": "Implemented and verified the scoped change.",
        "changed_paths": [
            {"path": "src/app/core.py", "action": "modified"},
            {"path": "docs/usage.md", "action": "created"},
        ],
        "checks": [
            {
                "command": "python -m unittest tests.test_app",
                "exit_code": 0,
                "result": "pass",
                "evidence": "Two focused tests passed.",
            }
        ],
        "criteria": [
            {"ac_id": "AC-001", "status": "pass", "evidence": "Focused test passed."},
            {"ac_id": "AC-002", "status": "pass", "evidence": "Diff is in scope."},
        ],
        "blockers": [],
        "limitations": [],
    }


def review_context() -> dict:
    return {
        "run_id": "cmro-test-a1",
        "plan_version": 2,
        "backend": "codex_app_tasks",
        "actor_id": "review-task-1",
        "route": "sol_reviewer",
        "configured_model": "gpt-5.6-sol",
        "acceptance_ids": ["AC-001", "AC-002"],
    }


def valid_review() -> dict:
    return {
        "schema": "cmro.review.v3",
        "run_id": "cmro-test-a1",
        "plan_version": 2,
        "reviewer": {
            "id": "review-task-1",
            "backend": "codex_app_tasks",
            "route": "sol_reviewer",
            "configured_model": "gpt-5.6-sol",
        },
        "decision": "accept",
        "criteria": [
            {"ac_id": "AC-001", "status": "pass", "evidence": "Behavior reproduced."},
            {"ac_id": "AC-002", "status": "pass", "evidence": "Diff is in scope."},
        ],
        "findings": [],
        "verification": [
            {
                "command": "python -m unittest tests.test_app",
                "exit_code": 0,
                "result": "pass",
                "evidence": "Two focused tests passed.",
            }
        ],
        "blockers": [],
        "limitations": [],
    }


class ValidatePacketTests(unittest.TestCase):
    def run_validator(
        self,
        packet: object,
        context: object | None = None,
        *,
        inline_context: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            packet_path = Path(directory) / "packet.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(packet_path)]
            if context is not None and inline_context:
                command.extend(["--context-json", json.dumps(context)])
            elif context is not None:
                context_path = Path(directory) / "context.json"
                context_path.write_text(json.dumps(context), encoding="utf-8")
                command.extend(["--context", str(context_path)])
            return subprocess.run(command, text=True, capture_output=True, check=False)

    def assert_invalid(self, packet: object, context: object | None, text: str) -> None:
        result = self.run_validator(packet, context)
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        output = json.loads(result.stdout)
        self.assertFalse(output["valid"])
        self.assertIn(text, " ".join(output["errors"]))

    def test_valid_worker_with_file_context(self) -> None:
        result = self.run_validator(valid_worker(), worker_context())
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(
            json.loads(result.stdout),
            {"valid": True, "authoritative_context_bound": True, "errors": []},
        )

    def test_valid_reviewer_with_inline_context(self) -> None:
        result = self.run_validator(valid_review(), review_context(), inline_context=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_intrinsic_validation_does_not_require_context(self) -> None:
        result = self.run_validator(valid_worker())
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertFalse(json.loads(result.stdout)["authoritative_context_bound"])

    def test_authoritative_run_plan_attempt_and_id_are_compared(self) -> None:
        mutations = [
            (("run_id",), "wrong-run", "authoritative context.run_id"),
            (("plan_version",), 3, "authoritative context.plan_version"),
            (("attempt",), 1, "authoritative context.attempt"),
            (("worker", "id"), "other-task", "authoritative context.actor_id"),
        ]
        for path, replacement, expected in mutations:
            with self.subTest(path=path):
                packet = valid_worker()
                target = packet
                for segment in path[:-1]:
                    target = target[segment]
                target[path[-1]] = replacement
                self.assert_invalid(packet, worker_context(), expected)

    def test_authoritative_backend_route_and_model_are_compared(self) -> None:
        mutations = [
            ("backend", "native_custom_agent", "context.backend"),
            ("route", "luna_worker", "configured_model does not match worker.route"),
            ("configured_model", "gpt-5.6-luna", "configured_model does not match worker.route"),
        ]
        for field, replacement, expected in mutations:
            with self.subTest(field=field):
                packet = valid_worker()
                packet["worker"][field] = replacement
                self.assert_invalid(packet, worker_context(), expected)

    def test_luna_route_model_combination_is_valid(self) -> None:
        packet = valid_worker()
        context = worker_context()
        packet["worker"]["route"] = context["route"] = "luna_worker"
        packet["worker"]["configured_model"] = context["configured_model"] = "gpt-5.6-luna"
        result = self.run_validator(packet, context)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_self_consistent_route_change_cannot_override_authoritative_context(self) -> None:
        packet = valid_worker()
        packet["worker"]["route"] = "luna_worker"
        packet["worker"]["configured_model"] = "gpt-5.6-luna"
        result = self.run_validator(packet, worker_context())
        self.assertEqual(result.returncode, 2)
        errors = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("worker.route does not match authoritative context.route", errors)
        self.assertIn("configured_model does not match authoritative context.configured_model", errors)

    def test_changed_path_must_be_safe_and_authorized(self) -> None:
        for path, expected in [
            ("../secret.txt", "parent segments"),
            ("C:/secret.txt", "repository-relative"),
            ("src/*.py", "one concrete path"),
            ("other/file.py", "outside authoritative allowed_paths"),
        ]:
            with self.subTest(path=path):
                packet = valid_worker()
                packet["changed_paths"][0]["path"] = path
                self.assert_invalid(packet, worker_context(), expected)

    def test_allowed_path_globs_are_segment_aware(self) -> None:
        packet = valid_worker()
        packet["changed_paths"] = [
            {"path": "src/private/secrets.py", "action": "modified"}
        ]
        context = worker_context()
        context["allowed_paths"] = ["src/*.py"]
        self.assert_invalid(packet, context, "outside authoritative allowed_paths")

        context["allowed_paths"] = ["src/**"]
        result = self.run_validator(packet, context)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_unknown_changed_path_action_is_rejected(self) -> None:
        packet = valid_worker()
        packet["changed_paths"][0]["action"] = "patched"
        self.assert_invalid(packet, worker_context(), "action must be one of")

    def test_worker_criteria_must_exactly_cover_context(self) -> None:
        missing = valid_worker()
        missing["criteria"].pop()
        self.assert_invalid(missing, worker_context(), "missing authoritative acceptance IDs: AC-002")

        extra = valid_worker()
        extra["criteria"].append(
            {"ac_id": "AC-999", "status": "pass", "evidence": "Unsupported extra."}
        )
        self.assert_invalid(extra, worker_context(), "outside authoritative context: AC-999")

    def test_bad_check_enum_and_inconsistent_exit_are_rejected(self) -> None:
        packet = valid_worker()
        packet["checks"][0]["result"] = "ok"
        self.assert_invalid(packet, worker_context(), "result must be pass, fail, or not_run")

        packet = valid_worker()
        packet["checks"][0]["exit_code"] = 7
        self.assert_invalid(packet, worker_context(), "exit_code must be 0")

    def test_criterion_requires_nonempty_evidence(self) -> None:
        packet = valid_worker()
        packet["criteria"][0]["evidence"] = "  "
        self.assert_invalid(packet, worker_context(), "evidence must be a non-empty string")

    def test_context_must_include_workflow_authority_fields(self) -> None:
        context = worker_context()
        del context["actor_id"]
        self.assert_invalid(valid_worker(), context, "context.actor_id is required")

    def test_review_rejects_bad_decision_and_bad_finding(self) -> None:
        packet = valid_review()
        packet["decision"] = "approved"
        self.assert_invalid(packet, review_context(), "decision must be accept")

        packet = valid_review()
        packet["decision"] = "revise"
        packet["criteria"][0]["status"] = "fail"
        packet["findings"] = [
            {
                "id": "F-001",
                "severity": "urgent",
                "ac_ids": ["AC-999"],
                "evidence": "Reproduced.",
                "requested_outcome": "Correct the behavior.",
            }
        ]
        result = self.run_validator(packet, review_context())
        self.assertEqual(result.returncode, 2)
        errors = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("severity must be critical", errors)
        self.assertIn("unknown criteria: AC-999", errors)

    def test_accept_rejects_failed_or_unverified_criterion(self) -> None:
        for status in ("fail", "not_verified"):
            with self.subTest(status=status):
                packet = valid_review()
                packet["criteria"][0]["status"] = status
                self.assert_invalid(packet, review_context(), "requires every acceptance criterion to pass")

    def test_accept_rejects_any_unresolved_finding(self) -> None:
        for severity in ("critical", "high", "medium", "low"):
            with self.subTest(severity=severity):
                packet = valid_review()
                packet["findings"] = [
                    {
                        "id": "F-001",
                        "severity": severity,
                        "ac_ids": ["AC-001"],
                        "evidence": "A blocking defect remains.",
                        "requested_outcome": "Resolve the defect.",
                    }
                ]
                self.assert_invalid(packet, review_context(), "findings to be empty")

    def test_accept_rejects_blocker(self) -> None:
        packet = valid_review()
        packet["blockers"] = ["Required local authority is unavailable."]
        self.assert_invalid(packet, review_context(), "blockers to be empty")

    def test_accept_rejects_failed_or_unexecuted_verification(self) -> None:
        for result_value, exit_code in (("fail", 1), ("not_run", None)):
            with self.subTest(result=result_value):
                packet = valid_review()
                packet["verification"][0]["result"] = result_value
                packet["verification"][0]["exit_code"] = exit_code
                self.assert_invalid(
                    packet,
                    review_context(),
                    "requires every verification result to pass",
                )

    def test_revise_requires_nonpassing_criteria_and_consistent_findings(self) -> None:
        packet = valid_review()
        packet["decision"] = "revise"
        packet["findings"] = [
            {
                "id": "F-001",
                "severity": "medium",
                "ac_ids": ["AC-001"],
                "evidence": "A defect remains.",
                "requested_outcome": "Correct the defect.",
            }
        ]
        self.assert_invalid(
            packet,
            review_context(),
            "requires at least one non-passing acceptance criterion",
        )

        packet["criteria"][1]["status"] = "fail"
        self.assert_invalid(
            packet,
            review_context(),
            "must reference only non-passing criteria",
        )

    def test_revise_requires_a_finding(self) -> None:
        packet = valid_review()
        packet["decision"] = "revise"
        packet["criteria"][0]["status"] = "fail"
        self.assert_invalid(packet, review_context(), "revise requires at least one finding")

    def test_review_context_omits_worker_only_fields(self) -> None:
        context = review_context()
        context["attempt"] = 2
        self.assert_invalid(valid_review(), context, "context.attempt is not allowed")

    def test_schema_is_strict_about_unknown_fields(self) -> None:
        packet = valid_worker()
        packet["self_certified_model"] = True
        self.assert_invalid(packet, worker_context(), "packet.self_certified_model is not allowed")

    def test_malformed_json_reports_machine_readable_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packet.json"
            path.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
