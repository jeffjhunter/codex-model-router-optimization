# Routing policy

CMRO spends Sol on the contract and gates, sends production to Luna or Terra, and returns the artifact to a separate Sol reviewer. It routes by ambiguity and verifiability rather than output length.

## Fixed roles

| Role | Model | Effort | Responsibility |
| --- | --- | --- | --- |
| Root coordinator | `gpt-5.6-sol` | xhigh | Define success, select backend and route, retain state, apply final gate |
| Luna writer | `gpt-5.6-luna` | medium | Clear, repeatable, deterministic transformations |
| Terra writer | `gpt-5.6-terra` | high | Multi-file, tool-heavy, ambiguous, recovery, and high-impact work |
| Sol reviewer | `gpt-5.6-sol` | xhigh | Independent evidence review |

## Luna or Terra score

Give one point for each signal:

1. Material ambiguity.
2. Several dependent steps or files.
3. Tool use or environment inspection.
4. Recovery from partial failure.
5. Judgment-heavy synthesis or regression risk.

Route 0–1 to Luna and 2–5 to Terra. When evidence is incomplete, choose Terra. High-impact work stays with Terra but adds explicit threat, authority, rollback, integrity, and operational checks. A stronger model never expands authorization.

## Backend gate

Route scoring chooses a model; it does not launch one.

Prefer model-pinned Codex app tasks when the coordinator can resolve the exact saved local project, create tasks with explicit model/effort, read their completed turns, and send follow-ups without changing the model. Use native custom agents only when the surface also provides an explicit custom-agent/profile/type selector, a no-write initial turn, idle/terminal reads with exact completed turn IDs, retained-agent follow-up, and session observation.

Never treat `task_name`, a thread title, a role-like prompt, or an agent filename as model selection.

## Runtime identity gate

Each actor starts with a no-write preflight. After the task becomes idle, the coordinator captures its completed preflight turn ID and verifies that exact task/turn from local session metadata. It repeats this check for every implementation, revision, review, and rereview turn. Every observation must match model, effort, repository CWD, and the expected top-level app-task or native-parent status.

Keep control-plane intent separate from runtime observation. Both must pass for root, writer, and reviewer before completion. Missing, ambiguous, inherited-only, or mismatched evidence produces `needs_human_review`.

## Examples

| Task | Score and route | Reason |
| --- | --- | --- |
| Rename images from a supplied bijective map | 1 → Luna | Mechanical and exhaustively checkable |
| Convert a CSV to a fixed schema | 1 → Luna | Deterministic transformation and validation |
| Add pagination to an internal list | 3 → Terra | Multiple files, tools, regression risk |
| Draft a cited technical comparison | 3 → Terra | Tools, source judgment, synthesis |
| Repair an authorization bypass | Terra + adversarial Sol review | Security boundary; local authority remains fixed |
| Plan a production migration | Terra + adversarial Sol review | Durable data, rollback, and operational risk |

## Escalation

- Escalate Luna to Terra when ambiguity, dependent edits, broad tools, recovery, or regression risk appears.
- Do not use a stronger model to compensate for missing permission, credentials, policy, or production context.
- Never leave old and replacement writers active together.
- Preserve failed identity and task evidence rather than relabeling or retrying with the root model.
