# Codex Model Router Optimization

[![CI](https://github.com/jeffjhunter/codex-model-router-optimization/actions/workflows/ci.yml/badge.svg)](https://github.com/jeffjhunter/codex-model-router-optimization/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/jeffjhunter/codex-model-router-optimization)](https://github.com/jeffjhunter/codex-model-router-optimization/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)

Risk-aware coordinator–worker–reviewer orchestration for Codex.

Codex Model Router Optimization (CMRO) is a repo-scoped Codex skill and custom-agent profile. It routes explicit workflow runs to a fast, balanced, or deep worker, requires independent evidence review, returns actionable feedback to the retained writer, and stops after a bounded number of attempts. It is **not** an API gateway, network proxy, deterministic scheduler, or official OpenAI project.

> [!IMPORTANT]
> This is an independent community project. It is not affiliated with or endorsed by OpenAI or Matt Farmer. Native skill instructions guide agent behavior but do not create a guaranteed state machine or hard security boundary.

## Why this exists

Large coding tasks fail in predictable ways: the plan stays vague, the implementer judges its own work, multiple writers collide, or confidence gets reported as proof. CMRO turns those failure modes into an explicit operating protocol:

- requirement IDs and atomic acceptance criteria before delegation;
- one writer selected by impact and verifiability;
- a separate reviewer checking the real artifact;
- same-worker revision to preserve task context;
- three total worker attempts, followed by human escalation;
- a root-thread final gate before completion.

```mermaid
flowchart LR
    U["User request"] --> C["Root coordinator"]
    C -->|"low risk + deterministic"| F["Fast worker"]
    C -->|"normal implementation"| B["Balanced worker"]
    C -->|"high-impact work"| D["Deep worker"]
    F --> R["Independent reviewer"]
    B --> R
    D --> DR["Deep reviewer"]
    R -->|"revise"| S["Same worker ID"]
    DR -->|"revise"| S
    S --> R
    R -->|"accept"| G["Root final gate"]
    DR -->|"accept"| G
    R -->|"blocked / attempt limit"| H["Human review"]
    DR -->|"blocked / attempt limit"| H
```

## Routes

| Route | Default model | Effort | Use it for |
| --- | --- | --- | --- |
| `fast_worker` | `gpt-5.6-terra` | low | Clear, reversible transformations with deterministic checks |
| `balanced_worker` | `gpt-5.6` | medium | Ordinary implementation, tool use, multi-file work, regression risk |
| `deep_worker` | `gpt-5.6` | high | Security, privacy, migrations, destructive effects, complex architecture |
| `standard_reviewer` | `gpt-5.6` | high | Independent correctness, scope, and regression review |
| `deep_reviewer` | `gpt-5.6` | xhigh | Adversarial review of high-impact work |

Model access varies by account and rollout. Confirm these IDs in your Codex model picker before a serious run. The project intentionally does **not** pin the root model, so installation does not change the model used by every ordinary prompt in the repository.

## Five-minute start

Prerequisites: Python 3.11+, Git, a backed-up or committed target repository, and a current Codex client with custom-agent support.

```bash
git clone https://github.com/jeffjhunter/codex-model-router-optimization.git
cd codex-model-router-optimization

python routerctl.py doctor --target /path/to/your/repository
python routerctl.py install --target /path/to/your/repository --dry-run
python routerctl.py install --target /path/to/your/repository
python routerctl.py verify --target /path/to/your/repository
```

On Windows, quote paths containing spaces:

```powershell
python .\routerctl.py install --target "C:\path\to\your repository" --dry-run
```

Exit code `0` means the requested operation completed. Exit code `2` means a safe manual step remains—usually merging the staged `.codex/config.codex-model-router.example.toml` into an existing config. Exit code `3` means a conflict stopped installation before managed files were overwritten.

Start a new Codex task in the target repository and invoke the workflow explicitly:

```text
$route-codex-work Add a tested CSV export to the activity page. Preserve existing API behavior, keep changes local to this repository, and show the verification evidence.
```

The skill is explicit-only by design. Ordinary Codex tasks do not automatically enter the routed loop.

## Safe operations

```bash
# Machine-readable verification
python routerctl.py verify --target /path/to/repo --json

# Inspect the exact allowlisted payload and hashes
python routerctl.py manifest

# Preview removal, then remove only unchanged installer-owned files
python routerctl.py uninstall --target /path/to/repo --dry-run
python routerctl.py uninstall --target /path/to/repo
```

The installer rejects unexpected payload files, verifies SHA-256 hashes, refuses symlink/reparse-point destinations, avoids overwriting changed managed files, respects root `AGENTS.override.md` precedence, stages incompatible TOML for manual merge, and records ownership for conservative uninstall behavior. Files edited after installation are preserved rather than deleted.

## What is and is not verified

The test suite verifies payload integrity, TOML parsing, installation conflicts, Git-root checks, idempotence, config staging, `AGENTS.md` merging, tamper detection, uninstall ownership, paths with spaces, and portable release archives across Windows, macOS, and Linux.

It does not prove that a native Codex run will follow every transition, that a configured model is entitled for your account, or that a reviewer sandbox cannot be overridden by the parent runtime. See [limitations](docs/limitations.md) and the [security model](docs/security-model.md).

## Documentation

- [Getting started](docs/getting-started.md)
- [Architecture and lifecycle](docs/architecture.md)
- [Routing policy](docs/routing-policy.md)
- [Configuration and model customization](docs/configuration.md)
- [Security and trust boundaries](docs/security-model.md)
- [Evaluation framework](docs/evaluation.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Design rationale](docs/design-rationale.md)
- [Examples](examples/prompts.md)

## Credits

The practical coordinator–worker–reviewer pattern was inspired by Matt Farmer’s article, [“Codex Model Routing: Build a Sol–Terra Review Loop”](https://mattfarmer.ai/codex-model-routing). This repository is an independently written implementation with different tooling, role names, defaults, contracts, and safety design. Read [CREDITS.md](CREDITS.md) for the full attribution.

## Contributing

Bug reports, routing scenarios, documentation improvements, and reproducible evaluation results are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), the [support policy](SUPPORT.md), and the [code of conduct](CODE_OF_CONDUCT.md).

Released under the [MIT License](LICENSE).
