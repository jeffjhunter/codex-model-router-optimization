# Troubleshooting

Start with:

```bash
python routerctl.py doctor --target /path/to/repo
python routerctl.py verify --target /path/to/repo --json
```

These commands validate distribution and installation only. They do not inspect Codex app capabilities or live model entitlement.

## Exit codes

| Code | Meaning | Response |
| --- | --- | --- |
| `0` | Operation completed | Continue |
| `2` | Incomplete, unavailable evidence, or verification failure | Perform the reported safe step |
| `3` | Safety conflict or observed identity mismatch | Stop and inspect the evidence |
| other | Usage, filesystem, or unexpected failure | Review stderr and repository status |

## Target must be the Git root

Pass the repository's top-level directory, not a subdirectory. Run `git rev-parse --show-toplevel`. Use `--allow-non-git` only when intentional and backed up.

## Exact saved project is missing

The app backend matches the current repository's canonical path to one saved local project. Add that repository as its own Codex project; selecting a parent folder is insufficient. Start a fresh task in the new project and invoke the skill again.

## Task tools are unavailable

The preferred backend needs project listing, model-pinned task creation, completed-turn reading, and retained-task follow-up. If any is absent, use native custom agents only when the client exposes explicit profile/type selection, no-write first turns, status/read with exact completed turn IDs, retained-agent follow-up, and session observation. Otherwise CMRO correctly stops before edits.

## Named worker ran the root model

`task_name="terra_worker"` labels a native subagent; it does not select `.codex/agents/terra_worker.toml` when the spawn schema has no profile field. Preserve the mismatch evidence, stop the run, and use the model-pinned app backend. Do not rename or re-prompt the Sol child and call it Terra.

## Session observation is not ready

Wait until the relevant preflight, implementation, revision, review, or rereview task turn is idle, capture its completed turn ID from the task read, and rerun the installed observer with `--expect-turn-id`, exact model/effort/CWD, and `--expect-top-level` for app tasks. Never substitute the newest log file heuristically.

## Session observation is ambiguous or mismatched

Do not continue. Check that the task ID and exact action turn ID came from the creation receipt and completed task read, the repository path matches exactly, and only one session log exists for the task. A model/effort mismatch may indicate unavailable entitlement, fallback, or a client regression.

## Preflight or final packet is missing

Poll task reads until the turn is complete and the task is idle. Follow pagination or increase output limits to recover the full packet. Stopped, failed, unreachable, truncated, stale-plan, or missing-packet tasks never count as success.

## Config example was staged

Merge `.codex/config.codex-model-router.example.toml` manually. Preserve unrelated settings and use one `[agents]` table, then rerun verification.

## Skill is not visible

1. Verify `.agents/skills/route-codex-work/SKILL.md` in the exact target.
2. Start a fresh Codex task from that saved project.
3. Invoke `$route-codex-work` exactly.
4. Confirm workspace policy permits project skills.
5. Rerun `routerctl verify`.

## Reviewer appears able to write

App task creation has no reviewer-specific read-only sandbox parameter. The reviewer contract prohibits mutation, but that is behavioral. Run `python .agents/skills/route-codex-work/scripts/snapshot_worktree.py --cwd /path/to/repo` immediately before and after review and compare `snapshot_sha256`. A mismatch invalidates acceptance even if the `git status` text is identical. Ignored files and nested submodule contents are outside the declared snapshot scope.

## Dirty or concurrently edited working tree

Establish an unambiguous baseline and preserve unrelated changes. Do not start a routed writer while another task, process, or person may write to the same checkout. Never discard unrelated work to simplify review.

## Managed file changed or uninstall preserved it

The installer treats target-local changes as drift and the uninstaller preserves files it cannot prove it owns unchanged. Move intentional customization into a source fork, rebuild the manifest, and reconcile preserved files manually.

## Release checksum mismatch

Do not install the archive. Download it again, verify the asset name, and compare `SHA256SUMS`. Report persistent mismatches privately as a security issue.
