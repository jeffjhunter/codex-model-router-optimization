# CMRO protocol v1

These packet shapes make handoffs inspectable. YAML examples are illustrative; native Codex does not enforce them as a state machine.

## Coordinator plan

```yaml
schema: "cmro.plan.v1"
run_id: "cmro-20260713-a1b2"
plan_version: 1
request: "Concise description of the requested outcome"
baseline:
  kind: "git"
  value: "commit-or-explicit-description"
requirements:
  - id: "RQ-001"
    text: "User-visible requirement"
acceptance:
  - id: "AC-001"
    rq_ids: ["RQ-001"]
    condition: "Atomic pass/fail condition"
    verification: "Command, inspection, or source check"
scope:
  allowed_paths: ["path/or/glob"]
  prohibited_actions: ["unapproved external writes"]
  authority: "local workspace only"
routing:
  worker: "balanced_worker"
  reviewer: "standard_reviewer"
  rationale: "Multi-file implementation with regression risk"
attempt_limit: 3
```

## Worker report

```yaml
schema: "cmro.worker.v1"
run_id: "cmro-20260713-a1b2"
plan_version: 1
attempt: 1
worker:
  id: "retained-agent-id"
  route: "balanced_worker"
status: "done" # done | blocked
summary: "What changed or why work stopped"
changed_paths:
  - path: "src/example.py"
    action: "modified"
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

Use `not_run` only for a check that was not executed and explain why. Use `not_verified` when a criterion lacks sufficient proof. Do not invent intermediate status values.

## Reviewer decision

```yaml
schema: "cmro.review.v1"
run_id: "cmro-20260713-a1b2"
plan_version: 1
reviewer:
  id: "retained-reviewer-id"
  route: "standard_reviewer"
decision: "accept" # accept | revise | needs_human_review
criteria:
  - ac_id: "AC-001"
    status: "pass" # pass | fail | not_verified
    evidence: "Independent observation"
findings:
  - id: "F-001"
    severity: "high" # critical | high | medium | low
    ac_ids: ["AC-001"]
    evidence: "Reproduction steps and current artifact reference"
    requested_outcome: "Observable correction, not an implementation prescription"
verification:
  - command: "python -m unittest"
    exit_code: 0
    result: "pass"
limitations: []
```

An `accept` decision requires every current acceptance criterion to pass and no unresolved critical or high finding. `needs_human_review` is appropriate when a safe technical revision cannot resolve the issue within current authority.

## Root final record

```yaml
schema: "cmro.final.v1"
run_id: "cmro-20260713-a1b2"
plan_version: 1
status: "complete" # complete | needs_human_review
attempts: 1
worker_id: "retained-agent-id"
reviewer_id: "retained-reviewer-id"
requirements:
  - rq_id: "RQ-001"
    ac_ids: ["AC-001"]
    status: "pass"
verification_summary: "What the root gate independently confirmed"
blockers: []
```

## Version and identity rules

- Keep `run_id` stable for the entire run.
- Increment `plan_version` for material user steering or scope changes.
- Reject packets for a different run or stale plan version.
- Keep worker and reviewer IDs stable across actionable revision cycles.
- Count no more than three worker attempts.
- Preserve blocked evidence instead of rewriting it as success.
