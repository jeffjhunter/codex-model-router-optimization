<!-- codex-model-router:begin -->
## Routed Codex workflow

Apply these rules only when the user explicitly invokes `$route-codex-work` or directly requests the installed routed workflow.

- Keep the root thread responsible for the request contract, scope, agent identities, plan version, attempt count, and final acceptance.
- Use one write-capable worker at a time. Read-only discovery may run concurrently, but it must not race the writer.
- Route work through `fast_worker`, `balanced_worker`, or `deep_worker` according to risk and verifiability. When uncertain, choose the stronger route.
- Give an independent `standard_reviewer` or `deep_reviewer` the current plan, baseline, artifact, and worker evidence.
- Return actionable revision findings to the same worker ID. Allow no more than three total worker attempts.
- Increment the plan version after material user steering and invalidate stale review evidence.
- Require artifact-, check-, or source-based proof for completion. Missing proof remains `not_verified`.
- Stop with `needs_human_review` when authority, input, evidence, or a safe continuation path is missing.
- Do not create repository-local orchestration logs or state files unless the user requests them as deliverables.
- Treat native skill sequencing as best effort; do not claim a hard timeout or deterministic state machine.
<!-- codex-model-router:end -->
