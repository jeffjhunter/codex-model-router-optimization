# CMRO protocol v3

These packet shapes make model selection, runtime observation, and handoffs inspectable. Coordinator and final-record YAML is shown for readability; native Codex does not enforce a state machine.

Worker and reviewer task responses are normative serialization boundaries: the complete response must be exactly one raw JSON object with no Markdown fence or surrounding prose. The root validates each object with `scripts/validate_packet.py` against authoritative context before handoff. It may request one separately accounted, no-write format repair from the same retained task when an otherwise useful action response is invalid.

## Coordinator plan

```yaml
schema: "cmro.plan.v3"
run_id: "cmro-20260714-a1b2"
plan_version: 1
request: "Concise description of the requested outcome"
baseline: {kind: "git", value: "commit"}
requirements:
  - {id: "RQ-001", text: "User-visible requirement"}
acceptance:
  - id: "AC-001"
    rq_ids: ["RQ-001"]
    condition: "Atomic pass/fail condition"
    verification: "Command, inspection, or source check"
scope:
  allowed_paths: ["path/or/glob"]
  prohibited_actions: ["unapproved external writes"]
  authority: "local workspace only"
backend:
  kind: "codex_app_tasks" # codex_app_tasks | native_custom_agent
  project_id: "/canonical/saved/project"
  environment: "local"
  capability_evidence:
    - "model-pinned task creation"
    - "task status/read"
    - "retained-task follow-up"
  actor_contract_sha256: "sha256"
routing:
  coordinator: {route: "root", configured_model: "gpt-5.6-sol"}
  worker: {route: "terra_worker", configured_model: "gpt-5.6-terra"}
  reviewer: {route: "sol_reviewer", configured_model: "gpt-5.6-sol"}
  score: 3
  rationale: "Multi-file implementation, tool use, and regression risk"
identity:
  root:
    control_plane_pinned: true
    runtime_observed: true
    task_id: "root-task-id"
    turn_ids: ["root-turn-id"]
    value: "gpt-5.6-sol/xhigh"
    source: "privacy-minimized local session observation"
  worker: {control_plane_pinned: false, runtime_observed: false, turn_ids: []}
  reviewer: {control_plane_pinned: false, runtime_observed: false, turn_ids: []}
attempt_limit: 3
```

## Identity preflight

```yaml
schema: "cmro.preflight.v3"
run_id: "cmro-20260714-a1b2"
plan_version: 1
role: "terra_worker"
status: "ready" # ready | blocked
observed_cwd: "/canonical/saved/project"
observed_baseline: "commit"
git_status: "clean"
blockers: []
```

This packet is task-reported readiness, not model proof. The root must wait for the completed preflight turn, capture its turn ID, and independently bind a session observation to that task and turn. It must repeat exact-turn observation for every later implementation, revision, review, and rereview turn before accepting that turn's packet.

## Worker report

```json
{
  "schema": "cmro.worker.v3",
  "run_id": "cmro-20260714-a1b2",
  "plan_version": 1,
  "attempt": 1,
  "worker": {
    "id": "retained-task-or-agent-id",
    "backend": "codex_app_tasks",
    "route": "terra_worker",
    "configured_model": "gpt-5.6-terra"
  },
  "status": "done",
  "summary": "What changed or why work stopped",
  "changed_paths": [
    {"path": "src/example.py", "action": "modified"}
  ],
  "checks": [
    {
      "command": "python -m unittest",
      "exit_code": 0,
      "result": "pass",
      "evidence": "Observed output or failure detail"
    }
  ],
  "criteria": [
    {"ac_id": "AC-001", "status": "pass", "evidence": "Current artifact or check evidence"}
  ],
  "blockers": [],
  "limitations": []
}
```

Allowed path actions are `created`, `modified`, `deleted`, and `renamed`. Allowed-path globs are segment-aware: `*` stays within one path segment, `**` spans segments, and a trailing `/` authorizes that directory subtree. Use `not_run` only for an unexecuted check and explain why. Use `not_verified` when proof is insufficient. A blocked report requires a blocker. Do not invent intermediate status values.

## Reviewer decision

```json
{
  "schema": "cmro.review.v3",
  "run_id": "cmro-20260714-a1b2",
  "plan_version": 1,
  "reviewer": {
    "id": "retained-task-or-agent-id",
    "backend": "codex_app_tasks",
    "route": "sol_reviewer",
    "configured_model": "gpt-5.6-sol"
  },
  "decision": "revise",
  "criteria": [
    {"ac_id": "AC-001", "status": "fail", "evidence": "Independent observation"}
  ],
  "findings": [
    {
      "id": "F-001",
      "severity": "high",
      "ac_ids": ["AC-001"],
      "evidence": "Reproduction steps and current artifact reference",
      "requested_outcome": "Observable correction, not an implementation prescription"
    }
  ],
  "verification": [
    {"command": "python -m unittest", "exit_code": 0, "result": "pass", "evidence": "Observed output"}
  ],
  "blockers": [],
  "limitations": []
}
```

An `accept` decision requires every current criterion and verification result to pass, at least one verification result, empty findings and blockers, and no reviewer-time mutation. `revise` requires at least one non-passing criterion, and each finding must reference only non-passing criteria.

