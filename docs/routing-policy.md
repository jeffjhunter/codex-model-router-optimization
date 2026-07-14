# Routing policy

Routing minimizes cost and latency only after satisfying the task’s risk envelope. It does not route by desired output length.

## Decision sequence

1. Identify authority and external effects.
2. Identify sensitive domains: authentication, authorization, secrets, privacy, durable data, production, billing, or destructive operations.
3. Determine ambiguity, dependency count, integration surface, and regression risk.
4. Determine whether verification is deterministic and exhaustive.
5. Choose the lowest route that covers every material concern.

## Worker matrix

| Signal | Fast | Balanced | Deep |
| --- | :---: | :---: | :---: |
| Clear, mechanical transformation | ✓ | ✓ | ✓ |
| Deterministic exhaustive checks | required | preferred | preferred |
| Several dependent files or tools |  | ✓ | ✓ |
| Meaningful design judgment |  | ✓ | ✓ |
| Ordinary integration/regression risk |  | ✓ | ✓ |
| Authentication, secrets, privacy |  |  | ✓ |
| Destructive or hard-to-reverse effects |  |  | ✓ |
| Data migration or production state |  |  | ✓ |
| Cross-system authority or billing |  |  | ✓ |

Choose the stronger route when evidence is incomplete. A stronger model never expands the user’s authorization.

## Reviewer matrix

Use `standard_reviewer` for fast and balanced tasks unless a deep-risk concern appears. Use `deep_reviewer` for deep tasks and any artifact where security, privacy, authorization, irreversible effects, or data integrity are material.

The reviewer receives the original request, current plan, baseline, artifact or diff, and worker report. It should rerun safe checks or inspect source directly rather than accepting the report at face value.

## Examples

| Task | Expected route | Reason |
| --- | --- | --- |
| Rename images using a supplied one-to-one map | Fast | Mechanical, reversible, and exhaustively checkable |
| Convert a CSV to a fixed JSON schema | Fast | Deterministic transformation with schema validation |
| Add pagination to an internal list page | Balanced | Multi-file behavior and regression risk |
| Research and draft a cited technical comparison | Balanced | Tool use, source judgment, and synthesis |
| Repair an authorization bypass | Deep + deep review | Security boundary and adversarial input |
| Plan a production database migration | Deep + deep review | Durable data, rollback, and operational risk |

## Escalation

- Escalate fast to balanced when ambiguity, broad tool use, or regression risk appears.
- Escalate balanced to deep when a deep-risk boundary appears or reasoning complexity blocks safe work.
- Do not escalate model depth to compensate for missing credentials, user choices, permission, or production context. Stop for human review.
- Never leave the old and new writer active together. Preserve evidence, close the old writer if possible, and hand the current plan to the replacement.

## Why the default models look this way

The profile uses `gpt-5.6-terra` for the fast route and `gpt-5.6` at increasing reasoning levels for demanding workers and reviewers. Current OpenAI guidance describes Terra as the faster, lower-cost option for lighter supporting work and recommends stronger GPT-5.6 configurations for ambiguous, multi-step work. Availability and supported effort levels can change; see [compatibility](compatibility.md).
