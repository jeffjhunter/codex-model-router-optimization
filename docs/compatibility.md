# Compatibility

Last reviewed against current public Codex guidance: **July 13, 2026**.

## Supported management environment

| Component | Supported |
| --- | --- |
| Python | 3.11 and newer |
| Operating systems | Windows, macOS, Linux |
| Git | Required by default; intentional non-Git targets need `--allow-non-git` |
| Filesystems | Normal local filesystems; link/reparse-point destination components are rejected |

CI runs the dependency-free management tooling on Windows, macOS, and Ubuntu with Python 3.11 and 3.13.

## Codex expectations

The installed profile expects a current Codex surface that supports:

- project `.codex/config.toml`;
- project `.codex/agents/*.toml` custom agents;
- repository `.agents/skills/<name>/SKILL.md` skills;
- optional `agents/openai.yaml` skill metadata; and
- direct subagent spawning, steering, and inspection.

Custom-agent authoring is documented as evolving. Review release notes before deploying CMRO broadly.

## Models

The default profile pins root and reviewer roles to `gpt-5.6-sol`, normal work to `gpt-5.6-terra`, and mechanical work to `gpt-5.6-luna`. Availability may vary by plan, workspace policy, region, rollout, and client version. Installer verification proves configuration, not entitlement or runtime selection.

If a model or effort level is unavailable, customize the payload as described in [configuration](configuration.md), regenerate the manifest, and test a reversible pilot. Do not simply edit an installed target and then ignore verification failure.

## Not supported or guaranteed

- Python 3.10 or older.
- Using a symlink or junction as the target directory itself. Ancestor aliases are resolved once to a canonical root before containment checks.
- Silent upgrade over modified managed files.
- Automatic discovery of account model entitlements.
- Deterministic native state transitions.
- Global installation into every repository.

Open a compatibility issue with the OS, filesystem, Python version, Codex version, exact command, and redacted output.