## Authoritative packet-validation context

The root supplies context independently; it is never copied from the packet being checked. A worker context includes the current attempt and allowed paths:

```json
{
  "run_id": "cmro-20260714-a1b2",
  "plan_version": 1,
  "backend": "codex_app_tasks",
  "actor_id": "retained-task-or-agent-id",
  "route": "terra_worker",
  "configured_model": "gpt-5.6-terra",
  "attempt": 1,
  "acceptance_ids": ["AC-001"],
  "allowed_paths": ["src/**", "tests/**"]
}
```

Validate a raw packet from a file or stdin:

```text
python .agents/skills/route-codex-work/scripts/validate_packet.py worker-response.json --context context.json
python .agents/skills/route-codex-work/scripts/validate_packet.py - --context-json '<authoritative JSON>'
```

Reviewer context binds the same run, plan, backend, actor, route/model, and acceptance IDs but omits worker-only `attempt` and `allowed_paths`.

## Root final record

```yaml
schema: "cmro.final.v3"
run_id: "cmro-20260714-a1b2"
plan_version: 1
status: "complete" # complete | needs_human_review
attempts: 1
backend: "codex_app_tasks"
worker_id: "retained-task-or-agent-id"
reviewer_id: "retained-task-or-agent-id"
identity:
  root:
    control_plane_pinned: true
    runtime_observed: true
    task_id: "root-task-id"
    turn_ids: ["root-turn-id"]
    value: "gpt-5.6-sol/xhigh"
  worker:
    control_plane_pinned: true
    runtime_observed: true
    task_id: "worker-task-id"
    preflight_turn_id: "worker-preflight-turn-id"
    turn_ids: ["worker-preflight-turn-id", "worker-implementation-turn-id"]
    action_turn_ids: ["worker-implementation-turn-id"]
    packet_repair_turn_ids: []
    value: "gpt-5.6-terra/high"
  reviewer:
    control_plane_pinned: true
    runtime_observed: true
    task_id: "review-task-id"
    preflight_turn_id: "review-preflight-turn-id"
    turn_ids: ["review-preflight-turn-id", "review-turn-id"]
    action_turn_ids: ["review-turn-id"]
    packet_repair_turn_ids: []
    value: "gpt-5.6-sol/xhigh"
review_snapshots:
  - reviewer_turn_id: "review-turn-id"
    scope: "tracked-index-and-untracked-content"
    before_sha256: "64-lowercase-hex-characters"
    after_sha256: "the-same-64-lowercase-hex-characters"
    matched: true
packet_repairs: []
requirements:
  - {rq_id: "RQ-001", ac_ids: ["AC-001"], status: "pass"}
verification_summary: "What the root gate independently confirmed"
blockers: []
```

When a format repair occurred, add one entry such as:

```json
{
  "actor_role": "worker",
  "invalid_turn_id": "worker-implementation-turn-id",
  "repaired_turn_id": "worker-format-repair-turn-id",
  "mode": "format-only",
  "writes": false,
  "reason": "Initial response failed cmro.worker.v3 packet validation",
  "snapshot": {
    "scope": "tracked-index-and-untracked-content",
    "before_sha256": "64-lowercase-hex-characters",
    "after_sha256": "the-same-64-lowercase-hex-characters",
    "matched": true
  }
}
```

The invalid action turn stays in `action_turn_ids`; the no-write follow-up belongs only in `packet_repair_turn_ids`. Both remain in `turn_ids` because both require independent runtime observation. `attempts` counts worker action turns, and review snapshots cover reviewer action turns, never repair turns. Records that omit the new accounting fields retain legacy v3 interpretation for backward compatibility.

## Version, identity, and task rules

- Keep `run_id` stable and increment `plan_version` after material steering.
- Reject packets for another run, a stale plan, or a missing/truncated task result.
- Keep writer and reviewer IDs stable across actionable revision cycles.
- Record whether each ID is a model-pinned app task or explicitly selected native custom agent.
- Keep `control_plane_pinned` separate from `runtime_observed`; both must be true for every role before `complete`.
- Record every material observed turn in that actor's `turn_ids`. Worker and reviewer records must identify their preflight turn, action turns, and packet-repair turns separately. Observe each exact turn before accepting its packet.
- Never use a task label, `task_name`, prompt claim, filename, or self-report as selection or runtime proof.
- For app tasks, require exact saved-project matching, explicit model/effort parameters, a completed no-write preflight, the completed preflight turn ID, `parent_thread_id == null`, and an exact session observation before work.
- For native custom agents, require an explicit selector, no-write first turn, status/read with exact completed turn IDs, same-agent follow-up, and session observation. Bind every observation to the child's own completed turn ID and expected parent.
- Follow task-read pagination or raise output limits until the complete final packet is available.
- Take root-owned content snapshots immediately before and after every review. A complete record requires matching digests for every accepted review turn; `git status` equality alone is insufficient.
- Initialize the first implementation as attempt 1 and increment before each revision. Count at most three implementation attempts; identity preflights and packet repairs do not consume an attempt, and completion requires at least one action attempt. A complete run has one independently observed reviewer action turn and one matching snapshot pair for every worker action attempt.
- A final record with unavailable, ambiguous, or mismatched identity evidence must use `needs_human_review`.
