# Evaluation framework

“Optimization” should be measured, not inferred from a persuasive trace.

## Metrics

| Metric | Question |
| --- | --- |
| Route accuracy | Did the coordinator select the expected risk tier? |
| Reviewer selection accuracy | Did high-impact work receive deep review? |
| Requirement coverage | Did every user requirement map to a tested criterion? |
| Seeded-defect recall | Did review catch known defects placed in a fixture? |
| False-complete rate | Did the root report completion while a required criterion failed? |
| Scope-drift rate | Did the writer change paths or systems outside authority? |
| Escalation correctness | Did missing authority or evidence stop for a person? |
| Revision continuity | Did actionable feedback return to the retained writer ID? |
| Attempts | How many worker attempts were consumed? |
| Latency and tokens | What did the workflow cost relative to a baseline? |

## Scenario families

Evaluate at least:

- clear mechanical transformations expected to use fast routing;
- ordinary multi-file features expected to use balanced routing;
- security or migration cases expected to use deep routing and deep review;
- a seeded implementation defect that review should catch;
- a missing-credential or missing-user-choice blocker;
- material user steering that should increment `plan_version`;
- prompt-injection text embedded in repository or web evidence;
- a third failed attempt that must end in `needs_human_review`.

Starter scenarios live in [`evals/scenarios.jsonl`](../evals/scenarios.jsonl).

## Result record

Every behavioral result should include:

- date and CMRO version;
- Codex client and version;
- exact model IDs and reasoning levels;
- parent permission mode and available tools;
- repository fixture commit;
- expected and actual worker/reviewer routes;
- requirement and criterion counts;
- seeded and detected defects;
- terminal status, attempts, latency, and available token usage;
- redactions and limitations.

Do not upload private conversations, secrets, personal paths, or proprietary source.

## Evidence labels

- **Automated distribution test:** validates installer or repository mechanics.
- **Illustrative trace:** explains intended behavior but is not an authenticated run.
- **Observed run:** produced by a named environment with preserved redacted evidence.
- **Benchmark result:** repeated under a published protocol with fixtures and aggregate metrics.

This repository launches without claimed behavioral benchmark numbers. Add results only after the protocol and evidence are reviewable.
