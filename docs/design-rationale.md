# Design rationale

## Explicit invocation

Multi-agent workflows consume more tokens and add latency. CMRO disables implicit skill invocation so ordinary repository tasks keep normal Codex behavior. The user opts in with `$route-codex-work`.

## Sol root by default

A top-level project model changes every root prompt, not just routed runs. CMRO 2 pins Sol because Sol coordination is part of the product contract and an unpinned root cannot mechanically verify the expected configuration. The installer surfaces conflicts instead of silently replacing an existing project model.

## Luna or Terra

A five-signal score routes production to:

- Luna for clear, repeatable, mechanically verifiable work; and
- Terra for multi-file, tool-heavy, ambiguous, recovery, or high-impact work.

High-impact work stays with Terra but adds threat, rollback, data-integrity, and authority checks. Model choice never substitutes for missing authorization.

## One independent Sol reviewer

Every run uses a separate read-only Sol reviewer. Ordinary work gets correctness, scope, regression, and evidence checks; high-impact work adds adversarial concerns to the same reviewer contract.

## Atomic criteria instead of a point score alone

Risk heuristics select a route; acceptance criteria decide success. Every requirement maps to an atomic criterion with a verification method, which gives the reviewer and root gate a shared observable contract.

## Root-owned ephemeral state

The coordinator’s state remains in the root task unless the user asks for an audit artifact. Application repositories should not receive hidden orchestration logs merely because a skill ran. The root retains agent IDs and plan versions to prevent stale or self-authored evidence from becoming authoritative.

## Same-worker revision

Actionable feedback returns to the retained writer so the task context and implementation intent are not reconstructed on every attempt. A writer replacement is a controlled escalation, never a silent reset or a concurrent edit race.

## Bounded retries without fake timeouts

Three total worker attempts limit repeated cost and failure. CMRO does not misuse unrelated config settings to claim a hard ordinary-turn timeout; interrupted or slow turns require explicit coordination.

## Deterministic distribution, honest runtime claims

Installation and verification can be enforced by code, hashes, filesystem checks, and tests. Native agent sequencing cannot. The project treats those layers differently and recommends an SDK controller when application-enforced transitions are required.

## Independent lineage

The Sol → Luna/Terra → Sol workflow was inspired by Matt Farmer’s public article, credited in [CREDITS.md](../CREDITS.md). CMRO is independently authored with an explicit-only policy, model-observation gate, versioned packets, cross-platform transactional tooling, and an open evaluation framework.
