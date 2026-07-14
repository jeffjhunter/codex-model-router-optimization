# Routing policy

CMRO spends Sol tokens on the contract and gates, sends bulk production to Luna or Terra, and routes by ambiguity and verifiability rather than output length.

## Fixed roles

| Role | Model | Effort | Responsibility |
| --- | --- | --- | --- |
| Root coordinator | `gpt-5.6-sol` | xhigh | Define success, select route, retain state, apply final gate |
| Luna writer | `gpt-5.6-luna` | medium | Clear, repeatable, deterministic transformations |
| Terra writer | `gpt-5.6-terra` | high | Everyday multi-file, tool-heavy, ambiguous, recovery, and high-impact work |
| Sol reviewer | `gpt-5.6-sol` | xhigh | Independent read-only evidence review |

## Luna or Terra score

Give one point for each signal:

1. Material ambiguity.
2. Several dependent steps or files.
3. Tool use or environment inspection.
4. Recovery from partial failure.
5. Judgment-heavy synthesis or regression risk.

Route 0–1 to Luna and 2–5 to Terra. When evidence is incomplete, choose Terra. High-impact work stays with Terra but adds explicit threat, authority, rollback, data-integrity, and operational checks to the plan and Sol review. A stronger route never expands authorization.

## Examples

| Task | Score and route | Reason |
| --- | --- | --- |
| Rename images from a supplied bijective map | 1 → Luna | Mechanical and exhaustively checkable |
| Convert a CSV to a fixed schema | 1 → Luna | Deterministic transformation and validation |
| Add pagination to an internal list | 3 → Terra | Multiple files, tools, regression risk |
| Draft a cited technical comparison | 3 → Terra | Tools, source judgment, synthesis |
| Repair an authorization bypass | Terra + adversarial Sol review | Security boundary; local authority remains fixed |
| Plan a production migration | Terra + adversarial Sol review | Durable data, rollback, and operational risk |

## Runtime identity gate

Exact TOML files and hashes prove the intended configuration. They do not prove entitlement or the model actually selected for a spawned session. A verified pilot must separately record client/session evidence showing:

- root: Sol;
- writer: the selected Luna or Terra custom agent/model;
- reviewer: a different Sol session.

A prompt label, thread name, agent self-report, or filename is not independent proof. If the client does not expose model identity, record `not_verified` and stop at `needs_human_review` rather than marketing the run as verified model routing.

## Escalation

- Escalate Luna to Terra when ambiguity, dependent edits, broad tools, recovery, or regression risk appears.
- Do not use a stronger model to compensate for missing permission, credentials, policy, or production context; stop for human review.
- Never leave old and replacement writers active together. Preserve evidence and hand off explicitly.
