<!-- codex-model-router:begin -->
## Routed Codex workflow

Apply these rules only when the user explicitly invokes `$route-codex-work` or directly requests the installed routed workflow.

- Keep the root thread responsible for the request contract, scope, agent identities, plan version, attempt count, and final acceptance.
- Use one write-capable worker at a time. Read-only discovery may run concurrently, but it must not race the writer.
- Keep the root coordinator on `gpt-5.6-sol`; route clear mechanical work to `luna_worker` and normal, ambiguous, tool-heavy, recovery, or high-impact work to `terra_worker`.
- Prefer model-pinned Codex app tasks in the exact saved local project. Run a no-write identity preflight, independently verify it, then continue the retained task and verify every exact implementation, revision, review, and rereview turn.
- Copy the installed app-task actor contract into each task prompt; normal app tasks do not activate custom-agent TOML developer instructions. Require complete protocol-v3 packets from idle/completed turns.
- Require exactly one raw JSON worker/reviewer object and validate it with `validate_packet.py` against root-owned run, plan, actor, route/model, acceptance, attempt, and path context before handoff.
- If a useful action turn returns only an invalid packet, permit one no-write, same-task format repair with exact-turn observation and matching before/after content snapshots. Record it separately; never count it as an implementation attempt or review action.
- Use native custom agents only when the surface provides an explicit custom-agent/profile/type selector, no-write first turn, status/read with exact completed turn IDs, same-agent follow-up, and session observation. `task_name`, a thread label, or a prompt claim is not model selection.
- Give a separate `sol_reviewer` the current plan, baseline, artifact, and worker evidence.
- Treat configured model names as expected state, not runtime proof. Require independent client/session evidence for every material Sol → Luna/Terra → Sol turn before claiming a verified model-routing run.
- Compare root-owned content snapshots immediately before and after every review; matching `git status` text is insufficient.
- Return actionable revision findings to the same worker ID. Start the first implementation at attempt 1, increment before each revision, and allow no more than three total worker attempts.
- Increment the plan version after material user steering and invalidate stale review evidence.
- Require artifact-, check-, or source-based proof for completion. Missing proof remains `not_verified`.
- Stop with `needs_human_review` when authority, input, evidence, or a safe continuation path is missing.
- Do not create repository-local orchestration logs or state files unless the user requests them as deliverables.
- Treat native skill sequencing as best effort; do not claim a hard timeout or deterministic state machine.
<!-- codex-model-router:end -->
