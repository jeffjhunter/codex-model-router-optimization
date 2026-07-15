#!/usr/bin/env python3
"""Generate the payload hash manifest used by routerctl."""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "router"
OUTPUT = PAYLOAD / "MANIFEST.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
GENERATED_PARTS = {"__pycache__"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_payload_source(path: Path) -> bool:
    relative = path.relative_to(PAYLOAD)
    return (
        path.is_file()
        and path != OUTPUT
        and not GENERATED_PARTS.intersection(relative.parts)
        and path.suffix.lower() not in GENERATED_SUFFIXES
    )


def render() -> str:
    files = {
        path.relative_to(PAYLOAD).as_posix(): digest(path)
        for path in sorted(PAYLOAD.rglob("*"))
        if is_payload_source(path)
    }
    data = {"format": 1, "version": VERSION, "files": files}
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when MANIFEST.json is stale")
    args = parser.parse_args()
    content = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("MANIFEST.json is stale; run python scripts/build_manifest.py")
        print("MANIFEST.json is current.")
        return
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT} with {len(json.loads(content)['files'])} files.")


if __name__ == "__main__":
    main()
