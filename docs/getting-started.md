# Getting started

## Prerequisites

- Python 3.11 or newer.
- Git.
- A current Codex desktop app, CLI, or IDE extension that supports project-scoped custom agents and skills.
- A target repository you can safely modify.
- Access to the configured models, or willingness to customize the local payload first.

Commit or back up the target repository before installation. Review the payload under `router/`; installation gives those agent instructions access to the tools and repository permissions available in the parent Codex task.

## 1. Diagnose the environment

```bash
python routerctl.py doctor --target /path/to/repository
```

`doctor` validates the distribution, Python, Git, optional Codex CLI visibility, and target Git root. It cannot determine ChatGPT plan entitlements or model rollout status; confirm models in Codex itself.

## 2. Preview installation

```bash
python routerctl.py install --target /path/to/repository --dry-run
```

The dry run performs payload, hash, path, collision, Git-root, TOML, and `AGENTS.md` preflight checks without writing.

## 3. Install

```bash
python routerctl.py install --target /path/to/repository
```

Clean repositories receive:

- `.codex/config.toml` with a Sol root pin and bounded agent settings;
- three project-scoped custom agent files for Luna, Terra, and an independent Sol reviewer;
- the explicit-only `$route-codex-work` skill;
- a marked router block in the active root `AGENTS.md` or `AGENTS.override.md`; and
- `.codex-model-router/installation.json` for integrity and safe uninstall ownership.

Existing managed files are never overwritten when their contents differ.

If the repository already has a root `AGENTS.override.md`, Codex gives it precedence over `AGENTS.md`. The installer detects that case and merges the marked router block into the active override instead. Adding or removing a root override after installation invalidates verification until the instruction sources are reconciled deliberately.

### Existing `.codex/config.toml`

The installer does not rewrite an existing incompatible TOML file. It stages `.codex/config.codex-model-router.example.toml` and exits `2`.

Merge the root settings and agent table into the existing config, preserving unrelated settings and ensuring there is only one `[agents]` table:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"

[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

Then rerun verification. Do not copy a second `[agents]` header into a file that already has one. Existing root `model` values are incompatible with the default v2 contract and must be reconciled deliberately.

## 4. Verify

```bash
python routerctl.py verify --target /path/to/repository
```

For automation:

```bash
python routerctl.py verify --target /path/to/repository --json
```

Verification compares managed files with the local allowlisted payload hashes, parses the effective config, checks the exact marked instruction block, and validates the installation record. Release checksums and provenance attest the distributed archive separately. Verification does not contact OpenAI or consume model usage.

## 5. Start a fresh Codex task

Skills, project instructions, and custom agents are discovered when Codex opens a new task or session. Start from the target repository, confirm the fresh session shows `gpt-5.6-sol`, and use a reversible pilot:

```text
$route-codex-work Add a --json flag to the local status command. Preserve its existing text output, add focused tests, and keep changes inside this repository.
```

Inspect the agent activity and session details. A healthy run should expose the selected Luna/Terra custom agent and model, create a separate Sol reviewer, return failed criteria to the same writer ID if needed, and finish with the Sol root gate. Stop the pilot if the model identities are unavailable or the observed sequence materially differs.

## Upgrade

1. Commit or back up the target repository.
2. With the **currently installed release's** `routerctl.py`, run `verify`, then `uninstall --dry-run` and `uninstall`.
3. If uninstall preserves modified files, reconcile or remove those files intentionally and rerun the old uninstaller until its installation record is gone.
4. Download or check out the new CMRO release, then read its changelog and inspect its payload.
5. Run the new release's `install --dry-run` against the target.
6. Resolve any remaining conflicts intentionally, then install and verify with the new release.

Each major payload version rejects installation records from other versions. The old release must therefore remove its own ownership record before the new release is installed; this prevents an upgrade from silently replacing customized prompts. Version 2 also changes the active root model to Sol, so review that project-wide effect before upgrading.

## Uninstall

Preview first:

```bash
python routerctl.py uninstall --target /path/to/repository --dry-run
python routerctl.py uninstall --target /path/to/repository
```

Uninstall removes only files the installation record says CMRO created and whose hashes remain unchanged. It removes the exact marked router block from a shared `AGENTS.md`. Modified or pre-existing files are preserved and reported. Review any CMRO settings manually merged into a pre-existing `.codex/config.toml`; the uninstaller will not guess which shared TOML lines belong to CMRO.
