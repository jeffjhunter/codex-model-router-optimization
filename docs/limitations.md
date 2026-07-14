# Limitations

## Native orchestration is best effort

Codex provides custom agents, skills, subagent controls, and project guidance. CMRO expresses a lifecycle through those primitives, but native instructions do not enforce every transition as application code would. Same-worker follow-up, reviewer reuse, attempt counting, and the root gate depend on the coordinator following the protocol.

Use an SDK controller when transition enforcement, durable recovery, auditable persistence, or machine-validated schemas are mandatory.

## No hard ordinary-turn timeout

The profile does not claim a hard timeout for ordinary subagent turns. The Codex config field for CSV-spawn job runtime is not a general agent-turn deadline. Slow or stalled handoffs may require user or root intervention.

## Reviewer read-only is not absolute isolation

A custom reviewer requests a read-only sandbox and is behaviorally prohibited from writing. Parent live permission overrides can still change the effective sandbox. Tool-specific external permissions may also differ.

## Model access is not verified

`routerctl` validates local configuration and file integrity. It cannot know which model IDs or reasoning levels are enabled for a particular account, workspace, region, client, or rollout.

## Tests validate distribution behavior

The automated tests exercise installer, verifier, manifest, config, path, ownership, and release behavior. They do not prove route-selection quality, reviewer accuracy, cost reduction, or universal workflow compliance. Those claims require dated behavioral evaluations.

## Shared working trees remain shared

The one-writer rule avoids intentional agent collisions; it cannot prevent unrelated processes or humans from editing simultaneously. Baseline and final-diff checks remain necessary.

## Exact verification treats customization as drift

Installed managed agent and skill files must match the source distribution. This catches silent changes but means target-local prompt customization fails verification. Customize the source payload, regenerate its manifest, test it, and install from that fork.

## User-approved side effects are still risky

Routing to a deeper worker improves analysis; it does not make deployments, migrations, billing changes, credential operations, or destructive actions harmless. Use explicit approvals, reversible stages, backups, and platform-native safeguards.
