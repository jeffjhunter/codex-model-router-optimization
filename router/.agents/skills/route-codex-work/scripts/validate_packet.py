#!/usr/bin/env python3
"""Validate one raw CMRO v3 worker or reviewer JSON packet.

The optional authoritative context is deliberately separate from the packet.  A
packet cannot make its own run, actor, route, scope, or acceptance claims true.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


SUPPORTED_BACKENDS = {"codex_app_tasks", "native_custom_agent"}
WORKER_ROUTES = {
    "luna_worker": "gpt-5.6-luna",
    "terra_worker": "gpt-5.6-terra",
}
REVIEWER_ROUTES = {"sol_reviewer": "gpt-5.6-sol"}
CHANGED_PATH_ACTIONS = {"created", "modified", "deleted", "renamed"}
CHECK_RESULTS = {"pass", "fail", "not_run"}
CRITERION_STATUSES = {"pass", "fail", "not_verified"}
REVIEW_DECISIONS = {"accept", "revise", "needs_human_review"}
FINDING_SEVERITIES = {"critical", "high", "medium", "low"}
DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def object_shape(
    value: Any,
    label: str,
    required: set[str],
    optional: set[str],
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    for field in missing:
        errors.append(f"{label}.{field} is required")
    for field in unknown:
        errors.append(f"{label}.{field} is not allowed")
    return value


def validate_string_array(
    value: Any,
    label: str,
    errors: list[str],
    *,
    nonempty: bool = False,
    unique: bool = False,
) -> list[str] | None:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return None
    if nonempty and not value:
        errors.append(f"{label} must not be empty")
    if not all(is_nonempty_string(item) for item in value):
        errors.append(f"{label} must contain only non-empty strings")
        return None
    if unique and len(set(value)) != len(value):
        errors.append(f"{label} must not contain duplicates")
    return value


def unsafe_repo_path(value: str, *, allow_glob: bool) -> str | None:
    if "\x00" in value:
        return "must not contain NUL"
    if "\\" in value:
        return "must use forward slashes"
    if value.startswith("/") or DRIVE_PREFIX_RE.match(value):
        return "must be repository-relative"
    if not allow_glob and any(character in value for character in "*?["):
        return "must identify one concrete path, not a glob"
    candidate = value[:-1] if allow_glob and value.endswith("/") else value
    if not candidate or candidate.startswith("./") or candidate.endswith("/"):
        return "must be a normalized repository-relative path"
    segments = candidate.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return "must not contain empty, current-directory, or parent segments"
    return None


def path_matches(path: str, allowed_pattern: str) -> bool:
    if allowed_pattern.endswith("/"):
        return path.startswith(allowed_pattern)
    path_segments = tuple(path.split("/"))
    pattern_segments = tuple(allowed_pattern.split("/"))

    @lru_cache(maxsize=None)
    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_segments):
            return path_index == len(path_segments)
        pattern_segment = pattern_segments[pattern_index]
        if pattern_segment == "**":
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path_segments)
                and matches(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_segments)
            and fnmatch.fnmatchcase(path_segments[path_index], pattern_segment)
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)


def validate_context(value: Any, kind: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    required = {
        "run_id",
        "plan_version",
        "backend",
        "actor_id",
        "route",
        "configured_model",
        "acceptance_ids",
    }
    if kind == "worker":
        required.update({"attempt", "allowed_paths"})
    context = object_shape(value, "context", required, set(), errors)
    if context is None:
        return None, errors

    if not is_nonempty_string(context.get("run_id")):
        errors.append("context.run_id must be a non-empty string")
    if not is_positive_integer(context.get("plan_version")):
        errors.append("context.plan_version must be a positive integer")
    if context.get("backend") not in SUPPORTED_BACKENDS:
        errors.append("context.backend must identify a supported orchestration backend")
    if not is_nonempty_string(context.get("actor_id")):
        errors.append("context.actor_id must be a non-empty string")

    routes = WORKER_ROUTES if kind == "worker" else REVIEWER_ROUTES
    route = context.get("route")
    if route not in routes:
        errors.append(f"context.route must be a supported {kind} route")
    elif context.get("configured_model") != routes[route]:
        errors.append("context.configured_model does not match context.route")

    acceptance_ids = validate_string_array(
        context.get("acceptance_ids"),
        "context.acceptance_ids",
        errors,
        nonempty=True,
        unique=True,
    )
    if acceptance_ids is not None and any(not item.startswith("AC-") for item in acceptance_ids):
        errors.append("context.acceptance_ids must contain AC-* identifiers")

    if kind == "worker":
        if not is_positive_integer(context.get("attempt")):
            errors.append("context.attempt must be a positive integer")
        allowed_paths = validate_string_array(
            context.get("allowed_paths"),
            "context.allowed_paths",
            errors,
            nonempty=True,
            unique=True,
        )
        if allowed_paths is not None:
            for index, pattern in enumerate(allowed_paths):
                reason = unsafe_repo_path(pattern, allow_glob=True)
                if reason:
                    errors.append(f"context.allowed_paths[{index}] {reason}")
    return context, errors


def validate_actor(
    value: Any,
    kind: str,
    context: dict[str, Any] | None,
    errors: list[str],
) -> None:
    label = kind
    actor = object_shape(
        value,
        label,
        {"id", "backend", "route", "configured_model"},
        set(),
        errors,
    )
    if actor is None:
        return
    if not is_nonempty_string(actor.get("id")):
        errors.append(f"{label}.id must be a non-empty retained actor ID")
    if actor.get("backend") not in SUPPORTED_BACKENDS:
        errors.append(f"{label}.backend must identify a supported orchestration backend")
    routes = WORKER_ROUTES if kind == "worker" else REVIEWER_ROUTES
    route = actor.get("route")
    if route not in routes:
        errors.append(f"{label}.route must be a supported {kind} route")
    elif actor.get("configured_model") != routes[route]:
        errors.append(f"{label}.configured_model does not match {label}.route")

    if context is not None:
        comparisons = {
            "id": "actor_id",
            "backend": "backend",
            "route": "route",
            "configured_model": "configured_model",
        }
        for packet_field, context_field in comparisons.items():
            if actor.get(packet_field) != context.get(context_field):
                errors.append(
                    f"{label}.{packet_field} does not match authoritative context.{context_field}"
                )


def validate_checks(value: Any, label: str, errors: list[str], *, evidence_required: bool) -> None:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        required = {"command", "exit_code", "result"}
        optional = {"evidence"}
        if evidence_required:
            required.add("evidence")
            optional.remove("evidence")
        check = object_shape(item, item_label, required, optional, errors)
        if check is None:
            continue
        if not is_nonempty_string(check.get("command")):
            errors.append(f"{item_label}.command must be a non-empty string")
        result = check.get("result")
        if result not in CHECK_RESULTS:
            errors.append(f"{item_label}.result must be pass, fail, or not_run")
        exit_code = check.get("exit_code")
        valid_integer_exit = isinstance(exit_code, int) and not isinstance(exit_code, bool)
        if result == "not_run":
            if exit_code is not None:
                errors.append(f"{item_label}.exit_code must be null when result is not_run")
        elif not valid_integer_exit:
            errors.append(f"{item_label}.exit_code must be an integer for an executed check")
        elif result == "pass" and exit_code != 0:
            errors.append(f"{item_label}.exit_code must be 0 when result is pass")
        elif result == "fail" and exit_code == 0:
            errors.append(f"{item_label}.exit_code must be nonzero when result is fail")
        if "evidence" in check and not is_nonempty_string(check.get("evidence")):
            errors.append(f"{item_label}.evidence must be a non-empty string")


def validate_criteria(
    value: Any,
    context: dict[str, Any] | None,
    errors: list[str],
) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(value, list):
        errors.append("criteria must be an array")
        return [], set()
    if not value:
        errors.append("criteria must not be empty")
    criteria: list[dict[str, Any]] = []
    ids: list[str] = []
    for index, item in enumerate(value):
        label = f"criteria[{index}]"
        criterion = object_shape(item, label, {"ac_id", "status", "evidence"}, set(), errors)
        if criterion is None:
            continue
        criteria.append(criterion)
        ac_id = criterion.get("ac_id")
        if not is_nonempty_string(ac_id) or not ac_id.startswith("AC-"):
            errors.append(f"{label}.ac_id must be an AC-* identifier")
        else:
            ids.append(ac_id)
        if criterion.get("status") not in CRITERION_STATUSES:
            errors.append(f"{label}.status must be pass, fail, or not_verified")
        if not is_nonempty_string(criterion.get("evidence")):
            errors.append(f"{label}.evidence must be a non-empty string")
    if len(ids) != len(set(ids)):
        errors.append("criteria must not duplicate acceptance criterion IDs")
    id_set = set(ids)
    if context is not None and isinstance(context.get("acceptance_ids"), list):
        expected = set(context["acceptance_ids"])
        missing = sorted(expected - id_set)
        extra = sorted(id_set - expected)
        if missing:
            errors.append("criteria are missing authoritative acceptance IDs: " + ", ".join(missing))
        if extra:
            errors.append("criteria contain acceptance IDs outside authoritative context: " + ", ".join(extra))
    return criteria, id_set


def validate_common_context(
    packet: dict[str, Any],
    context: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if not is_nonempty_string(packet.get("run_id")):
        errors.append("run_id must be a non-empty string")
    if not is_positive_integer(packet.get("plan_version")):
        errors.append("plan_version must be a positive integer")
    if context is not None:
        if packet.get("run_id") != context.get("run_id"):
            errors.append("run_id does not match authoritative context.run_id")
        if packet.get("plan_version") != context.get("plan_version"):
            errors.append("plan_version does not match authoritative context.plan_version")


def validate_changed_paths(
    value: Any,
    context: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append("changed_paths must be an array")
        return
    paths: list[str] = []
    for index, item in enumerate(value):
        label = f"changed_paths[{index}]"
        change = object_shape(item, label, {"path", "action"}, set(), errors)
        if change is None:
            continue
        path = change.get("path")
        if not is_nonempty_string(path):
            errors.append(f"{label}.path must be a non-empty string")
        else:
            reason = unsafe_repo_path(path, allow_glob=False)
            if reason:
                errors.append(f"{label}.path {reason}")
            else:
                paths.append(path)
                if context is not None and isinstance(context.get("allowed_paths"), list):
                    if not any(path_matches(path, pattern) for pattern in context["allowed_paths"]):
                        errors.append(f"{label}.path is outside authoritative allowed_paths")
        if change.get("action") not in CHANGED_PATH_ACTIONS:
            errors.append(
                f"{label}.action must be one of: " + ", ".join(sorted(CHANGED_PATH_ACTIONS))
            )
    if len(paths) != len(set(paths)):
        errors.append("changed_paths must not contain duplicate paths")


def validate_worker(packet: dict[str, Any], context: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "run_id",
        "plan_version",
        "attempt",
        "worker",
        "status",
        "summary",
        "changed_paths",
        "checks",
        "criteria",
        "blockers",
        "limitations",
    }
    if object_shape(packet, "packet", required, set(), errors) is None:
        return errors
    if packet.get("schema") != "cmro.worker.v3":
        errors.append("schema must be cmro.worker.v3")
    validate_common_context(packet, context, errors)
    if not is_positive_integer(packet.get("attempt")):
        errors.append("attempt must be a positive integer")
    elif context is not None and packet.get("attempt") != context.get("attempt"):
        errors.append("attempt does not match authoritative context.attempt")
    validate_actor(packet.get("worker"), "worker", context, errors)

    status = packet.get("status")
    if status not in {"done", "blocked"}:
        errors.append("status must be done or blocked")
    if not is_nonempty_string(packet.get("summary")):
        errors.append("summary must be a non-empty string")
    validate_changed_paths(packet.get("changed_paths"), context, errors)
    validate_checks(packet.get("checks"), "checks", errors, evidence_required=True)
    validate_criteria(packet.get("criteria"), context, errors)
    blockers = validate_string_array(packet.get("blockers"), "blockers", errors)
    validate_string_array(packet.get("limitations"), "limitations", errors)
    if blockers is not None:
        if status == "blocked" and not blockers:
            errors.append("blocked worker packets must contain at least one blocker")
        if status == "done" and blockers:
            errors.append("done worker packets cannot contain blockers")
    return errors


def validate_findings(value: Any, criterion_ids: set[str], errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("findings must be an array")
        return []
    findings: list[dict[str, Any]] = []
    finding_ids: list[str] = []
    for index, item in enumerate(value):
        label = f"findings[{index}]"
        finding = object_shape(
            item,
            label,
            {"id", "severity", "ac_ids", "evidence", "requested_outcome"},
            set(),
            errors,
        )
        if finding is None:
            continue
        findings.append(finding)
        finding_id = finding.get("id")
        if not is_nonempty_string(finding_id) or not finding_id.startswith("F-"):
            errors.append(f"{label}.id must be an F-* identifier")
        else:
            finding_ids.append(finding_id)
        if finding.get("severity") not in FINDING_SEVERITIES:
            errors.append(f"{label}.severity must be critical, high, medium, or low")
        ac_ids = validate_string_array(
            finding.get("ac_ids"),
            f"{label}.ac_ids",
            errors,
            nonempty=True,
            unique=True,
        )
        if ac_ids is not None:
            unknown = sorted(set(ac_ids) - criterion_ids)
            if unknown:
                errors.append(f"{label}.ac_ids reference unknown criteria: " + ", ".join(unknown))
        if not is_nonempty_string(finding.get("evidence")):
            errors.append(f"{label}.evidence must be a non-empty string")
        if not is_nonempty_string(finding.get("requested_outcome")):
            errors.append(f"{label}.requested_outcome must be a non-empty string")
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("findings must not contain duplicate IDs")
    return findings


def validate_review(packet: dict[str, Any], context: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "run_id",
        "plan_version",
        "reviewer",
        "decision",
        "criteria",
        "findings",
        "verification",
        "blockers",
        "limitations",
    }
    if object_shape(packet, "packet", required, set(), errors) is None:
        return errors
    if packet.get("schema") != "cmro.review.v3":
        errors.append("schema must be cmro.review.v3")
    validate_common_context(packet, context, errors)
    validate_actor(packet.get("reviewer"), "reviewer", context, errors)
    decision = packet.get("decision")
    if decision not in REVIEW_DECISIONS:
        errors.append("decision must be accept, revise, or needs_human_review")
    criteria, criterion_ids = validate_criteria(packet.get("criteria"), context, errors)
    findings = validate_findings(packet.get("findings"), criterion_ids, errors)
    verification = packet.get("verification")
    validate_checks(verification, "verification", errors, evidence_required=True)
    blockers = validate_string_array(packet.get("blockers"), "blockers", errors)
    validate_string_array(packet.get("limitations"), "limitations", errors)

    if decision == "accept":
        if any(criterion.get("status") != "pass" for criterion in criteria):
            errors.append("accept requires every acceptance criterion to pass")
        if findings:
            errors.append("accept requires findings to be empty")
        if blockers:
            errors.append("accept requires blockers to be empty")
        if not isinstance(verification, list) or not verification:
            errors.append("accept requires at least one passing verification result")
        elif any(
            not isinstance(item, dict) or item.get("result") != "pass"
            for item in verification
        ):
            errors.append("accept requires every verification result to pass")
    elif decision == "revise":
        if not findings:
            errors.append("revise requires at least one finding")
        nonpassing_ids = {
            criterion.get("ac_id")
            for criterion in criteria
            if criterion.get("status") in {"fail", "not_verified"}
        }
        if not nonpassing_ids:
            errors.append("revise requires at least one non-passing acceptance criterion")
        for index, finding in enumerate(findings):
            finding_ac_ids = finding.get("ac_ids")
            if isinstance(finding_ac_ids, list) and not set(finding_ac_ids) <= nonpassing_ids:
                errors.append(
                    f"findings[{index}].ac_ids must reference only non-passing criteria for revise"
                )
    elif decision == "needs_human_review" and not findings and not blockers:
        errors.append("needs_human_review requires at least one finding or blocker")
    return errors


def validate(packet: Any, context_value: Any | None = None) -> list[str]:
    if not isinstance(packet, dict):
        return ["packet must be a JSON object"]
    schema = packet.get("schema")
    if schema == "cmro.worker.v3":
        kind = "worker"
    elif schema == "cmro.review.v3":
        kind = "reviewer"
    else:
        return ["schema must be cmro.worker.v3 or cmro.review.v3"]

    context: dict[str, Any] | None = None
    context_errors: list[str] = []
    if context_value is not None:
        context, context_errors = validate_context(context_value, kind)
    packet_errors = validate_worker(packet, context) if kind == "worker" else validate_review(packet, context)
    return context_errors + packet_errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a raw cmro.worker.v3 or cmro.review.v3 JSON packet. "
            "Without context, only intrinsic packet shape is checked."
        )
    )
    parser.add_argument("packet", type=Path, help="packet JSON path, or - for stdin")
    context_group = parser.add_mutually_exclusive_group()
    context_group.add_argument("--context", type=Path, help="authoritative context JSON path")
    context_group.add_argument("--context-json", help="authoritative context as a JSON argument")
    return parser.parse_args(argv)


def read_json(path: Path, label: str) -> Any:
    raw = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse {label} JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        packet = read_json(args.packet, "packet")
        if args.context is not None:
            if str(args.packet) == "-" and str(args.context) == "-":
                raise ValueError("packet and context cannot both read from stdin")
            context_value = read_json(args.context, "context")
        elif args.context_json is not None:
            try:
                context_value = json.loads(args.context_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"cannot parse context JSON: {exc}") from exc
        else:
            context_value = None
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 2

    errors = validate(packet, context_value)
    print(
        json.dumps(
            {
                "valid": not errors,
                "authoritative_context_bound": context_value is not None,
                "errors": errors,
            },
            indent=2,
        )
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
