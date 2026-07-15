#!/usr/bin/env python3
"""Read only model identity metadata from a local Codex session log.

The script intentionally ignores prompts, messages, tool arguments, and tool output.
It emits only session metadata and turn-context fields needed by CMRO's identity gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


THREAD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,127}$")


def default_sessions_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "sessions"
    return Path.home() / ".codex" / "sessions"


def canonical_path(value: str | Path) -> str:
    return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))


def display_path(path: Path) -> str:
    resolved = path.expanduser().resolve(strict=False)
    home = Path.home().resolve(strict=False)
    try:
        return str(Path("~") / resolved.relative_to(home))
    except ValueError:
        return str(resolved)


def read_evidence(path: Path, thread_id: str) -> dict[str, Any] | None:
    session_meta: dict[str, Any] | None = None
    session_meta_line: int | None = None
    contexts: list[dict[str, Any]] = []

    task_started_turns: set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                try:
                    record = json.loads(raw_line)
                except (TypeError, ValueError):
                    continue
                if not isinstance(record, dict):
                    continue

                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue

                if record.get("type") == "session_meta" and payload.get("id") == thread_id:
                    session_meta = payload
                    session_meta_line = line_number
                elif record.get("type") == "event_msg" and payload.get("type") == "task_started":
                    turn_id = payload.get("turn_id")
                    if isinstance(turn_id, str):
                        task_started_turns.add(turn_id)
                elif record.get("type") == "turn_context":
                    turn_id = payload.get("turn_id")
                    contexts.append(
                        {
                            "line": line_number,
                            "turn_id": turn_id,
                            "task_started": turn_id in task_started_turns,
                            "model": payload.get("model"),
                            "effort": payload.get("effort", payload.get("reasoning_effort")),
                            "cwd": payload.get("cwd"),
                        }
                    )
    except (OSError, UnicodeError):
        return None

    if session_meta is None:
        return None

    selected = contexts[-1] if contexts else None
    return {
        "schema": "cmro.session-observation.v1",
        "status": "verified" if selected and selected.get("model") else "not_ready",
        "thread_id": thread_id,
        "session": {
            "id": session_meta.get("id"),
            "parent_thread_id_present": bool(session_meta.get("parent_thread_id")),
            "cwd": session_meta.get("cwd"),
            "line": session_meta_line,
        },
        "_parent_thread_id": session_meta.get("parent_thread_id"),
        "source": {"path": display_path(path), "turn_context_count": len(contexts)},
        "selected_turn_context": selected,
        "turn_contexts": contexts,
    }


def locate_evidence(sessions_root: Path, thread_id: str) -> dict[str, Any] | None:
    if not sessions_root.is_dir():
        return None

    candidates: list[tuple[int, Path, dict[str, Any]]] = []
    try:
        paths = sessions_root.rglob(f"*{thread_id}*.jsonl")
        for path in paths:
            if not path.is_file():
                continue
            evidence = read_evidence(path, thread_id)
            if evidence is None:
                continue
            try:
                modified = path.stat().st_mtime_ns
            except OSError:
                modified = 0
            candidates.append((modified, path, evidence))
    except OSError:
        return None

    if not candidates:
        return None
    if len(candidates) > 1:
        return {
            "schema": "cmro.session-observation.v1",
            "status": "ambiguous",
            "thread_id": thread_id,
            "candidate_count": len(candidates),
            "candidates": [display_path(item[1]) for item in candidates],
        }
    candidates.sort(key=lambda item: (item[0], str(item[1])))
    return candidates[-1][2]


def select_expected_turn(evidence: dict[str, Any], turn_id: str | None) -> None:
    contexts = evidence.get("turn_contexts") or []
    if turn_id:
        matches = [item for item in contexts if item.get("turn_id") == turn_id]
        selected = matches[-1] if matches else None
    else:
        selected = contexts[-1] if contexts else None
    evidence["selected_turn_context"] = selected
    evidence["status"] = "verified" if selected and selected.get("model") else "not_ready"


def evaluate_expectations(evidence: dict[str, Any], args: argparse.Namespace) -> list[str]:
    selected = evidence.get("selected_turn_context") or {}
    mismatches: list[str] = []
    if args.expect_turn_id and selected.get("turn_id") != args.expect_turn_id:
        mismatches.append(
            f"turn_id expected {args.expect_turn_id!r}, observed {selected.get('turn_id')!r}"
        )
    if selected and not selected.get("task_started"):
        mismatches.append("selected turn_context has no preceding task_started record")
    if args.expect_model and selected.get("model") != args.expect_model:
        mismatches.append(
            f"model expected {args.expect_model!r}, observed {selected.get('model')!r}"
        )
    if args.expect_effort and selected.get("effort") != args.expect_effort:
        mismatches.append(
            f"effort expected {args.expect_effort!r}, observed {selected.get('effort')!r}"
        )
    if args.expect_cwd:
        observed_cwd = selected.get("cwd")
        if not observed_cwd or canonical_path(observed_cwd) != canonical_path(args.expect_cwd):
            mismatches.append(
                f"cwd expected {canonical_path(args.expect_cwd)!r}, "
                f"observed {canonical_path(observed_cwd) if observed_cwd else None!r}"
            )
        session_cwd = (evidence.get("session") or {}).get("cwd")
        if not session_cwd or canonical_path(session_cwd) != canonical_path(args.expect_cwd):
            mismatches.append(
                f"session cwd expected {canonical_path(args.expect_cwd)!r}, "
                f"observed {canonical_path(session_cwd) if session_cwd else None!r}"
            )
    parent_thread_id = evidence.get("_parent_thread_id")
    if parent_thread_id and not args.expect_turn_id:
        mismatches.append("forked sessions require --expect-turn-id to reject inherited context")
    if args.expect_top_level and parent_thread_id:
        mismatches.append("expected a top-level app task, observed a forked child session")
    if args.expect_parent_thread_id and parent_thread_id != args.expect_parent_thread_id:
        mismatches.append("observed parent thread does not match expected parent thread")
    return mismatches


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit privacy-minimized runtime model evidence for one local Codex task."
    )
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--sessions-root", type=Path, default=default_sessions_root())
    parser.add_argument("--expect-model")
    parser.add_argument("--expect-effort")
    parser.add_argument("--expect-cwd")
    parser.add_argument("--expect-turn-id")
    parent = parser.add_mutually_exclusive_group()
    parent.add_argument(
        "--expect-top-level",
        action="store_true",
        help="Require session_meta.parent_thread_id to be absent (Codex app task backend).",
    )
    parent.add_argument("--expect-parent-thread-id")
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=0,
        help="Poll for a matching turn_context for at most this many seconds (maximum 60).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not THREAD_ID_RE.fullmatch(args.thread_id):
        print(json.dumps({"status": "error", "error": "invalid thread id"}, indent=2))
        return 2
    if args.wait_seconds < 0 or args.wait_seconds > 60:
        print(json.dumps({"status": "error", "error": "wait-seconds must be 0..60"}, indent=2))
        return 2

    deadline = time.monotonic() + args.wait_seconds
    evidence: dict[str, Any] | None = None
    while True:
        evidence = locate_evidence(args.sessions_root.expanduser(), args.thread_id)
        if evidence and evidence.get("status") not in {"ambiguous"}:
            select_expected_turn(evidence, args.expect_turn_id)
            mismatches = evaluate_expectations(evidence, args)
            selected = evidence.get("selected_turn_context")
            if evidence.get("status") == "verified" and not mismatches:
                break
            if args.expect_turn_id and selected and selected.get("turn_id") == args.expect_turn_id:
                break
        elif evidence and evidence.get("status") == "ambiguous":
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)

    if evidence is None:
        evidence = {
            "schema": "cmro.session-observation.v1",
            "status": "not_found",
            "thread_id": args.thread_id,
            "sessions_root": display_path(args.sessions_root),
        }
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 2

    mismatches = evaluate_expectations(evidence, args)
    evidence.pop("_parent_thread_id", None)
    evidence["expectation_status"] = "match" if not mismatches else "mismatch"
    evidence["mismatches"] = mismatches
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if evidence.get("status") != "verified":
        return 2
    return 3 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
