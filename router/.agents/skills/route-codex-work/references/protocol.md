# CMRO protocol v3

These packet shapes make model selection, runtime observation, and handoffs inspectable. YAML examples are illustrative; native Codex does not enforce them as a state machine.

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

```yaml
schema: "cmro.worker.v3"
run_id: "cmro-20260714-a1b2"
plan_version: 1
attempt: 1
worker:
  id: "retained-task-or-agent-id"
  backend: "codex_app_tasks"
  route: "terra_worker"
  configured_model: "gpt-5.6-terra"
status: "done" # done | blocked
summary: "What changed or why work stopped"
changed_paths:
  - {path: "src/example.py", action: "modified"}
checks:
  - command: "python -m unittest"
    exit_code: 0
    result: "pass" # pass | fail | not_run
    evidence: "Observed output or failure detail"
criteria:
  - ac_id: "AC-001"
    status: "pass" # pass | fail | not_verified
    evidence: "Current artifact or check evidence"
blockers: []
limitations: []
```

Use `not_run` only for an unexecuted check and explain why. Use `not_verified` when proof is insufficient. Do not invent intermediate status values.

## Reviewer decision

```yaml
schema: "cmro.review.v3"
run_id: "cmro-20260714-a1b2"
plan_version: 1
reviewer:
  id: "retained-task-or-agent-id"
  backend: "codex_app_tasks"
  route: "sol_reviewer"
  configured_model: "gpt-5.6-sol"
decision: "accept" # accept | revise | needs_human_review
criteria:
  - {ac_id: "AC-001", status: "pass", evidence: "Independent observation"}
findings:
  - id: "F-001"
    severity: "high" # critical | high | medium | low
    ac_ids: ["AC-001"]
    evidence: "Reproduction steps and current artifact reference"
    requested_outcome: "Observable correction, not an implementation prescription"
verification:
  - {command: "python -m unittest", exit_code: 0, result: "pass"}
limitations: []
```

An `accept` decision requires every current criterion to pass, no unresolved critical/high finding, and no reviewer-time mutation.

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
    value: "gpt-5.6-terra/high"
  reviewer:
    control_plane_pinned: true
    runtime_observed: true
    task_id: "review-task-id"
    preflight_turn_id: "review-preflight-turn-id"
    turn_ids: ["review-preflight-turn-id", "review-turn-id"]
    value: "gpt-5.6-sol/xhigh"
review_snapshots:
  - reviewer_turn_id: "review-turn-id"
    scope: "tracked-index-and-untracked-content"
    before_sha256: "64-lowercase-hex-characters"
    after_sha256: "the-same-64-lowercase-hex-characters"
    matched: true
requirements:
  - {rq_id: "RQ-001", ac_ids: ["AC-001"], status: "pass"}
verification_summary: "What the root gate independently confirmed"
blockers: []
```

## Version, identity, and task rules

- Keep `run_id` stable and increment `plan_version` after material steering.
- Reject packets for another run, a stale plan, or a missing/truncated task result.
- Keep writer and reviewer IDs stable across actionable revision cycles.
- Record whether each ID is a model-pinned app task or explicitly selected native custom agent.
- Keep `control_plane_pinned` separate from `runtime_observed`; both must be true for every role before `complete`.
- Record every material observed turn in that actor's `turn_ids`. Worker and reviewer records must identify their preflight turn separately and include at least one later action turn. Observe each exact turn before accepting its packet.
- Never use a task label, `task_name`, prompt claim, filename, or self-report as selection or runtime proof.
- For app tasks, require exact saved-project matching, explicit model/effort parameters, a completed no-write preflight, the completed preflight turn ID, `parent_thread_id == null`, and an exact session observation before work.
- For native custom agents, require an explicit selector, no-write first turn, status/read with exact completed turn IDs, same-agent follow-up, and session observation. Bind every observation to the child's own completed turn ID and expected parent.
- Follow task-read pagination or raise output limits until the complete final packet is available.
- Take root-owned content snapshots immediately before and after every review. A complete record requires matching digests for every accepted review turn; `git status` equality alone is insufficient.
- Initialize the first implementation as attempt 1 and increment before each revision. Count at most three implementation attempts; identity preflights do not consume an attempt and completion requires at least one attempt. A complete run has one independently observed reviewer action turn and one matching snapshot pair for every worker attempt.
- A final record with unavailable, ambiguous, or mismatched identity evidence must use `needs_human_review`.
