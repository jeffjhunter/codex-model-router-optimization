# Design rationale

## Explicit invocation

Multi-agent workflows consume more tokens and add latency. CMRO disables implicit skill invocation so ordinary repository tasks keep normal Codex behavior. The user opts in with `$route-codex-work`.

## No root-model override

A top-level project model changes every root prompt, not just routed runs. CMRO leaves the root model unpinned and pins only specialized child roles. This makes installation less surprising and lets teams choose the coordinator per task.

## Three worker tiers

A binary fast/deep split leaves an awkward middle. CMRO separates:

- fast mechanical work;
- balanced everyday implementation; and
- deep high-impact work.

The third route is a risk control, not an invitation to delegate missing authorization.

## Two review depths

Ordinary correctness review benefits from high reasoning, while security, privacy, migrations, and irreversible effects warrant a separate deeper review posture. This concentrates the most expensive reasoning where the impact supports it.

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

The high-level workflow was inspired by Matt Farmer’s public article, credited in [CREDITS.md](../CREDITS.md). CMRO was independently authored with generic risk-role names, public documented model defaults, an explicit-only policy, versioned packets, a third worker tier, cross-platform transactional tooling, and an open evaluation framework.
