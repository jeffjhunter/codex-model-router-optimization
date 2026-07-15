#!/usr/bin/env python3
"""Build a deterministic, portable source release and checksum file."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DIST = ROOT / "dist"
ARCHIVE = DIST / f"codex-model-router-optimization-{VERSION}.zip"
PREFIX = f"codex-model-router-optimization-{VERSION}/"
EXCLUDED_PREFIXES = ("dist/", ".git/")
REQUIRED_ARCHIVE_MEMBERS = {
    "router/.agents/skills/route-codex-work/references/actors.md",
    "router/.agents/skills/route-codex-work/scripts/observe_session.py",
    "router/.agents/skills/route-codex-work/scripts/snapshot_worktree.py",
    "router/.agents/skills/route-codex-work/scripts/validate_packet.py",
    "router/.agents/skills/route-codex-work/scripts/validate_run.py",
}


def run_release_checks() -> None:
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if status:
        raise SystemExit("Release builds require a clean Git worktree.")
    for script, arguments in (
        ("scripts/build_manifest.py", ["--check"]),
        ("scripts/check_repo.py", []),
    ):
        subprocess.run(
            [sys.executable, str(ROOT / script), *arguments],
            cwd=ROOT,
            check=True,
        )


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    return sorted(
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item and not item.decode("utf-8").startswith(EXCLUDED_PREFIXES)
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run_release_checks()
    files = tracked_files()
    if not files:
        raise SystemExit("No tracked files found. Initialize and commit the repository first.")
    DIST.mkdir(exist_ok=True)
    ARCHIVE.unlink(missing_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            source = ROOT / relative
            if not source.is_file() or source.is_symlink():
                raise SystemExit(f"Release input is not a regular file: {relative}")
            info = zipfile.ZipInfo(PREFIX + relative.replace(os.sep, "/"))
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.create_system = 3
            mode = 0o755 if relative.endswith(".py") else 0o644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {
            name.removeprefix(PREFIX)
            for name in archive.namelist()
            if name.startswith(PREFIX)
        }
    missing = sorted(REQUIRED_ARCHIVE_MEMBERS - members)
    if missing:
        ARCHIVE.unlink(missing_ok=True)
        raise SystemExit("Release archive is missing required backend files: " + ", ".join(missing))
    checksums = DIST / "SHA256SUMS"
    checksums.write_text(f"{sha256(ARCHIVE)}  {ARCHIVE.name}\n", encoding="utf-8", newline="\n")
    print(f"Built {ARCHIVE} ({ARCHIVE.stat().st_size} bytes)")
    print(checksums.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
