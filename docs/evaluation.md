# Evaluation framework

“Optimization” and “verified routing” must be measured, not inferred from a persuasive trace.

## Metrics

| Metric | Question |
| --- | --- |
| Route accuracy | Did Sol select Luna or Terra using the published score? |
| Backend validity | Did the control plane explicitly select a model/profile rather than label a task? |
| Model identity | Does exact-turn session evidence cover every material Sol → Luna/Terra → Sol turn? |
| Reviewer coverage | Did high-impact work receive adversarial Sol review? |
| Requirement coverage | Did every user requirement map to a tested criterion? |
| Seeded-defect recall | Did review catch known fixture defects? |
| False-complete rate | Did root complete while a criterion or identity gate failed? |
| Scope drift | Did any actor change paths or systems outside authority? |
| Packet validity | Did raw worker/reviewer output match authoritative run, actor, route, acceptance, attempt, and path context? |
| Repair rate | How often was one no-write format repair needed, and did repair snapshots match? |
| Revision continuity | Did feedback return to the retained writer task ID? |
| Reviewer mutation | Did the root-owned content digest change during read-only review? |
| Attempts, latency, tokens | What did the workflow consume relative to a baseline? |

## Scenario families

Evaluate at least:

- a mechanical Luna task;
- an ordinary multi-file Terra feature;
- a high-impact Terra task with adversarial Sol review;
- a seeded defect the reviewer should catch;
- a missing credential or user choice;
- material steering that increments `plan_version`;
- prompt-injection text in repository or web evidence;
- a third failed attempt;
- a native spawn surface with no profile selector and one with the full staged contract;
- an exact saved-project path mismatch;
- an unavailable model or session metadata mismatch during preflight or a later action turn;
- a stopped task or missing/truncated packet;
- a malformed but useful packet repaired once without consuming an attempt;
- a second-invalid, mutating, orphaned, or duplicate repair that must fail closed;
- a same-ID revision with no model override; and
- reviewer-time mutation that leaves `git status` categories unchanged.

Starter descriptors live in [`evals/scenarios.jsonl`](../evals/scenarios.jsonl). Public CI validates descriptors and deterministic fixtures; signed-in desktop canaries remain separate observed runs.

## Result record

Every behavioral result should include:

- date, CMRO version, Codex client, and host;
- baseline fixture commit and exact saved-project identity;
- backend and callable capability evidence;
- actor-contract hash;
- task creation receipts with requested model/effort;
- independently observed task ID, every material completed turn ID, model, effort, and CWD for every role;
- requirement and criterion counts;
- expected and actual routes;
- seeded and detected defects;
- task terminal states, retained IDs, attempts, latency, and available token usage;
- action-turn IDs, packet-repair-turn IDs, validator results, and repair reasons;
- pre/post-review worktree snapshot digests and declared scope;
- redactions and limitations.

Do not upload private conversations, secrets, personal paths, proprietary source, or raw session logs.

Validate each sanitized handoff with `python routerctl.py validate-packet --packet worker.json --context context.json`, then validate the sanitized final record with `python routerctl.py validate-run --record cmro-final.json`. These commands check protocol-v3 invariants; they do not authenticate the underlying session log or reconstruct omitted evidence.

## Evidence labels

- **Automated distribution test:** installer, manifest, parser, or repository mechanics.
- **Control-plane preflight:** model-pinned task creation plus task/turn-bound session observation, without a complete build/review cycle.
- **Illustrative trace:** intended behavior, not an authenticated run.
- **Observed run:** a named-environment lifecycle with sanitized identity, handoff, review, and terminal evidence; the terminal state may honestly be `needs_human_review`.
- **Benchmark result:** repeated observed runs under a published fixture/protocol with aggregate metrics.

Do not market a control-plane preflight as an observed end-to-end run. Publish topology and routing claims only after the writer produced artifacts, a separate reviewer inspected them, exact-turn evidence and snapshots reconcile, and the sanitized terminal record is reviewable. Claim product completion only when the root gate passed; preserve `needs_human_review` when it did not.
