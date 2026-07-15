#!/usr/bin/env python3
"""Install and verify the Codex Model Router Optimization profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - Python enforces this first
    raise SystemExit("routerctl requires Python 3.11 or newer.") from exc


VERSION = "3.0.0"
ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "router"
SOURCE_MANIFEST = PAYLOAD / "MANIFEST.json"
INSTALL_RECORD = Path(".codex-model-router/installation.json")
CONFIG_REL = Path(".codex/config.toml")
CONFIG_EXAMPLE_REL = Path(".codex/config.codex-model-router.example.toml")
AGENTS_REL = Path("AGENTS.md")
AGENTS_OVERRIDE_REL = Path("AGENTS.override.md")
ADDENDUM_REL = Path("AGENTS.addendum.md")
RUN_VALIDATOR_REL = Path(".agents/skills/route-codex-work/scripts/validate_run.py")
BEGIN_MARKER = "<!-- codex-model-router:begin -->"
END_MARKER = "<!-- codex-model-router:end -->"

EXIT_OK = 0
EXIT_INCOMPLETE = 2
EXIT_CONFLICT = 3


class RouterError(RuntimeError):
    """Base error with a stable process exit code."""

    exit_code = 1


class ConflictError(RouterError):
    exit_code = EXIT_CONFLICT


class VerificationError(RouterError):
    exit_code = EXIT_INCOMPLETE


@dataclass(frozen=True)
class Write:
    destination: Path
    content: bytes
    label: str


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def ensure_safe_components(root: Path, destination: Path) -> None:
    root_abs = root.absolute()
    destination_abs = destination.absolute()
    try:
        relative = destination_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ConflictError(f"Path escapes target root: {destination}") from exc

    current = root_abs
    if is_linklike(current):
        raise ConflictError(f"Target root cannot be a symlink or reparse point: {root}")
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if is_linklike(current):
                raise ConflictError(f"Destination path crosses a symlink or reparse point: {current}")
            if current != destination_abs and not current.is_dir():
                raise ConflictError(f"Destination path crosses a non-directory entry: {current}")


def ensure_no_link_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.exists() or current.is_symlink():
            if is_linklike(current):
                raise ConflictError(f"Path crosses a symlink or reparse point: {current}")


def canonical_target(value: str, error_type: type[RouterError]) -> Path:
    """Resolve ancestor aliases once while rejecting a link at the target itself."""
    candidate = Path(value).expanduser().absolute()
    if not candidate.exists() or not candidate.is_dir() or is_linklike(candidate):
        raise error_type(f"Target must be an existing regular directory: {candidate}")
    try:
        target = candidate.resolve(strict=True)
    except OSError as exc:
        raise error_type(f"Cannot resolve target directory {candidate}: {exc}") from exc
    if not target.is_dir() or is_linklike(target):
        raise error_type(f"Resolved target must be a regular directory: {target}")
    ensure_no_link_components(target)
    return target


def require_regular_file(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file() or is_linklike(path):
        raise ConflictError(f"{label} must be a regular file: {path}")


def load_source_manifest() -> dict[str, str]:
    require_regular_file(SOURCE_MANIFEST, "Payload manifest")
    try:
        raw = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConflictError(f"Cannot read payload manifest: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConflictError("Payload manifest must contain a JSON object.")
    if raw.get("format") != 1 or raw.get("version") != VERSION:
        raise ConflictError("Payload manifest format or version does not match routerctl.")
    files = raw.get("files")
    if not isinstance(files, dict) or not files:
        raise ConflictError("Payload manifest has no file allowlist.")

    expected: dict[str, str] = {}
    for relative, digest in files.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ConflictError("Payload manifest entries must be string pairs.")
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative:
            raise ConflictError(f"Unsafe payload manifest path: {relative!r}")
        expected[candidate.as_posix()] = digest.lower()

    actual: set[str] = set()
    for path in PAYLOAD.rglob("*"):
        if is_linklike(path):
            raise ConflictError(f"Payload cannot contain symlinks or reparse points: {path}")
        if path.is_file():
            actual.add(path.relative_to(PAYLOAD).as_posix())
        elif not path.is_dir():
            raise ConflictError(f"Payload contains an unsupported filesystem entry: {path}")
    allowed = set(expected) | {"MANIFEST.json"}
    if actual != allowed:
        missing = sorted(allowed - actual)
        extra = sorted(actual - allowed)
        raise ConflictError(f"Payload allowlist mismatch; missing={missing}, extra={extra}")

    for relative, digest in expected.items():
        source = PAYLOAD / Path(relative)
        require_regular_file(source, f"Payload entry {relative}")
        observed = sha256_file(source)
        if observed != digest:
            raise ConflictError(
                f"Payload hash mismatch for {relative}: expected {digest}, observed {observed}"
            )
    return expected


def managed_files(manifest: dict[str, str]) -> dict[str, str]:
    prefixes = (".codex/agents/", ".agents/skills/route-codex-work/")
    result = {path: digest for path, digest in manifest.items() if path.startswith(prefixes)}
    if not result:
        raise ConflictError("Payload manifest does not contain managed agent and skill files.")
    return result


def verified_source_bytes(relative: str, source: dict[str, str]) -> bytes:
    if relative not in source:
        raise ConflictError(f"Payload path is not allowlisted: {relative}")
    content = (PAYLOAD / Path(relative)).read_bytes()
    observed = sha256_bytes(content)
    if observed != source[relative]:
        raise ConflictError(f"Payload changed during operation: {relative}")
    return content


def parse_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise VerificationError(f"Invalid TOML at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"Unexpected TOML document at {path}")
    return value


def config_compatible(path: Path) -> tuple[bool, str]:
    try:
        data = parse_toml(path)
    except VerificationError as exc:
        return False, str(exc)
    expected_root = {"model": "gpt-5.6-sol", "model_reasoning_effort": "xhigh"}
    root_mismatches = [
        f"{key}={data.get(key)!r}" for key, value in expected_root.items() if data.get(key) != value
    ]
    if root_mismatches:
        return False, "required Sol coordinator settings differ: " + ", ".join(root_mismatches)
    agents = data.get("agents")
    if not isinstance(agents, dict):
        return False, "missing top-level [agents] table"
    expected = {"max_threads": 4, "max_depth": 1, "interrupt_message": True}
    mismatches: list[str] = []
    for key, value in expected.items():
        observed = agents.get(key)
        same_type = type(observed) is type(value)
        if not same_type or observed != value:
            mismatches.append(f"{key}={observed!r}")
    if mismatches:
        return False, "required agent settings differ: " + ", ".join(mismatches)
    return True, "required Sol coordinator and [agents] settings are active"


def find_addendum(document: str) -> tuple[int, int] | None:
    begin_count = document.count(BEGIN_MARKER)
    end_count = document.count(END_MARKER)
    if begin_count == 0 and end_count == 0:
        return None
    if begin_count != 1 or end_count != 1:
        raise ConflictError("AGENTS.md contains duplicate or incomplete router markers.")
    start = document.index(BEGIN_MARKER)
    end_start = document.index(END_MARKER)
    if end_start < start:
        raise ConflictError("AGENTS.md router markers are reversed.")
    end = end_start + len(END_MARKER)
    return start, end


def newline_for(content: bytes) -> bytes:
    if b"\r\n" in content:
        return b"\r\n"
    if b"\r" in content and b"\n" not in content:
        return b"\r"
    return b"\n"


def addendum_bytes(addendum: str, newline: bytes) -> bytes:
    normalized = addendum.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return normalized.replace("\n", newline.decode("ascii")).encode("utf-8") + newline


def addendum_append(content: bytes, addendum: str) -> bytes:
    """Return the exact bytes the installer appends after existing instructions."""
    newline = newline_for(content)
    block = addendum_bytes(addendum, newline)
    if not content:
        separator = b""
    elif any(content.endswith(ending + ending) for ending in (b"\r\n", b"\n", b"\r")):
        separator = b""
    elif any(content.endswith(ending) for ending in (b"\r\n", b"\n", b"\r")):
        separator = newline
    else:
        separator = newline + newline
    return separator + block


def active_agents_relative(target: Path) -> Path:
    override = target / AGENTS_OVERRIDE_REL
    if override.exists() or override.is_symlink():
        return AGENTS_OVERRIDE_REL
    return AGENTS_REL


def ensure_git_root(target: Path, allow_non_git: bool) -> None:
    git = shutil.which("git")
    if not git:
        if allow_non_git:
            return
        raise VerificationError("Git is not installed; use --allow-non-git only for an intentional non-Git target.")
    result = subprocess.run(
        [git, "-C", str(target), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        if allow_non_git:
            return
        raise VerificationError("Target is not a Git worktree root. Commit or back up the repository first.")
    observed = Path(result.stdout.strip()).resolve()
    if observed != target.resolve():
        raise VerificationError(f"Target must be the Git root ({observed}), not {target.resolve()}.")


def load_install_record(target: Path, source: dict[str, str]) -> dict[str, Any] | None:
    path = target / INSTALL_RECORD
    ensure_safe_components(target, path)
    if not path.exists():
        return None
    require_regular_file(path, "Installation record")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConflictError(f"Cannot read existing installation record: {exc}") from exc
    if not isinstance(value, dict):
        raise ConflictError("Existing installation record must contain a JSON object.")
    if value.get("format") != 1:
        raise ConflictError("Existing installation record has an unsupported format.")
    expected_managed = managed_files(source)
    if value.get("version") != VERSION or value.get("managed_files") != expected_managed:
        raise ConflictError("Existing installation record belongs to a different payload version.")
    if value.get("source_manifest_sha256") != sha256_file(SOURCE_MANIFEST):
        raise ConflictError("Existing installation record has a different source manifest hash.")
    if value.get("addendum_sha256") != sha256_file(PAYLOAD / ADDENDUM_REL):
        raise ConflictError("Existing installation record has a different addendum hash.")
    owned = value.get("owned_files")
    if not isinstance(owned, list) or any(not isinstance(item, str) for item in owned):
        raise ConflictError("Existing installation record has an invalid owned_files list.")
    if not set(owned).issubset(expected_managed):
        raise ConflictError("Existing installation record claims paths outside the managed allowlist.")
    for field in ("config_owned", "config_example_owned", "agents_owned"):
        if not isinstance(value.get(field), bool):
            raise ConflictError(f"Existing installation record has an invalid {field} value.")
    if value.get("agents_path") not in {AGENTS_REL.as_posix(), AGENTS_OVERRIDE_REL.as_posix()}:
        raise ConflictError("Existing installation record has an invalid agents_path value.")
    if not isinstance(value.get("agents_block_owned"), bool):
        raise ConflictError("Existing installation record has an invalid agents_block_owned value.")
    original_length = value.get("agents_original_length")
    original_hash = value.get("agents_original_sha256")
    append_hash = value.get("agents_append_sha256")
    if value["agents_block_owned"]:
        if type(original_length) is not int or original_length < 0:
            raise ConflictError("Existing installation record has an invalid agents_original_length.")
        for field_name, field_value in (
            ("agents_original_sha256", original_hash),
            ("agents_append_sha256", append_hash),
        ):
            if not isinstance(field_value, str) or len(field_value) != 64:
                raise ConflictError(f"Existing installation record has an invalid {field_name}.")
    elif any(value is not None for value in (original_length, original_hash, append_hash)):
        raise ConflictError("Unowned AGENTS block cannot claim installation byte metadata.")
    if value["agents_owned"]:
        addendum = verified_source_bytes(ADDENDUM_REL.as_posix(), source).decode("utf-8")
        canonical = addendum_append(b"", addendum)
        if (
            not value["agents_block_owned"]
            or original_length != 0
            or original_hash != sha256_bytes(b"")
            or append_hash != sha256_bytes(canonical)
        ):
            raise ConflictError("Installer-owned AGENTS.md metadata is inconsistent.")
    return value


class AtomicBatch:
    """Best-effort transactional writer for files on one target filesystem."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.staged: list[tuple[Write, Path]] = []
        self.backups: list[tuple[Path, Path | None]] = []
        self.created_directories: list[Path] = []

    def _mkdirs(self, directory: Path) -> None:
        missing: list[Path] = []
        current = directory
        while not current.exists() and current != self.root.parent:
            missing.append(current)
            current = current.parent
        for item in reversed(missing):
            item.mkdir()
            self.created_directories.append(item)

    def stage(self, writes: Iterable[Write]) -> None:
        try:
            for write in writes:
                ensure_safe_components(self.root, write.destination)
                self._mkdirs(write.destination.parent)
                descriptor, temp_name = tempfile.mkstemp(
                    prefix=f".{write.destination.name}.cmro-", dir=write.destination.parent
                )
                temp_path = Path(temp_name)
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(write.content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    mode = (
                        stat.S_IMODE(write.destination.stat().st_mode)
                        if write.destination.exists()
                        else 0o644
                    )
                    os.chmod(temp_path, mode)
                except Exception:
                    temp_path.unlink(missing_ok=True)
                    raise
                self.staged.append((write, temp_path))
        except Exception:
            self.rollback()
            raise

    def commit(self) -> None:
        try:
            for write, staged_path in self.staged:
                backup: Path | None = None
                if write.destination.exists():
                    descriptor, backup_name = tempfile.mkstemp(
                        prefix=f".{write.destination.name}.cmro-backup-",
                        dir=write.destination.parent,
                    )
                    os.close(descriptor)
                    backup = Path(backup_name)
                    backup.unlink()
                    os.replace(write.destination, backup)
                self.backups.append((write.destination, backup))
                os.replace(staged_path, write.destination)
        except Exception:
            self.rollback()
            raise
        finally:
            for _, staged_path in self.staged:
                staged_path.unlink(missing_ok=True)
        for _, backup in self.backups:
            if backup:
                backup.unlink(missing_ok=True)

    def rollback(self) -> None:
        for destination, backup in reversed(self.backups):
            destination.unlink(missing_ok=True)
            if backup and backup.exists():
                os.replace(backup, destination)
        for _, staged_path in self.staged:
            staged_path.unlink(missing_ok=True)
        for directory in reversed(self.created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_install_plan(target: Path, source: dict[str, str]) -> tuple[list[Write], dict[str, Any], bool, list[str]]:
    writes: list[Write] = []
    notes: list[str] = []
    incomplete = False
    existing_record = load_install_record(target, source)
    old_owned = set((existing_record or {}).get("owned_files", []))
    owned_files = set(old_owned)

    for relative, digest in managed_files(source).items():
        destination = target / Path(relative)
        ensure_safe_components(target, destination)
        if destination.exists():
            require_regular_file(destination, f"Managed destination {relative}")
            observed = sha256_file(destination)
            if observed != digest:
                raise ConflictError(f"Managed file conflict at {relative}; no files were changed.")
            notes.append(f"current  {relative}")
        else:
            writes.append(Write(destination, verified_source_bytes(relative, source), relative))
            owned_files.add(relative)
            notes.append(f"install  {relative}")

    config_content = verified_source_bytes(CONFIG_REL.as_posix(), source)
    config_destination = target / CONFIG_REL
    ensure_safe_components(target, config_destination)
    config_owned = bool((existing_record or {}).get("config_owned", False))
    config_example_owned = bool((existing_record or {}).get("config_example_owned", False))
    if config_destination.exists():
        require_regular_file(config_destination, "Target config")
        compatible, detail = config_compatible(config_destination)
        if compatible:
            notes.append(f"active   {CONFIG_REL.as_posix()} ({detail})")
        else:
            example = target / CONFIG_EXAMPLE_REL
            ensure_safe_components(target, example)
            content = config_content
            if example.exists():
                require_regular_file(example, "Config merge example")
                if sha256_file(example) != sha256_bytes(content):
                    raise ConflictError(f"Config example conflict at {CONFIG_EXAMPLE_REL}")
            else:
                writes.append(Write(example, content, CONFIG_EXAMPLE_REL.as_posix()))
                config_example_owned = True
            incomplete = True
            notes.append(f"manual   merge {CONFIG_EXAMPLE_REL.as_posix()} into {CONFIG_REL.as_posix()} ({detail})")
    else:
        writes.append(Write(config_destination, config_content, CONFIG_REL.as_posix()))
        config_owned = True
        notes.append(f"install  {CONFIG_REL.as_posix()}")

    addendum_source = verified_source_bytes(ADDENDUM_REL.as_posix(), source).decode("utf-8")
    agents_relative = active_agents_relative(target)
    previous_agents_path = (existing_record or {}).get("agents_path")
    if previous_agents_path and previous_agents_path != agents_relative.as_posix():
        raise ConflictError(
            "The active root instruction file changed since installation; reconcile the router block manually."
        )
    agents_destination = target / agents_relative
    ensure_safe_components(target, agents_destination)
    agents_owned = bool((existing_record or {}).get("agents_owned", False))
    agents_block_owned = bool((existing_record or {}).get("agents_block_owned", False))
    agents_original_length = (existing_record or {}).get("agents_original_length")
    agents_original_sha256 = (existing_record or {}).get("agents_original_sha256")
    agents_append_sha256 = (existing_record or {}).get("agents_append_sha256")
    if agents_destination.exists():
        require_regular_file(agents_destination, "Target AGENTS.md")
        current_bytes = agents_destination.read_bytes()
        current = current_bytes.decode("utf-8")
        region = find_addendum(current)
        if region is None:
            if existing_record:
                raise ConflictError("The recorded AGENTS.md router block is missing; reconcile it manually.")
            appended = addendum_append(current_bytes, addendum_source)
            writes.append(Write(agents_destination, current_bytes + appended, "merge AGENTS.md"))
            agents_block_owned = True
            agents_original_length = len(current_bytes)
            agents_original_sha256 = sha256_bytes(current_bytes)
            agents_append_sha256 = sha256_bytes(appended)
            notes.append(f"merge    {agents_relative.as_posix()} router block")
        else:
            installed = current[region[0] : region[1]]
            if normalized_text(installed) != normalized_text(addendum_source):
                raise ConflictError("AGENTS.md contains a modified router block; resolve it manually.")
            if not existing_record:
                agents_block_owned = False
                agents_original_length = None
                agents_original_sha256 = None
                agents_append_sha256 = None
            notes.append(f"current  {agents_relative.as_posix()} router block")
    else:
        if existing_record and not agents_owned:
            raise ConflictError("The recorded pre-existing AGENTS.md file is missing; reconcile it manually.")
        installed_bytes = addendum_append(b"", addendum_source)
        if existing_record and agents_append_sha256 != sha256_bytes(installed_bytes):
            raise ConflictError("The recorded AGENTS.md bytes cannot be reconstructed safely.")
        writes.append(
            Write(
                agents_destination,
                installed_bytes,
                agents_relative.as_posix(),
            )
        )
        agents_owned = True
        agents_block_owned = True
        agents_original_length = 0
        agents_original_sha256 = sha256_bytes(b"")
        agents_append_sha256 = sha256_bytes(installed_bytes)
        notes.append(f"install  {agents_relative.as_posix()} router block")

    record = {
        "format": 1,
        "version": VERSION,
        "source_manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "managed_files": managed_files(source),
        "owned_files": sorted(owned_files),
        "config_owned": config_owned,
        "config_example_owned": config_example_owned,
        "agents_owned": agents_owned,
        "agents_block_owned": agents_block_owned,
        "agents_original_length": agents_original_length,
        "agents_original_sha256": agents_original_sha256,
        "agents_append_sha256": agents_append_sha256,
        "agents_path": agents_relative.as_posix(),
        "addendum_sha256": sha256_file(PAYLOAD / ADDENDUM_REL),
    }
    record_destination = target / INSTALL_RECORD
    ensure_safe_components(target, record_destination)
    record_content = json_bytes(record)
    if record_destination.exists():
        require_regular_file(record_destination, "Installation record")
        if record_destination.read_bytes() != record_content:
            writes.append(Write(record_destination, record_content, INSTALL_RECORD.as_posix()))
            notes.append(f"update   {INSTALL_RECORD.as_posix()}")
    else:
        writes.append(Write(record_destination, record_content, INSTALL_RECORD.as_posix()))
        notes.append(f"install  {INSTALL_RECORD.as_posix()}")
    return writes, record, incomplete, notes


def command_install(args: argparse.Namespace) -> int:
    source = load_source_manifest()
    target = canonical_target(args.target, ConflictError)
    ensure_git_root(target, args.allow_non_git)
    writes, _, incomplete, notes = build_install_plan(target, source)
    print("Install plan:")
    for note in notes:
        print(f"  {note}")
    if args.dry_run:
        print("Dry run only; no files changed.")
        return EXIT_INCOMPLETE if incomplete else EXIT_OK
    if writes:
        batch = AtomicBatch(target)
        batch.stage(writes)
        batch.commit()
    print("Installation files are current." if not writes else "Installation writes completed.")
    if incomplete:
        print("Manual config merge required; rerun verify after merging the example.")
        return EXIT_INCOMPLETE
    return EXIT_OK


def check_target(target: Path, source: dict[str, str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    for relative, digest in managed_files(source).items():
        destination = target / Path(relative)
        try:
            ensure_safe_components(target, destination)
        except ConflictError as exc:
            add(relative, False, str(exc))
            continue
        passed = destination.is_file() and not is_linklike(destination)
        if passed:
            observed = sha256_file(destination)
            passed = observed == digest
            detail = "hash matches payload" if passed else f"hash mismatch: {observed}"
        else:
            detail = "missing, not a file, or link-like"
        add(relative, passed, detail)

    config = target / CONFIG_REL
    try:
        ensure_safe_components(target, config)
        if config.is_file() and not is_linklike(config):
            passed, detail = config_compatible(config)
        else:
            passed, detail = False, "missing, not a file, or link-like"
    except ConflictError as exc:
        passed, detail = False, str(exc)
    add(CONFIG_REL.as_posix(), passed, detail)

    active_agents = active_agents_relative(target)
    agents = target / active_agents
    addendum = (PAYLOAD / ADDENDUM_REL).read_text(encoding="utf-8")
    try:
        ensure_safe_components(target, agents)
        if agents.is_file() and not is_linklike(agents):
            current = agents.read_text(encoding="utf-8")
            region = find_addendum(current)
            passed = region is not None and normalized_text(current[region[0] : region[1]]) == normalized_text(addendum)
            detail = "router block is current" if passed else "router block missing or modified"
        else:
            passed, detail = False, "missing, not a file, or link-like"
    except (OSError, UnicodeError, ConflictError) as exc:
        passed, detail = False, str(exc)
    add(f"{active_agents.as_posix()} router block", passed, detail)

    try:
        value = load_install_record(target, source)
        passed = value is not None and value.get("agents_path") == active_agents.as_posix()
        detail = (
            "installation record matches payload and active instructions"
            if passed
            else "installation record is missing or names an inactive instruction file"
        )
    except RouterError as exc:
        passed, detail = False, str(exc)
    add(INSTALL_RECORD.as_posix(), passed, detail)
    return checks


def command_verify(args: argparse.Namespace) -> int:
    source = load_source_manifest()
    target = canonical_target(args.target, VerificationError)
    ensure_git_root(target, args.allow_non_git)
    checks = check_target(target, source)
    passed = all(check["passed"] for check in checks)
    if args.json:
        print(
            json.dumps(
                {
                    "schema": "cmro.distribution-verification.v1",
                    "scope": "distribution",
                    "version": VERSION,
                    "passed": passed,
                    "target": str(target),
                    "checks": checks,
                    "limitations": [
                        "Does not inspect Codex app task capabilities, model entitlement, or live runtime identity."
                    ],
                },
                indent=2,
            )
        )
    else:
        for check in checks:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"[{marker}] {check['name']}: {check['detail']}")
        print("Verification passed." if passed else "Verification failed.")
    return EXIT_OK if passed else EXIT_INCOMPLETE


def remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    while current != stop and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def command_uninstall(args: argparse.Namespace) -> int:
    source = load_source_manifest()
    target = canonical_target(args.target, ConflictError)
    ensure_git_root(target, args.allow_non_git)
    record = load_install_record(target, source)
    if not record:
        raise VerificationError("No installation record found; nothing can be safely removed.")

    agents_relative = Path(record["agents_path"])
    preflight_paths = [
        *(target / Path(relative) for relative in record.get("owned_files", [])),
        target / CONFIG_REL,
        target / CONFIG_EXAMPLE_REL,
        target / agents_relative,
        target / INSTALL_RECORD,
    ]
    for path in preflight_paths:
        ensure_safe_components(target, path)

    removals: list[Path] = []
    skipped: list[str] = []
    managed = record.get("managed_files", {})
    for relative in record.get("owned_files", []):
        destination = target / Path(relative)
        expected = managed.get(relative)
        if destination.is_file() and not is_linklike(destination) and expected and sha256_file(destination) == expected:
            removals.append(destination)
        elif destination.exists() or destination.is_symlink():
            skipped.append(f"modified managed file: {relative}")

    config = target / CONFIG_REL
    if record.get("config_owned"):
        source_digest = sha256_file(PAYLOAD / CONFIG_REL)
        if config.is_file() and not is_linklike(config) and sha256_file(config) == source_digest:
            removals.append(config)
        elif config.exists() or config.is_symlink():
            skipped.append(f"modified config: {CONFIG_REL.as_posix()}")

    example = target / CONFIG_EXAMPLE_REL
    if record.get("config_example_owned"):
        source_digest = sha256_file(PAYLOAD / CONFIG_REL)
        if example.is_file() and not is_linklike(example) and sha256_file(example) == source_digest:
            removals.append(example)
        elif example.exists() or example.is_symlink():
            skipped.append(f"modified config example: {CONFIG_EXAMPLE_REL.as_posix()}")

    agents = target / agents_relative
    agents_rewrite: bytes | None = None
    if record.get("agents_block_owned"):
        if agents.is_file() and not is_linklike(agents):
            current_bytes = agents.read_bytes()
            parse_failed = False
            try:
                current = current_bytes.decode("utf-8")
                region = find_addendum(current)
            except (UnicodeError, ConflictError) as exc:
                region = None
                parse_failed = True
                skipped.append(str(exc))
            if region:
                addendum = verified_source_bytes(ADDENDUM_REL.as_posix(), source).decode("utf-8")
                installed = current[region[0] : region[1]]
                original_length = record["agents_original_length"]
                prefix = current_bytes[:original_length]
                appended = current_bytes[original_length:]
                expected_append = addendum_append(prefix, addendum)
                metadata_matches = (
                    sha256_bytes(prefix) == record["agents_original_sha256"]
                    and sha256_bytes(appended) == record["agents_append_sha256"]
                    and appended == expected_append
                )
                if normalized_text(installed) != normalized_text(addendum) or not metadata_matches:
                    skipped.append(f"modified {agents_relative.as_posix()} router block or surrounding bytes")
                elif record.get("agents_owned"):
                    removals.append(agents)
                else:
                    agents_rewrite = prefix
            elif not parse_failed:
                original_length = record["agents_original_length"]
                original = current_bytes[:original_length]
                already_restored = (
                    len(current_bytes) == original_length
                    and sha256_bytes(original) == record["agents_original_sha256"]
                )
                if not already_restored:
                    skipped.append(f"missing or modified {agents_relative.as_posix()} router markers")
        elif agents.exists() or agents.is_symlink():
            skipped.append(f"instruction path is not a regular file: {agents_relative.as_posix()}")

    if args.dry_run:
        for path in removals:
            print(f"would remove {path.relative_to(target).as_posix()}")
        if agents_rewrite is not None:
            print("would remove router block from AGENTS.md")
        for item in skipped:
            print(f"would keep   {item}")
        return EXIT_INCOMPLETE if skipped else EXIT_OK

    if agents_rewrite is not None:
        batch = AtomicBatch(target)
        batch.stage([Write(agents, agents_rewrite, "remove AGENTS.md router block")])
        batch.commit()
    for path in removals:
        path.unlink(missing_ok=True)
        remove_empty_parents(path.parent, target)
    if not skipped:
        (target / INSTALL_RECORD).unlink(missing_ok=True)
        remove_empty_parents((target / INSTALL_RECORD).parent, target)
    for item in skipped:
        print(f"kept: {item}")
    print(
        "Safe uninstall completed."
        if not skipped
        else "Partial uninstall completed; modified files and the installation record were preserved."
    )
    return EXIT_INCOMPLETE if skipped else EXIT_OK


def command_manifest(args: argparse.Namespace) -> int:
    source = load_source_manifest()
    value = {
        "schema": "cmro.payload-manifest-view.v1",
        "scope": "distribution",
        "version": VERSION,
        "payload": str(PAYLOAD),
        "manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "files": source,
    }
    print(json.dumps(value, indent=2, sort_keys=True))
    return EXIT_OK


def command_validate_run(args: argparse.Namespace) -> int:
    source = load_source_manifest()
    relative = RUN_VALIDATOR_REL.as_posix()
    verified_source_bytes(relative, source)
    result = subprocess.run(
        [sys.executable, str(PAYLOAD / RUN_VALIDATOR_REL), str(args.record)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def tool_version(command: str, arguments: list[str]) -> tuple[bool, str]:
    executable = shutil.which(command)
    if not executable:
        return False, "not found"
    try:
        result = subprocess.run(
            [executable, *arguments],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"unavailable: {exc}"
    output = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, output[0] if output else executable


def command_doctor(args: argparse.Namespace) -> int:
    findings: list[tuple[str, bool, str]] = []
    source: dict[str, str] = {}
    try:
        source = load_source_manifest()
        findings.append(("payload", True, f"{len(source)} allowlisted files with valid hashes"))
    except RouterError as exc:
        findings.append(("payload", False, str(exc)))
    findings.append(("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    for name, argv in (("git", ["--version"]), ("codex", ["--version"])):
        ok, detail = tool_version(name, argv)
        findings.append((name, ok, detail))

    if args.target:
        try:
            target = canonical_target(args.target, VerificationError)
            ensure_git_root(target, args.allow_non_git)
            findings.append(("target", True, str(target)))
        except RouterError as exc:
            findings.append(("target", False, str(exc)))

    backend_paths = {
        ".agents/skills/route-codex-work/references/actors.md",
        ".agents/skills/route-codex-work/scripts/observe_session.py",
        ".agents/skills/route-codex-work/scripts/snapshot_worktree.py",
        ".agents/skills/route-codex-work/scripts/validate_run.py",
    }
    missing_backend_paths = sorted(backend_paths - set(source))
    findings.append(
        (
            "backend_contract",
            not missing_backend_paths,
            "actor contracts, session observer, worktree snapshot, and run validator are allowlisted"
            if not missing_backend_paths
            else "missing: " + ", ".join(missing_backend_paths),
        )
    )

    passed = all(value for name, value, _ in findings if name != "codex")
    limitations = [
        "Scope is distribution and local CLI prerequisites only.",
        "Codex app task tools, saved-project matching, model entitlement, and runtime identity are not inspected.",
    ]
    if args.json:
        print(
            json.dumps(
                {
                    "schema": "cmro.doctor.v1",
                    "scope": "distribution",
                    "version": VERSION,
                    "passed": passed,
                    "findings": [
                        {"name": name, "passed": value, "detail": detail}
                        for name, value, detail in findings
                    ],
                    "limitations": limitations,
                },
                indent=2,
            )
        )
    else:
        for name, value, detail in findings:
            print(f"[{'PASS' if value else 'WARN'}] {name}: {detail}")
        print("Scope: distribution only. App task capabilities and model entitlement are not inferred.")
    return EXIT_OK if passed else EXIT_INCOMPLETE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="routerctl",
        description="Safely install, verify, diagnose, or remove the Codex Model Router Optimization profile.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def target_options(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--target", required=True, help="Target repository root")
        subparser.add_argument(
            "--allow-non-git",
            action="store_true",
            help="Allow an intentional non-Git target (disables the Git-root safety check)",
        )

    install = subparsers.add_parser("install", help="Install the profile without overwriting conflicts")
    target_options(install)
    install.add_argument("--dry-run", action="store_true", help="Show the plan without writing")
    install.set_defaults(handler=command_install)

    verify = subparsers.add_parser("verify", help="Verify an installed profile")
    target_options(verify)
    verify.add_argument("--json", action="store_true", help="Emit machine-readable results")
    verify.set_defaults(handler=command_verify)

    uninstall = subparsers.add_parser("uninstall", help="Remove only unchanged files owned by this installer")
    target_options(uninstall)
    uninstall.add_argument("--dry-run", action="store_true", help="Show safe removals without writing")
    uninstall.set_defaults(handler=command_uninstall)

    manifest = subparsers.add_parser("manifest", help="Print the verified payload manifest")
    manifest.set_defaults(handler=command_manifest)

    validate_run = subparsers.add_parser(
        "validate-run", help="Validate a sanitized cmro.final.v3 JSON record"
    )
    validate_run.add_argument("--record", required=True, help="JSON record path, or - for stdin")
    validate_run.set_defaults(handler=command_validate_run)

    doctor = subparsers.add_parser("doctor", help="Check local prerequisites and payload integrity")
    doctor.add_argument("--target", help="Optional target repository root")
    doctor.add_argument("--allow-non-git", action="store_true")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable distribution findings")
    doctor.set_defaults(handler=command_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except RouterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: filesystem operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
