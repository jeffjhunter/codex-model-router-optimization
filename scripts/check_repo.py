#!/usr/bin/env python3
"""Dependency-free repository integrity checks used by CI."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "router/.agents/skills/route-codex-work/SKILL.md"
OPENAI_YAML = ROOT / "router/.agents/skills/route-codex-work/agents/openai.yaml"
SESSION_PROBE = ROOT / "router/.agents/skills/route-codex-work/scripts/observe_session.py"
WORKTREE_SNAPSHOT = ROOT / "router/.agents/skills/route-codex-work/scripts/snapshot_worktree.py"
RUN_VALIDATOR = ROOT / "router/.agents/skills/route-codex-work/scripts/validate_run.py"
ACTOR_CONTRACTS = ROOT / "router/.agents/skills/route-codex-work/references/actors.md"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_toml() -> None:
    paths = sorted((ROOT / "router/.codex").rglob("*.toml"))
    if len(paths) != 4:
        fail(f"expected 4 TOML files, found {len(paths)}")
    parsed = {}
    for path in paths:
        with path.open("rb") as handle:
            parsed[path.name] = tomllib.load(handle)
    expected = {
        "config.toml": ("gpt-5.6-sol", "xhigh"),
        "luna_worker.toml": ("gpt-5.6-luna", "medium"),
        "terra_worker.toml": ("gpt-5.6-terra", "high"),
        "sol_reviewer.toml": ("gpt-5.6-sol", "xhigh"),
    }
    for name, (model, effort) in expected.items():
        value = parsed.get(name)
        if value is None or value.get("model") != model or value.get("model_reasoning_effort") != effort:
            fail(f"{name} does not pin {model} / {effort}")
    print(f"PASS: parsed {len(paths)} TOML files")


def check_skill() -> None:
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        fail("SKILL.md frontmatter is malformed")
    frontmatter = text.split("---", 2)[1].strip().splitlines()
    keys = [line.split(":", 1)[0].strip() for line in frontmatter if ":" in line]
    if keys != ["name", "description"]:
        fail(f"SKILL.md frontmatter keys are {keys}")
    if "name: route-codex-work" not in text:
        fail("skill name does not match folder")
    if "TODO" in text:
        fail("SKILL.md contains TODO text")
    required_workflow_text = (
        "codex_app_tasks",
        "native_custom_agent",
        "codex_app__create_thread",
        'task_name="terra_worker"',
        "observe_session.py",
        "snapshot_worktree.py",
        "validate_run.py",
        "cmro.worker.v3",
        "cmro.review.v3",
    )
    for value in required_workflow_text:
        if value not in text:
            fail(f"SKILL.md is missing authenticated-backend rule {value!r}")
    if not SESSION_PROBE.is_file():
        fail("runtime session observation script is missing")
    if not WORKTREE_SNAPSHOT.is_file():
        fail("worktree content snapshot script is missing")
    if not RUN_VALIDATOR.is_file():
        fail("protocol v3 final-record validator is missing")
    if not ACTOR_CONTRACTS.is_file():
        fail("app-task actor contracts are missing")
    actors = ACTOR_CONTRACTS.read_text(encoding="utf-8")
    for value in ("Identity preflight contract", "Luna writer contract", "Terra writer contract", "Sol reviewer contract"):
        if value not in actors:
            fail(f"actor contract file is missing {value!r}")
    yaml = OPENAI_YAML.read_text(encoding="utf-8")
    required = (
        'display_name: "Route Codex Work"',
        'short_description: "Run verified Sol, Luna/Terra, Sol routing"',
        'default_prompt: "Use $route-codex-work',
        "allow_implicit_invocation: false",
    )
    for value in required:
        if value not in yaml:
            fail(f"openai.yaml is missing {value!r}")
    print("PASS: skill metadata and explicit-only policy")


def check_local_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        for target in pattern.findall(path.read_text(encoding="utf-8")):
            clean = target.strip("<>").split("#", 1)[0]
            if not clean or "://" in clean or clean.startswith("mailto:"):
                continue
            destination = (path.parent / clean).resolve()
            if not destination.exists():
                errors.append(f"{path.relative_to(ROOT)} -> {target}")
    if errors:
        fail("broken local Markdown links: " + "; ".join(errors))
    print("PASS: local Markdown links")


def check_manifest() -> None:
    path = ROOT / "router/MANIFEST.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != (ROOT / "VERSION").read_text(encoding="utf-8").strip():
        fail("manifest version differs from VERSION")
    generated = [
        relative
        for relative in value.get("files", {})
        if "__pycache__" in Path(relative).parts or Path(relative).suffix in {".pyc", ".pyo"}
    ]
    if generated:
        fail("manifest includes generated Python cache files: " + ", ".join(generated))
    result = __import__("subprocess").run(
        [sys.executable, str(ROOT / "routerctl.py"), "manifest"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        fail("routerctl manifest failed: " + result.stderr)
    print("PASS: payload allowlist and hashes")


def check_eval_inventory() -> None:
    path = ROOT / "evals/scenarios.jsonl"
    scenarios = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    required_ids = {
        "review-seeded-defect",
        "attempt-limit",
        "route-terra-migration-blocker",
        "native-no-selector",
        "saved-project-mismatch",
        "runtime-model-mismatch",
        "worker-followup-model-mismatch",
        "review-followup-model-mismatch",
        "stopped-worker-task",
        "reviewer-mutation",
        "same-id-revision",
        "native-full-contract",
    }
    observed_ids = {item.get("id") for item in scenarios}
    if not required_ids.issubset(observed_ids):
        fail(f"eval inventory is missing required scenarios: {sorted(required_ids - observed_ids)}")
    expected_models = {"luna_worker": "gpt-5.6-luna", "terra_worker": "gpt-5.6-terra"}
    for item in scenarios:
        worker = item.get("expected_worker")
        if expected_models.get(worker) != item.get("expected_model"):
            fail(f"eval {item.get('id')} has inconsistent worker/model routing")
        if item.get("expected_reviewer") != "sol_reviewer":
            fail(f"eval {item.get('id')} does not use sol_reviewer")
        if item.get("expected_backend") not in {
            "codex_app_tasks",
            "native_custom_agent",
            "none",
        }:
            fail(f"eval {item.get('id')} has no valid v3 backend expectation")
    print(f"PASS: {len(scenarios)} evaluation scenarios use the v3 model contract")


def check_sensitive_literals() -> None:
    suspicious = re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY)")
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() in {".zip", ".png", ".jpg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if suspicious.search(text):
            hits.append(str(path.relative_to(ROOT)))
    if hits:
        fail("possible secret literals in: " + ", ".join(hits))
    print("PASS: no common secret literals")


def main() -> None:
    check_toml()
    check_skill()
    check_manifest()
    check_eval_inventory()
    check_local_links()
    check_sensitive_literals()
    print("Repository checks passed.")


if __name__ == "__main__":
    main()
