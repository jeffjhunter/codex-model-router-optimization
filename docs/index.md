# Documentation

CMRO separates user guidance from the compact instructions installed into Codex.

## Use the project

- [Getting started](getting-started.md): install, verify, pilot, upgrade, and uninstall.
- [Configuration](configuration.md): project settings, model-pinned app tasks, role contracts, session observation, and model customization.
- [Troubleshooting](troubleshooting.md): exit codes and common runtime problems.
- [Compatibility](compatibility.md): supported platforms and version expectations.

## Understand the design

- [Architecture](architecture.md): distribution, app-task/native backends, lifecycle, state, and handoffs.
- [Routing policy](routing-policy.md): Sol coordination, Luna/Terra scoring, and Sol review.
- [Security model](security-model.md): trust assumptions and permission boundaries.
- [Limitations](limitations.md): what task orchestration, runtime evidence, and native instructions cannot guarantee.
- [Design rationale](design-rationale.md): why the defaults differ from a simple two-route loop.

## Measure and maintain it

- [Evaluation](evaluation.md): routing and review quality metrics.
- [Releasing](releasing.md): reproducible archives, checksums, tags, and attestations.
- [Examples](../examples/prompts.md): suggested pilots and expected routes.

The installable agent-facing instructions live in [`router/`](../router/). Keep those files concise; user-facing explanation belongs here.
