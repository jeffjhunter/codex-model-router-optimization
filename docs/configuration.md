# Configuration

## Project config

The supplied `.codex/config.toml` pins the Sol coordinator and contains agent controls:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"

[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

- `max_threads = 4` bounds open child capacity for the intended writer/reviewer workflow.
- `max_depth = 1` lets the root spawn direct children and prevents recursive delegation by those children.
- `interrupt_message = true` preserves model-visible interruption context.

The profile omits `job_max_runtime_seconds` because that setting applies to CSV-spawn jobs rather than ordinary agent turns. CMRO does not advertise a hard timeout.

## Root model is project-wide

The default profile pins the project root to `gpt-5.6-sol` with `xhigh` reasoning. A project-level root model affects ordinary prompts in that repository, not only explicit skill runs. Version 2 intentionally chooses a mechanically verifiable Sol coordinator over an opt-in variation; removing those lines makes the installation incompatible with the stock verifier.

## Custom agents

Each file under `.codex/agents/` contains the required `name`, `description`, and `developer_instructions`, plus an explicit model, reasoning effort, and sandbox default.

| File | Write posture | Intended use |
| --- | --- | --- |
| `luna_worker.toml` | workspace write | Clear, repeatable, mechanically verifiable work |
| `terra_worker.toml` | workspace write | Multi-file, ambiguous, tool-heavy, recovery, and high-impact work |
| `sol_reviewer.toml` | read-only | Independent evidence review, including adversarial concerns when required |

Parent live permission choices can override child sandbox defaults. Reviewer prompts therefore prohibit mutation behaviorally as well as requesting `read-only`.

## Customize model IDs

Model availability varies. To publish a custom fork of this profile:

1. Edit `router/.codex/config.toml` and the agent TOML files under `router/.codex/agents/`.
2. Update every semantic model reference in the installed skill and its protocol/routing references, `router/AGENTS.addendum.md`, `evals/scenarios.jsonl`, documentation, and examples.
3. Update exact mechanical expectations in `routerctl.py`, `scripts/check_repo.py`, and tests; otherwise the fork correctly fails verification.
4. Keep role responsibilities and permission posture intact.
5. Run `python scripts/build_manifest.py` and the complete test suite.
6. Install from that customized checkout.

The target verifier compares installed files with the source checkout. Editing only the installed target is treated as drift, which protects against unnoticed prompt changes.

## Existing config merge

The installer accepts an existing config when the Sol root model, reasoning effort, and required `[agents]` values are already active. Otherwise, it stages an example and exits `2`. It never attempts a lossy parse-and-rewrite of the user’s TOML.

If the existing config already has `[agents]`, merge keys inside that table. TOML does not permit duplicate tables.

## Skill invocation policy

`router/.agents/skills/route-codex-work/agents/openai.yaml` sets:

```yaml
policy:
  allow_implicit_invocation: false
```

This prevents ordinary requests from unexpectedly consuming a multi-agent workflow. Invoke `$route-codex-work` explicitly.

## Official references

- [Codex subagents and custom agents](https://developers.openai.com/codex/subagents)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex `AGENTS.md` guidance](https://developers.openai.com/codex/guides/agents-md)
