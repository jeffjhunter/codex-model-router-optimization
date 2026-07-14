# Routing policy

Use the lowest route that safely covers the task. Output length is not a risk signal by itself.

## Fast worker

Choose `fast_worker` only when every condition is true:

- the requested outcome and allowed paths are unambiguous;
- changes are reversible and low impact;
- the work is mechanical or narrowly patterned;
- deterministic checks cover the result; and
- failure cannot expose secrets, weaken authorization, corrupt durable data, or trigger external effects.

Examples: rename files from an explicit map, normalize a fixed schema, or make a small documented text replacement.

## Balanced worker

Choose `balanced_worker` for the normal case, including:

- several dependent edits or files;
- repository exploration or tool use;
- implementation choices with tradeoffs;
- integration behavior or regression risk;
- source-backed research and synthesis; or
- uncertainty about whether the fast route is sufficient.

Examples: add a tested feature, repair a moderate bug, or build a multi-source technical report.

## Deep worker

Choose `deep_worker` when any material concern involves:

- authentication, authorization, cryptography, secrets, or privacy;
- destructive or difficult-to-reverse operations;
- schema or data migrations;
- cross-system effects, deployment, billing, or production state;
- adversarial input or prompt-injection exposure;
- broad architectural changes; or
- a balanced worker blocked by reasoning complexity rather than missing user input.

Deep routing does not grant broader authority. It increases analysis depth while preserving the same user-approved boundaries.

## Reviewer selection

Use `standard_reviewer` for fast and balanced work unless the artifact crosses a deep-risk boundary. Use `deep_reviewer` for every deep-worker task and whenever security, privacy, authorization, irreversible effects, or data integrity are material.

## Escalation rules

- Prefer the stronger route when evidence is incomplete.
- Never downgrade after a material risk is discovered without documenting why it no longer applies.
- Missing authority or user input is a blocker, not a reason to select a stronger model.
- A route change creates a controlled writer handoff; it never authorizes concurrent writers.
