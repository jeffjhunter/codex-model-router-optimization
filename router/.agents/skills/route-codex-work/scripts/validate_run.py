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
    uses_explicit_turn_accounting = "packet_repairs" in value or any(
        isinstance(identity.get(role), dict)
        and (
            "action_turn_ids" in identity[role]
            or "packet_repair_turn_ids" in identity[role]
        )
        for role in ("worker", "reviewer")
    )
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

    action_turn_ids: dict[str, list[str]] = {}
    packet_repair_turn_ids: dict[str, list[str]] = {}
    if uses_explicit_turn_accounting:
        for role in ("worker", "reviewer"):
            actor = identity.get(role)
            if not isinstance(actor, dict):
                continue
            for field, destination in (
                ("action_turn_ids", action_turn_ids),
                ("packet_repair_turn_ids", packet_repair_turn_ids),
            ):
                turn_ids = actor.get(field)
                valid_ids = (
                    isinstance(turn_ids, list)
                    and all(is_nonempty_string(turn_id) for turn_id in turn_ids)
                    and len(set(turn_ids)) == len(turn_ids)
                )
                if not valid_ids:
                    errors.append(
                        f"identity.{role}.{field} must contain unique non-empty strings"
                    )
                    continue
                destination[role] = turn_ids

            actions = action_turn_ids.get(role)
            repairs = packet_repair_turn_ids.get(role)
            observed = role_turn_ids.get(role)
            preflight_turn_id = actor.get("preflight_turn_id")
            if actions is None or repairs is None:
                continue
            overlap = set(actions) & set(repairs)
            if overlap:
                errors.append(
                    f"identity.{role}.action_turn_ids and packet_repair_turn_ids cannot overlap"
                )
            if is_nonempty_string(preflight_turn_id) and (
                preflight_turn_id in actions or preflight_turn_id in repairs
            ):
                errors.append(
                    f"identity.{role} action and packet repair turn IDs must exclude preflight"
                )
            if observed is not None:
                observed_set = set(observed)
                for field, ids in (
                    ("action_turn_ids", actions),
                    ("packet_repair_turn_ids", repairs),
                ):
                    if not set(ids) <= observed_set:
                        errors.append(
                            f"identity.{role}.{field} must be observed in identity.{role}.turn_ids"
                        )
                non_preflight_ids = {
                    turn_id for turn_id in observed if turn_id != preflight_turn_id
                }
                if set(actions) | set(repairs) != non_preflight_ids:
                    errors.append(
                        f"identity.{role} explicit turn accounting must classify every "
                        "non-preflight turn"
                    )
            elif actions or repairs:
                errors.append(
                    f"identity.{role} action and packet repair turn IDs must be observed "
                    f"in identity.{role}.turn_ids"
                )

        all_explicit_turn_ids = [
            turn_id
            for role in ("worker", "reviewer")
            for turn_id in action_turn_ids.get(role, [])
            + packet_repair_turn_ids.get(role, [])
        ]
        if len(all_explicit_turn_ids) != len(set(all_explicit_turn_ids)):
            errors.append("action and packet repair turn IDs must be distinct across actors")

        worker_actions = action_turn_ids.get("worker")
        if worker_actions is not None and attempts != len(worker_actions):
            errors.append("attempts must equal identity.worker.action_turn_ids count")
        reviewer_actions = action_turn_ids.get("reviewer")
        if (
            reviewer_actions is not None
            and isinstance(attempts, int)
            and not isinstance(attempts, bool)
            and len(reviewer_actions) > attempts
        ):
            errors.append("reviewer action turns cannot exceed worker attempts")

        packet_repairs = value.get("packet_repairs")
        if not isinstance(packet_repairs, list):
            errors.append("packet_repairs must be an array for explicit turn accounting")
            packet_repairs = []
        seen_invalid_packets: set[tuple[str, str]] = set()
        seen_repaired_packets: set[tuple[str, str]] = set()
        for index, repair in enumerate(packet_repairs):
            if not isinstance(repair, dict):
                errors.append(f"packet_repairs[{index}] must be an object")
                continue
            required_repair_fields = {
                "actor_role",
                "invalid_turn_id",
                "repaired_turn_id",
                "mode",
                "writes",
                "reason",
                "snapshot",
            }
            missing_repair_fields = sorted(required_repair_fields - repair.keys())
            unknown_repair_fields = sorted(repair.keys() - required_repair_fields)
            for field in missing_repair_fields:
                errors.append(f"packet_repairs[{index}].{field} is required")
            for field in unknown_repair_fields:
                errors.append(f"packet_repairs[{index}].{field} is not allowed")
            actor_role = repair.get("actor_role")
            if actor_role not in {"worker", "reviewer"}:
                errors.append(f"packet_repairs[{index}].actor_role must be worker or reviewer")
                actor_role = None
            invalid_turn_id = repair.get("invalid_turn_id")
            if not is_nonempty_string(invalid_turn_id):
                errors.append(f"packet_repairs[{index}].invalid_turn_id is required")
            repaired_turn_id = repair.get("repaired_turn_id")
            if not is_nonempty_string(repaired_turn_id):
                errors.append(f"packet_repairs[{index}].repaired_turn_id is required")
            if repair.get("mode") != "format-only":
                errors.append(f"packet_repairs[{index}].mode must be format-only")
            if repair.get("writes") is not False:
                errors.append(f"packet_repairs[{index}].writes must be false")
            if not is_nonempty_string(repair.get("reason")):
                errors.append(f"packet_repairs[{index}].reason must be a non-empty string")
            snapshot = repair.get("snapshot")
            if not isinstance(snapshot, dict):
                errors.append(f"packet_repairs[{index}].snapshot must be an object")
            else:
                snapshot_fields = {"scope", "before_sha256", "after_sha256", "matched"}
                for field in sorted(snapshot_fields - snapshot.keys()):
                    errors.append(f"packet_repairs[{index}].snapshot.{field} is required")
                for field in sorted(snapshot.keys() - snapshot_fields):
                    errors.append(f"packet_repairs[{index}].snapshot.{field} is not allowed")
                before = snapshot.get("before_sha256")
                after = snapshot.get("after_sha256")
                if snapshot.get("scope") != "tracked-index-and-untracked-content":
                    errors.append(f"packet_repairs[{index}].snapshot.scope is unsupported")
                if not isinstance(before, str) or not SHA256_RE.fullmatch(before):
                    errors.append(
                        f"packet_repairs[{index}].snapshot.before_sha256 must be lowercase SHA-256"
                    )
                if not isinstance(after, str) or not SHA256_RE.fullmatch(after):
                    errors.append(
                        f"packet_repairs[{index}].snapshot.after_sha256 must be lowercase SHA-256"
                    )
                if snapshot.get("matched") is not True or before != after:
                    errors.append(
                        f"packet_repairs[{index}].snapshot must contain matching digests"
                    )

            if (
                actor_role is None
                or not is_nonempty_string(invalid_turn_id)
                or not is_nonempty_string(repaired_turn_id)
            ):
                continue
            invalid_key = (actor_role, invalid_turn_id)
            repaired_key = (actor_role, repaired_turn_id)
            if invalid_key in seen_invalid_packets:
                errors.append("packet_repairs allows at most one repair per invalid action packet")
            seen_invalid_packets.add(invalid_key)
            if repaired_key in seen_repaired_packets:
                errors.append("packet_repairs cannot account for a repaired turn more than once")
            seen_repaired_packets.add(repaired_key)
            if invalid_turn_id not in action_turn_ids.get(actor_role, []):
                errors.append(
                    f"packet_repairs[{index}].invalid_turn_id must reference that actor's "
                    "action_turn_ids"
                )
            if repaired_turn_id not in packet_repair_turn_ids.get(actor_role, []):
                errors.append(
                    f"packet_repairs[{index}].repaired_turn_id must reference that actor's "
                    "packet_repair_turn_ids"
                )

        for role in ("worker", "reviewer"):
            recorded_repair_ids = {
                repaired_turn_id
                for actor_role, repaired_turn_id in seen_repaired_packets
                if actor_role == role
            }
            if set(packet_repair_turn_ids.get(role, [])) != recorded_repair_ids:
                errors.append(
                    f"identity.{role}.packet_repair_turn_ids must each have exactly one "
                    "packet_repairs record"
                )

    if status == "complete":
        if value.get("worker_id") != identity.get("worker", {}).get("task_id"):
            errors.append("worker_id must match identity.worker.task_id")
        if value.get("reviewer_id") != identity.get("reviewer", {}).get("task_id"):
            errors.append("reviewer_id must match identity.reviewer.task_id")
        worker_turn_ids = role_turn_ids.get("worker", [])
        if (
            not uses_explicit_turn_accounting
            and worker_turn_ids
            and attempts != len(worker_turn_ids) - 1
        ):
            errors.append("attempts must equal the number of observed worker action turns")
        reviewer_turn_ids = role_turn_ids.get("reviewer", [])
        if (
            uses_explicit_turn_accounting
            and "reviewer" in action_turn_ids
            and attempts != len(action_turn_ids["reviewer"])
        ):
            errors.append("attempts must equal identity.reviewer.action_turn_ids count")
        elif (
            not uses_explicit_turn_accounting
            and reviewer_turn_ids
            and attempts != len(reviewer_turn_ids) - 1
        ):
            errors.append("attempts must equal the number of observed reviewer action turns")

    review_snapshots = value.get("review_snapshots")
    reviewer_actions_for_snapshots = action_turn_ids.get("reviewer", [])
    snapshots_required = status == "complete" or (
        uses_explicit_turn_accounting and bool(reviewer_actions_for_snapshots)
    )
    if snapshots_required and (not isinstance(review_snapshots, list) or not review_snapshots):
        errors.append("review_snapshots must contain every reviewer action turn")
    elif isinstance(review_snapshots, list):
        snapshot_turn_ids: list[str] = []
        reviewer_turn_ids = role_turn_ids.get("reviewer", [])
        reviewer_preflight = identity.get("reviewer", {}).get("preflight_turn_id")
        expected_review_turn_ids = (
            set(reviewer_actions_for_snapshots)
            if uses_explicit_turn_accounting
            else {turn_id for turn_id in reviewer_turn_ids if turn_id != reviewer_preflight}
        )
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
        if (status == "complete" or uses_explicit_turn_accounting) and (
            set(snapshot_turn_ids) != expected_review_turn_ids
        ):
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
