#!/usr/bin/env python3
"""Create a privacy-minimized content snapshot of a Git worktree.

The snapshot covers the Git index plus the raw contents of tracked and
non-ignored untracked artifacts. It emits digests and counts, never paths or
file contents, so a coordinator can detect reviewer-time mutations without
persisting repository data in an orchestration record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


SCOPE = "tracked-index-and-untracked-content"


class SnapshotError(RuntimeError):
    """Raised when a stable, bounded snapshot cannot be produced."""


def run_git(cwd: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise SnapshotError(f"cannot execute Git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SnapshotError(detail or f"Git command failed with exit {result.returncode}")
    return result.stdout


def split_nul(value: bytes) -> list[bytes]:
    return [item for item in value.split(b"\0") if item]


def decode_path(value: bytes) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        return os.fsdecode(value)


def hash_regular_file(path: Path, before: os.stat_result) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        after = path.lstat()
    except OSError as exc:
        raise SnapshotError(f"cannot read an indexed worktree artifact: {exc}") from exc
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise SnapshotError("worktree changed while its snapshot was being computed")
    return digest.hexdigest()


def artifact_record(root: Path, relative_bytes: bytes) -> bytes:
    relative = decode_path(relative_bytes)
    candidate = root / Path(relative)
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        kind = "missing"
        content_digest = "-"
        mode = 0
    except OSError as exc:
        raise SnapshotError(f"cannot inspect an indexed worktree artifact: {exc}") from exc
    else:
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):
            kind = "file"
            content_digest = hash_regular_file(candidate, info)
        elif stat.S_ISLNK(info.st_mode):
            kind = "symlink"
            try:
                target = os.readlink(candidate)
            except OSError as exc:
                raise SnapshotError(f"cannot read a worktree symlink: {exc}") from exc
            content_digest = hashlib.sha256(os.fsencode(target)).hexdigest()
        elif stat.S_ISDIR(info.st_mode):
            # Gitlink/submodule contents are outside this snapshot's declared scope.
            kind = "directory"
            content_digest = "-"
        else:
            raise SnapshotError("unsupported special file in tracked or untracked artifacts")
    return b"\0".join(
        (
            relative_bytes,
            kind.encode("ascii"),
            str(mode).encode("ascii"),
            content_digest.encode("ascii"),
        )
    )


def snapshot(cwd: Path) -> dict[str, object]:
    root_raw = run_git(cwd, "rev-parse", "--show-toplevel").rstrip(b"\r\n")
    if not root_raw:
        raise SnapshotError("Git did not return a repository root")
    root = Path(decode_path(root_raw)).resolve(strict=True)

    tracked = split_nul(run_git(root, "ls-files", "-z", "--cached"))
    untracked = split_nul(run_git(root, "ls-files", "-z", "--others", "--exclude-standard"))
    relative_paths = sorted(set(tracked + untracked))

    worktree = hashlib.sha256()
    for relative_bytes in relative_paths:
        worktree.update(artifact_record(root, relative_bytes))
        worktree.update(b"\0\0")

    index_bytes = run_git(root, "ls-files", "-z", "--stage")
    status_bytes = run_git(
        root,
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    index_sha256 = hashlib.sha256(index_bytes).hexdigest()
    worktree_sha256 = worktree.hexdigest()
    status_sha256 = hashlib.sha256(status_bytes).hexdigest()

    combined = hashlib.sha256()
    for label, value in (
        ("index", index_sha256),
        ("worktree", worktree_sha256),
        ("status", status_sha256),
    ):
        combined.update(label.encode("ascii") + b"\0" + value.encode("ascii") + b"\0")

    return {
        "schema": "cmro.worktree-snapshot.v1",
        "scope": SCOPE,
        "root": str(root),
        "artifact_count": len(relative_paths),
        "tracked_count": len(tracked),
        "untracked_count": len(untracked),
        "snapshot_sha256": combined.hexdigest(),
        "index_sha256": index_sha256,
        "worktree_sha256": worktree_sha256,
        "status_sha256": status_sha256,
        "limitations": [
            "Ignored files and nested submodule contents are outside this snapshot scope."
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hash tracked, staged, and non-ignored untracked Git worktree state."
    )
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        value = snapshot(args.cwd.expanduser())
    except (OSError, SnapshotError) as exc:
        print(
            json.dumps(
                {"schema": "cmro.worktree-snapshot.v1", "status": "error", "error": str(exc)},
                indent=2,
            )
        )
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
