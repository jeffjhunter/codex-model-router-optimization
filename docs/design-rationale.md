# Design rationale

## Explicit invocation

Multi-agent workflows consume more tokens and add latency. CMRO disables implicit skill invocation so ordinary repository tasks keep normal Codex behavior. The user opts in with `$route-codex-work`.

## Sol root by default

A top-level project model changes every root prompt, not just routed runs. CMRO pins Sol because Sol coordination is part of the product contract and an unpinned root cannot mechanically verify the expected configuration. The installer surfaces conflicts instead of silently replacing an existing project model.

## Model-pinned app tasks before named subagents

An early Fieldstead preflight proved that naming a generic native child `terra_worker` did not load Terra: the child's own runtime remained Sol. A separate app task created with explicit Terra/high parameters did select Terra in the correct repository. CMRO 3 therefore prefers model-pinned app tasks and permits native routing only when the client supplies the full staged selector, turn-read, retained-follow-up, and observation contract.

Every app actor starts read-only, reaches an idle READY state, and is then bound to task-and-turn-specific session evidence before receiving real work. This costs an extra turn but prevents labels and inherited context from becoming false proof.

## Luna or Terra

A five-signal score routes production to:

- Luna for clear, repeatable, mechanically verifiable work; and
- Terra for multi-file, tool-heavy, ambiguous, recovery, or high-impact work.

High-impact work stays with Terra but adds threat, rollback, data-integrity, and authority checks. Model choice never substitutes for missing authorization.

## One independent Sol reviewer

Every run uses a separate Sol reviewer task with a read-only behavioral contract. Ordinary work gets correctness, scope, regression, and evidence checks; high-impact work adds adversarial concerns. Root-owned pre/post-review content snapshots detect lasting mutation, including edits that do not change `git status` categories, because app task creation does not itself provide a reviewer-only sandbox parameter.

## Atomic criteria instead of a point score alone

Risk heuristics select a route; acceptance criteria decide success. Every requirement maps to an atomic criterion with a verification method, which gives the reviewer and root gate a shared observable contract.

## Root-owned ephemeral state

The coordinator’s state remains in the root task unless the user asks for an audit artifact. Application repositories should not receive hidden orchestration logs merely because a skill ran. The root retains agent IDs and plan versions to prevent stale or self-authored evidence from becoming authoritative.

## Same-worker revision

Actionable feedback returns to the retained writer so the task context and implementation intent are not reconstructed on every attempt. A writer replacement is a controlled escalation, never a silent reset or a concurrent edit race.

## Bounded retries without fake timeouts

Three total worker attempts limit repeated cost and failure. CMRO does not misuse unrelated config settings to claim a hard ordinary-turn timeout; interrupted or slow turns require explicit coordination.

## Deterministic distribution, honest runtime claims

Installation, parser behavior, and payload verification can be enforced by code, hashes, filesystem checks, and tests. Task sequencing is still instruction-driven. The project labels distribution checks, control-plane preflights, observed runs, and benchmarks separately, and recommends an SDK controller when application-enforced transitions are required.

## Independent lineage

The Sol → Luna/Terra → Sol workflow was inspired by Matt Farmer’s public article, credited in [CREDITS.md](../CREDITS.md). CMRO is independently authored with an explicit-only policy, model-observation gate, versioned packets, cross-platform transactional tooling, and an open evaluation framework.
