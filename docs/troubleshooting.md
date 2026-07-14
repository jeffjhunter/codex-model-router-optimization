# Troubleshooting

Start with:

```bash
python routerctl.py doctor --target /path/to/repo
python routerctl.py verify --target /path/to/repo --json
```

## Exit codes

| Code | Meaning | Response |
| --- | --- | --- |
| `0` | Operation completed | Continue |
| `2` | Incomplete or verification failed | Perform the reported manual step or repair drift |
| `3` | Safety conflict | Inspect the named path; no differing managed file was overwritten |
| other | Usage, filesystem, or unexpected failure | Review stderr and repository status |

## “Target must be the Git root”

Pass the repository’s top-level directory, not a subdirectory. Run `git rev-parse --show-toplevel` from the target. Use `--allow-non-git` only when a non-Git destination is intentional and backed up.

## Config example was staged

Your existing `.codex/config.toml` did not contain the required Sol root settings and `[agents]` values, or could not be parsed. Merge `.codex/config.codex-model-router.example.toml` manually, including top-level `model = "gpt-5.6-sol"` and `model_reasoning_effort = "xhigh"`. Keep a single `[agents]` table, preserve unrelated settings, then rerun verification.

## Skill is not visible

1. Verify the target path and installed `.agents/skills/route-codex-work/SKILL.md`.
2. Start a new Codex task/session from the target repository.
3. Use the exact explicit invocation `$route-codex-work`.
4. Confirm workspace policy permits project skills.
5. Rerun `routerctl verify`.

## Active instruction file changed

Codex prefers a root `AGENTS.override.md` over `AGENTS.md`. If an override is added or removed after CMRO installation, the recorded router block may no longer be active. The installer stops instead of copying the block into a second file automatically. Review both instruction files, move or merge the marked block intentionally, and reinstall from a clean ownership state.

## Custom agent cannot be spawned

Confirm the agent file exists, its TOML parses, and the model is available in the current account. Model IDs and reasoning levels may be rollout-dependent. If you customize them, do so in the source payload and regenerate the manifest.

## Reviewer appears able to write

Parent live permission choices can override child sandbox defaults. Stop the run if the reviewer mutates state. Use a less permissive parent mode, inspect the effective session permissions, and report a reproducible CMRO instruction failure if applicable.

## Thread cap reached

Close completed or inactive agent threads. The coordinator should retain only the current writer and reviewer needed for the run. Do not open a replacement writer while the old writer remains active.

## Slow or interrupted handoff

Native turns have no CMRO-enforced hard timeout. Inspect the agent thread, preserve any completed result, and steer or stop it deliberately. Do not count an interruption as an actionable revision attempt unless the worker received revision instructions.

## Dirty working tree

CMRO can operate in a dirty repository only when the coordinator can establish an unambiguous baseline and preserve unrelated changes. For installation and initial pilots, prefer a clean committed repository. Never discard unrelated user work to simplify review.

## Verification reports a changed managed file

Compare the target file with the source payload. If the edit is intentional, move the customization into a fork of the payload, regenerate `MANIFEST.json`, test, and reinstall. If unexpected, investigate before overwriting anything.

## Uninstall preserved a file

This is deliberate. The file was modified, pre-existing, or not provably owned by CMRO. Remove or reconcile it manually after reviewing its contents and Git history.

## Release checksum mismatch

Do not install the archive. Download it again from the tagged GitHub release, verify the asset name, and compare with `SHA256SUMS`. If the mismatch persists, report it privately as a security issue.
