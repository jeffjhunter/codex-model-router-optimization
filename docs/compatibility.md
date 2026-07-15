# Compatibility

Last reviewed against current Codex guidance and local control-plane preflights: **July 14, 2026**.

## Supported management environment

| Component | Supported |
| --- | --- |
| Python | 3.11 and newer |
| Operating systems | Windows, macOS, Linux |
| Git | Required by default; intentional non-Git targets need `--allow-non-git` |
| Filesystems | Normal local filesystems; link/reparse-point destination components are rejected |

CI runs the dependency-free management tooling on Windows, macOS, and Ubuntu with Python 3.11 and 3.13.

## Preferred Codex app backend

The control-plane backend expects a current Codex app surface that can:

- list saved projects and identify the exact local repository;
- create a task in that project with an explicit model and reasoning effort;
- read task status and results;
- send follow-up instructions to the retained task without changing its model; and
- expose local session logs containing privacy-minimized `session_meta` and `turn_context` records.

Add the target repository as its own saved project before invoking CMRO. If the exact canonical repository path cannot be resolved, the workflow stops before edits.

## Conditional native backend

Project `.codex/config.toml`, `.codex/agents/*.toml`, `.agents/skills/<name>/SKILL.md`, and `agents/openai.yaml` remain supported installation surfaces. Native routing is accepted only when the client has explicit custom-agent/profile/type selection, a no-write first turn, status/read with exact completed turn IDs, retained-agent follow-up, and session observation. A spawn surface with only `task_name`, prompt, and context-fork fields is insufficient because the name labels the task without selecting a model.

Custom-agent authoring and tool schemas can evolve. CMRO inspects current callable capabilities and fails closed when it cannot prove selection.

## Models

The default profile pins root and reviewer roles to `gpt-5.6-sol`, normal work to `gpt-5.6-terra`, and mechanical work to `gpt-5.6-luna`. Availability may vary by plan, workspace policy, region, rollout, and client version. Installer verification proves configuration, not entitlement or runtime selection.

If a model or effort level is unavailable, customize the source payload as described in [configuration](configuration.md), regenerate the manifest, and test a reversible pilot. Do not edit an installed target and ignore verification failure.

## Not supported or guaranteed

- Python 3.10 or older.
- A target directory that is itself a symlink or junction.
- Silent upgrade over modified managed files.
- Automatic discovery of account model entitlements.
- Treating task names, thread titles, prompts, or filenames as model selection.
- Deterministic native state transitions or hard ordinary-turn timeouts.
- Global installation into every repository.

Open a compatibility issue with the OS, filesystem, Python version, Codex version, backend, exact command, and redacted output.
