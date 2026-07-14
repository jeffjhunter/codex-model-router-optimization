# Illustrative run

> This is a design example, not an authenticated Codex transcript or benchmark result.

## Request

```text
$route-codex-work Add a --json flag to the local status command. Preserve text output, add focused tests, and keep all work local.
```

## 1. Root contract

The coordinator records `RQ-001` for JSON output, `RQ-002` for backward-compatible text output, `RQ-003` for tests, and `RQ-004` for local-only scope. It creates atomic criteria, captures the Git baseline, selects `balanced_worker`, and records the spawned worker ID.

See [plan-packet.yaml](plan-packet.yaml).

## 2. Worker attempt 1

The retained worker implements the flag and tests. Its report says every criterion passes and includes commands, exits, changed paths, and limitations.

See [worker-report.yaml](worker-report.yaml).

## 3. Independent review

The reviewer inspects the diff and reruns focused tests. It finds that redirected text output changed its final newline, marks the backward-compatibility criterion failed, and requests the observable old behavior—not a prescribed code edit.

See [review-revise.yaml](review-revise.yaml).

## 4. Same-worker revision

The coordinator sends only the failed criterion, reproduction, and requested outcome to the recorded worker ID as attempt 2. The worker fixes the behavior and updates its evidence.

## 5. Review and root gate

The retained reviewer accepts the current plan version. The root independently checks requirement coverage, current paths, test evidence, and local-only scope before returning complete.

The key properties are identity continuity, current-version evidence, an independent artifact check, and a root gate. The prose alone does not guarantee native Codex will always produce this sequence.
