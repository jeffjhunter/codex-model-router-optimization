# Configuration

## Project config

The supplied `.codex/config.toml` pins the Sol coordinator and bounds native-agent behavior:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"

[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

The root pin applies to ordinary prompts in the repository, not only explicit skill runs. `max_threads` and `max_depth` constrain the conditional native backend. CMRO omits `job_max_runtime_seconds` because it is not a hard timeout for ordinary turns.

## Model-pinned app tasks

The preferred backend does not rely on inherited child-model behavior. For each role, the root creates a user-owned task in the exact saved local project with explicit model and reasoning parameters:

| Role | Model | Effort | First turn |
| --- | --- | --- | --- |
| Luna writer | `gpt-5.6-luna` | medium | No-write identity preflight |
| Terra writer | `gpt-5.6-terra` | high | No-write identity preflight |
| Sol reviewer | `gpt-5.6-sol` | xhigh | Read-only identity preflight |

After independent verification, the root sends the real packet to the retained task ID without a model override. Revisions return to that same writer ID.

## Custom-agent role files

Each file under `.codex/agents/` contains the required `name`, `description`, and `developer_instructions`, plus an explicit model, effort, and sandbox default.

| File | Write posture | Intended use |
| --- | --- | --- |
| `luna_worker.toml` | workspace write | Behavior contract and selectable Luna profile |
| `terra_worker.toml` | workspace write | Behavior contract and selectable Terra profile |
| `sol_reviewer.toml` | read-only | Behavior contract and selectable Sol reviewer profile |

App tasks are told to follow the corresponding behavior contract after their model identity passes. Native clients may load the files as profiles only when they expose the complete staged native contract, not merely a profile/type selector. Parent permission choices can override sandbox defaults, so reviewer behavior and root-owned pre/post-review content snapshots are checked separately.

## Runtime observation

The installed skill includes `scripts/observe_session.py`. It reads only `session_meta` and `turn_context` JSONL records, emits no prompts or tool content, and supports exact expectations:

```bash
python .agents/skills/route-codex-work/scripts/observe_session.py \
  --thread-id TASK_ID \
  --expect-model gpt-5.6-terra \
  --expect-effort high \
  --expect-cwd /absolute/path/to/repository \
  --wait-seconds 30
```

Exit code `0` means verified and matched, `2` means invalid input or evidence unavailable/not ready, and `3` means observed metadata mismatched an expectation. Local session-log layout is a compatibility surface; a parser failure stops routing rather than weakening the gate.

## Customize model IDs

To publish a custom fork:

1. Edit `router/.codex/config.toml` and the role TOML files.
2. Update semantic model references in the skill, references, addendum, evals, docs, and examples.
3. Update exact expectations in `routerctl.py`, `scripts/check_repo.py`, and tests.
4. Keep role responsibilities, no-write preflights, and permission posture intact.
5. Run `python scripts/build_manifest.py` and the complete suite.
6. Install from the customized checkout and run an authenticated reversible pilot.

Editing only the installed target is treated as drift.

## Existing config merge

The installer accepts an existing config when the Sol root model, effort, and required `[agents]` values are already active. Otherwise it stages `.codex/config.codex-model-router.example.toml` and exits `2`. Merge keys into the existing table; TOML does not permit duplicate `[agents]` tables.

## Skill invocation policy

`agents/openai.yaml` sets `allow_implicit_invocation: false`. Invoke `$route-codex-work` explicitly; this also makes the creation of its worker and reviewer tasks an explicit part of the requested workflow.
