# Routing policy

Use the least expensive model that safely covers the task. Output length is not a risk signal by itself. CMRO has two write routes—Luna and Terra—and one independent Sol review route. The root coordinator is Sol.

## Luna worker

Choose `luna_worker` only when every condition is true:

- the requested outcome and allowed paths are unambiguous;
- changes are reversible and low impact;
- the work is mechanical or narrowly patterned;
- deterministic checks cover the result; and
- failure cannot expose secrets, weaken authorization, corrupt durable data, or trigger external effects.

Examples: rename files from an explicit map, normalize a fixed schema, or make a small documented text replacement.

## Terra worker

Choose `terra_worker` for the normal case, including:

- several dependent edits or files;
- repository exploration or tool use;
- implementation choices with tradeoffs;
- integration behavior or regression risk;
- source-backed research and synthesis; or
- uncertainty about whether the fast route is sufficient.

Examples: add a tested feature, repair a moderate bug, or build a multi-source technical report.

Also choose `terra_worker` when a material concern involves authentication, authorization, privacy, destructive operations, migrations, production state, or adversarial input. Those concerns require explicit threat, authority, rollback, and evidence checks; they do not invent a third write model or expand permissions.

## Reviewer selection

Use a separate `sol_reviewer` for every run. The reviewer is always configured as `gpt-5.6-sol` with `xhigh` reasoning and read-only behavior. High-impact work adds adversarial review concerns to the same Sol reviewer contract.

## Routing score

Give one point for each: material ambiguity; several dependent files or steps; tool use or environment inspection; recovery from partial failure; judgment-heavy synthesis or regression risk. Route 0–1 to Luna and 2–5 to Terra. When evidence is incomplete, use Terra.

## Model identity gate

Configuration is not runtime proof. Before delegation, the root records the expected model for each role. Before final acceptance, it must record independent session or UI evidence that the root/reviewer ran as Sol and the writer ran as the selected Luna or Terra route. If the current client does not expose that evidence, set model observation to `not_verified` and return `needs_human_review`; never relabel a generic subagent as a model-specific route.

## Escalation rules

- Prefer Terra when evidence is incomplete.
- Never downgrade from Terra to Luna after material ambiguity or risk is discovered without documenting why it no longer applies.
- Missing authority or user input is a blocker, not a reason to select a stronger model.
- A route change creates a controlled writer handoff; it never authorizes concurrent writers.
