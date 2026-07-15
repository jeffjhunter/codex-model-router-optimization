# Limitations

## Orchestration remains instruction-driven

Model-pinned task creation makes model selection explicit, but skills and prompts still coordinate the lifecycle. Same-writer follow-up, reviewer reuse, attempt counting, and the root gate are not a durable application state machine. Use an SDK controller when transition enforcement, crash recovery, auditable persistence, or machine-validated schemas are mandatory.

## App backend availability varies

The preferred backend needs callable saved-project listing, model-pinned task creation, completed-turn reading, and task follow-up in the current Codex app environment. The target must be registered as the exact saved project. If those capabilities are missing, CMRO can use native custom agents only when the client provides explicit profile selection, no-write first turns, status/read with exact completed turn IDs, retained-agent follow-up, and session observation; otherwise it stops before edits.

## No hard ordinary-turn timeout

CMRO does not claim a hard timeout for ordinary task turns. Slow or stalled handoffs may require inspection or deliberate interruption.

## Reviewer read-only is behavioral

The reviewer task is instructed to remain read-only, and the role file requests a read-only sandbox where applicable. Parent permissions or task-surface defaults can still provide write-capable tools. The root compares content snapshots around every review. Those snapshots cover the Git index and raw contents of tracked and non-ignored untracked artifacts; ignored files and nested submodule contents remain outside their declared scope.

## Session metadata is local and evolving

`observe_session.py` reads only local `session_meta` and `turn_context` records and emits no conversation content. The local JSONL layout is still a product compatibility surface, not a CMRO-owned API. Missing or changed metadata produces `not_verified` and stops the run.

## Configuration is not runtime proof

`routerctl` proves intended files and hashes. A model pin passed at task creation proves selection intent. Final verification additionally requires the resulting session's observed model, effort, task ID, and repository CWD. Task names, titles, prompts, filenames, and self-reports are insufficient.

## Static tests do not prove optimization

The automated suite covers installer behavior, payload integrity, session-probe parsing, and repository contracts. It does not prove routing quality, reviewer accuracy, cost reduction, latency improvement, or universal workflow compliance. Publish those claims only from dated, reproducible observed runs.

## Shared working trees remain shared

The one-writer rule avoids intentional collisions; it cannot prevent unrelated people, processes, or dormant tasks from editing. Baseline, status, and final-diff checks remain necessary.

## Exact verification treats customization as drift

Installed managed files must match the source distribution. Customize the source payload, regenerate its manifest, test it, and install from that fork.

## Stronger models do not expand authority

Routing to Terra and adding Sol review does not make deployments, migrations, billing changes, credential operations, or destructive actions harmless. Keep explicit approvals, reversible stages, backups, and platform safeguards.
