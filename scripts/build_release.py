#!/usr/bin/env python3
"""Build a deterministic, portable source release and checksum file."""

from __future__ import annotations

import hashlib
import os
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DIST = ROOT / "dist"
ARCHIVE = DIST / f"codex-model-router-optimization-{VERSION}.zip"
PREFIX = f"codex-model-router-optimization-{VERSION}/"
EXCLUDED_PREFIXES = ("dist/", ".git/")


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
    checksums = DIST / "SHA256SUMS"
    checksums.write_text(f"{sha256(ARCHIVE)}  {ARCHIVE.name}\n", encoding="utf-8", newline="\n")
    print(f"Built {ARCHIVE} ({ARCHIVE.stat().st_size} bytes)")
    print(checksums.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
