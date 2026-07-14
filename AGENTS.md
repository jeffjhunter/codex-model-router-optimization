# Repository instructions

## Scope

This repository distributes a Codex routing profile and a dependency-free Python management CLI. The installable payload lives under `router/`; it is not active merely because this development repository is open.

## Required checks

- After changing anything under `router/`, run `python scripts/build_manifest.py`.
- Run `python -m unittest discover -s tests -v` after code, payload, or installer changes.
- Run `python scripts/check_repo.py` before completion.
- Keep release archives portable: forward-slash entries, one top-level directory, dot-directories preserved, and deterministic timestamps.

## Safety

- Test install and uninstall behavior only in disposable repositories.
- Never weaken conflict, containment, allowlist, hash, ownership, or link/reparse-point checks without a documented security rationale and regression coverage.
- Do not add real secrets, private repository content, authenticated traces, or third-party packages without an explicit compatible license.
- Keep native orchestration claims bounded: skills guide behavior but do not guarantee a deterministic state machine, hard timeout, or unoverrideable sandbox.
