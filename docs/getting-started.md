# Getting started

## Prerequisites

- Python 3.11 or newer.
- Git.
- A current Codex app with model-pinned task creation, task inspection, and task follow-up tools.
- The target repository added as its own saved local Codex project.
- Access to the configured Sol, Luna, and Terra models, or a tested custom fork.

Commit or back up the target before installation. Review the payload under `router/`; routed tasks receive the tools and repository permissions available in the parent environment.

## 1. Diagnose the environment

```bash
python routerctl.py doctor --target /path/to/repository
```

`doctor` validates the distribution, Python, Git, optional Codex CLI visibility, and target Git root. It cannot determine ChatGPT model entitlement or whether the app exposes the required task tools.

## 2. Preview and install

```bash
python routerctl.py install --target /path/to/repository --dry-run
python routerctl.py install --target /path/to/repository
```

Clean repositories receive:

- `.codex/config.toml` with a Sol root pin and bounded native-agent settings;
- Luna, Terra, and Sol reviewer role contracts under `.codex/agents/`;
- the explicit-only `$route-codex-work` skill, session observer, worktree snapshot, and final-record validator;
- a marked router block in the active root `AGENTS.md` or `AGENTS.override.md`; and
- `.codex-model-router/installation.json` for integrity and conservative uninstall.

Existing managed files are never overwritten when contents differ.

### Existing `.codex/config.toml`

When the installer stages `.codex/config.codex-model-router.example.toml` and exits `2`, merge these settings without duplicating an existing `[agents]` table:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"

[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

Then rerun verification.

## 3. Verify installation

```bash
python routerctl.py verify --target /path/to/repository
python routerctl.py verify --target /path/to/repository --json
```

Verification checks managed hashes, TOML structure, the active instruction block, and ownership metadata. It does not contact OpenAI or prove a live model route.

## 4. Add and select the saved project

In the Codex app, add the target repository as its own project and start a fresh task there. CMRO requires an exact canonical path match; a parent project that merely contains the repository is not sufficient for the model-pinned task backend.

Confirm the root task shows Sol/xhigh, then use a reversible pilot:

```text
$route-codex-work Add a --json flag to the local status command. Preserve existing text output, add focused tests, and keep all changes inside this repository.
```

## 5. Inspect the live route

A healthy app run has this sequence:

1. Sol root records the contract, score, backend, baseline, and root session evidence.
2. One model-pinned Luna or Terra task performs a no-write identity preflight.
3. The root independently verifies the preflight task model, effort, exact turn, and repository CWD.
4. The retained worker receives the implementation packet, becomes idle after reporting evidence, and has that exact action turn independently verified.
5. A separate model-pinned Sol task passes its read-only preflight; the root snapshots content, sends review, verifies the exact review turn, and requires an identical post-review snapshot.
6. Correctable findings return to the same writer task ID and every revision/rereview turn is verified; acceptance then reaches the root final gate.

Stop if the selected route mismatches, session evidence is unavailable, the exact saved project cannot be resolved, a reviewer mutates files, or a label-only native spawn is presented as model selection.

## Native fallback

A native client may use `.codex/agents/*.toml` only when it provides explicit custom-agent/profile/type selection, a no-write first turn, status/read with exact completed turn IDs, retained-agent follow-up, and session observation. A tool with only `task_name`, message, and context-fork fields cannot perform authenticated model routing and must stop before edits.

## Upgrade

1. Commit or back up the target.
2. Use the currently installed release's `routerctl.py` to run `verify`, `uninstall --dry-run`, and `uninstall`.
3. Reconcile any modified files the old uninstaller preserves.
4. Inspect the new release and run its install dry run.
5. Install, verify, start a fresh task, and run a reversible identity-gated pilot.

Major payload versions reject other versions' installation records, preventing silent replacement of customized prompts.

## Uninstall

```bash
python routerctl.py uninstall --target /path/to/repository --dry-run
python routerctl.py uninstall --target /path/to/repository
```

Uninstall removes only files recorded as installer-owned whose hashes remain unchanged. It removes the exact marked router block from a shared instruction file. Review CMRO settings manually merged into a pre-existing config; the uninstaller does not guess ownership of shared TOML lines.
