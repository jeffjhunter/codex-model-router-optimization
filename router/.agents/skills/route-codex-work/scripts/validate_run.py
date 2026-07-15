#!/usr/bin/env python3
"""Validate a sanitized CMRO v3 final record without reading session logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROLES = ("root", "worker", "reviewer")
EXPECTED_VALUES = {
    "root": {"gpt-5.6-sol/xhigh"},
    "worker": {"gpt-5.6-luna/medium", "gpt-5.6-terra/high"},
    "reviewer": {"gpt-5.6-sol/xhigh"},
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["record must be a JSON object"]
    if value.get("schema") != "cmro.final.v3":
        errors.append("schema must be cmro.final.v3")
    if not is_nonempty_string(value.get("run_id")):
        errors.append("run_id must be a non-empty string")
    if (
        not isinstance(value.get("plan_version"), int)
        or isinstance(value.get("plan_version"), bool)
        or value.get("plan_version", 0) < 1
    ):
        errors.append("plan_version must be a positive integer")
    status = value.get("status")
    if status not in {"complete", "needs_human_review"}:
        errors.append("status must be complete or needs_human_review")
    if value.get("backend") not in {"codex_app_tasks", "native_custom_agent"}:
        errors.append("backend must identify a supported orchestration backend")
    attempts = value.get("attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or not 0 <= attempts <= 3:
        errors.append("attempts must be an integer from 0 through 3")
    elif status == "complete" and attempts < 1:
        errors.append("attempts must be 1 through 3 for complete records")

    identity = value.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity must be an object")
        identity = {}
    task_ids: list[str] = []
    observed_turn_ids: list[str] = []
    role_turn_ids: dict[str, list[str]] = {}
    for role in ROLES:
        actor = identity.get(role)
        if not isinstance(actor, dict):
            errors.append(f"identity.{role} must be an object")
            continue
        for field in ("control_plane_pinned", "runtime_observed"):
            if not isinstance(actor.get(field), bool):
                errors.append(f"identity.{role}.{field} must be boolean")
        task_id = actor.get("task_id")
        if is_nonempty_string(task_id):
            task_ids.append(task_id)
        elif status == "complete":
            errors.append(f"identity.{role}.task_id is required for complete records")

        turn_ids = actor.get("turn_ids")
        valid_turn_ids = (
            isinstance(turn_ids, list)
            and all(is_nonempty_string(turn_id) for turn_id in turn_ids)
            and len(set(turn_ids)) == len(turn_ids)
        )
        if turn_ids is not None and not valid_turn_ids:
            errors.append(f"identity.{role}.turn_ids must contain unique non-empty strings")
        if valid_turn_ids:
            role_turn_ids[role] = turn_ids
            observed_turn_ids.extend(turn_ids)
        elif status == "complete":
            errors.append(f"identity.{role}.turn_ids is required for complete records")

        if status == "complete":
            if actor.get("control_plane_pinned") is not True:
                errors.append(f"identity.{role}.control_plane_pinned must be true for complete")
            if actor.get("runtime_observed") is not True:
                errors.append(f"identity.{role}.runtime_observed must be true for complete")
            if not is_nonempty_string(actor.get("value")):
                errors.append(f"identity.{role}.value is required for complete records")
            elif actor.get("value") not in EXPECTED_VALUES[role]:
                errors.append(f"identity.{role}.value does not match the stock CMRO route")
            if role == "root" and valid_turn_ids and not turn_ids:
                errors.append("identity.root.turn_ids must include at least one coordinator turn")
            if role != "root":
                preflight_turn_id = actor.get("preflight_turn_id")
                if not is_nonempty_string(preflight_turn_id):
                    errors.append(
                        f"identity.{role}.preflight_turn_id is required for complete records"
                    )
                elif valid_turn_ids and preflight_turn_id not in turn_ids:
                    errors.append(f"identity.{role}.preflight_turn_id must appear in turn_ids")
                if valid_turn_ids and len(turn_ids) < 2:
                    errors.append(
                        f"identity.{role}.turn_ids must include preflight and an action turn"
                    )

    if status == "complete" and len(task_ids) == len(ROLES) and len(set(task_ids)) != len(task_ids):
        errors.append("root, worker, and reviewer task IDs must be distinct")
    if status == "complete" and len(set(observed_turn_ids)) != len(observed_turn_ids):
        errors.append("observed turn IDs must be distinct across actors")
    if status == "complete":
        if value.get("worker_id") != identity.get("worker", {}).get("task_id"):
            errors.append("worker_id must match identity.worker.task_id")
        if value.get("reviewer_id") != identity.get("reviewer", {}).get("task_id"):
            errors.append("reviewer_id must match identity.reviewer.task_id")
        worker_turn_ids = role_turn_ids.get("worker", [])
        if worker_turn_ids and attempts != len(worker_turn_ids) - 1:
            errors.append("attempts must equal the number of observed worker action turns")
        reviewer_turn_ids = role_turn_ids.get("reviewer", [])
        if reviewer_turn_ids and attempts != len(reviewer_turn_ids) - 1:
            errors.append("attempts must equal the number of observed reviewer action turns")

    review_snapshots = value.get("review_snapshots")
    if status == "complete" and (not isinstance(review_snapshots, list) or not review_snapshots):
        errors.append("review_snapshots must contain every accepted review for complete records")
    elif isinstance(review_snapshots, list):
        snapshot_turn_ids: list[str] = []
        reviewer_turn_ids = role_turn_ids.get("reviewer", [])
        reviewer_preflight = identity.get("reviewer", {}).get("preflight_turn_id")
        expected_review_turn_ids = {
            turn_id for turn_id in reviewer_turn_ids if turn_id != reviewer_preflight
        }
        for index, snapshot in enumerate(review_snapshots):
            if not isinstance(snapshot, dict):
                errors.append(f"review_snapshots[{index}] must be an object")
                continue
            turn_id = snapshot.get("reviewer_turn_id")
            if not is_nonempty_string(turn_id):
                errors.append(f"review_snapshots[{index}].reviewer_turn_id is required")
            else:
                snapshot_turn_ids.append(turn_id)
            if snapshot.get("scope") != "tracked-index-and-untracked-content":
                errors.append(f"review_snapshots[{index}].scope is unsupported")
            before = snapshot.get("before_sha256")
            after = snapshot.get("after_sha256")
            if not isinstance(before, str) or not SHA256_RE.fullmatch(before):
                errors.append(f"review_snapshots[{index}].before_sha256 must be lowercase SHA-256")
            if not isinstance(after, str) or not SHA256_RE.fullmatch(after):
                errors.append(f"review_snapshots[{index}].after_sha256 must be lowercase SHA-256")
            if snapshot.get("matched") is not True or before != after:
                errors.append(f"review_snapshots[{index}] must contain matching digests")
        if status == "complete" and set(snapshot_turn_ids) != expected_review_turn_ids:
            errors.append("review_snapshots must cover every reviewer action turn exactly")
        if len(snapshot_turn_ids) != len(set(snapshot_turn_ids)):
            errors.append("review_snapshots cannot duplicate reviewer turn IDs")

    requirements = value.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty array")
    elif status == "complete":
        for index, item in enumerate(requirements):
            if not isinstance(item, dict) or item.get("status") != "pass":
                errors.append(f"requirements[{index}] must pass for complete records")
                continue
            if not is_nonempty_string(item.get("rq_id")):
                errors.append(f"requirements[{index}].rq_id must be a non-empty string")
            ac_ids = item.get("ac_ids")
            if not isinstance(ac_ids, list) or not ac_ids or not all(
                is_nonempty_string(ac_id) for ac_id in ac_ids
            ):
                errors.append(f"requirements[{index}].ac_ids must contain criterion IDs")

    if status == "complete" and not is_nonempty_string(value.get("verification_summary")):
        errors.append("verification_summary is required for complete records")

    blockers = value.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be an array")
    elif status == "complete" and blockers:
        errors.append("complete records cannot contain blockers")
    elif status == "needs_human_review" and not blockers:
        errors.append("needs_human_review records must explain at least one blocker")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a sanitized cmro.final.v3 JSON record.")
    parser.add_argument("record", type=Path, help="JSON file path, or - for stdin")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        raw = sys.stdin.read() if str(args.record) == "-" else args.record.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [f"cannot read JSON record: {exc}"]}, indent=2))
        return 2
    errors = validate(value)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
