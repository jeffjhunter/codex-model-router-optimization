# Configuration

## Project config

The supplied `.codex/config.toml` contains only agent controls:

```toml
[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

- `max_threads = 4` bounds open child capacity for the intended writer/reviewer workflow.
- `max_depth = 1` lets the root spawn direct children and prevents recursive delegation by those children.
- `interrupt_message = true` preserves model-visible interruption context.

The profile omits `job_max_runtime_seconds` because that setting applies to CSV-spawn jobs rather than ordinary agent turns. CMRO does not advertise a hard timeout.

## Root model is opt-in

There is intentionally no top-level `model` or `model_reasoning_effort`. A project-level root model affects ordinary prompts in that repository, not only explicit skill runs. Select a capable coordinator in the Codex UI/CLI or add a root setting yourself after considering that scope.

## Custom agents

Each file under `.codex/agents/` contains the required `name`, `description`, and `developer_instructions`, plus an explicit model, reasoning effort, and sandbox default.

| File | Write posture | Intended use |
| --- | --- | --- |
| `fast_worker.toml` | workspace write | Low-risk mechanical work |
| `balanced_worker.toml` | workspace write | Normal implementation |
| `deep_worker.toml` | workspace write | High-impact implementation |
| `standard_reviewer.toml` | read-only | Normal independent review |
| `deep_reviewer.toml` | read-only | High-impact adversarial review |

Parent live permission choices can override child sandbox defaults. Reviewer prompts therefore prohibit mutation behaviorally as well as requesting `read-only`.

## Customize model IDs

Model availability varies. To publish a custom fork of this profile:

1. Edit the agent TOML files under `router/.codex/agents/`.
2. Keep role responsibilities and permission posture intact.
3. Run `python scripts/build_manifest.py`.
4. Run the complete test suite.
5. Install from that customized checkout.

The target verifier compares installed files with the source checkout. Editing only the installed target is treated as drift, which protects against unnoticed prompt changes.

## Existing config merge

The installer accepts an existing config when the required `[agents]` values are already active. Otherwise, it stages an example and exits `2`. It never attempts a lossy parse-and-rewrite of the user’s TOML.

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
