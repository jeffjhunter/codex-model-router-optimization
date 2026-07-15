# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and semantic versioning.

## [Unreleased]

### Changed

- Update project attribution to reflect Matt Farmer’s support for CMRO while preserving its independent authorship and maintenance status.

## [3.0.1] - 2026-07-14

### Added

- Add strict `cmro.worker.v3` and `cmro.review.v3` packet validation against root-owned run, plan, actor, route/model, acceptance, attempt, and allowed-path context.
- Add one bounded, same-task, no-write format-repair contract with exact-turn observation and matching content snapshots.
- Add explicit action-turn and packet-repair accounting, including matching no-write content snapshots, to sanitized final records while preserving legacy protocol-v3 compatibility.
- Add a candid Fieldstead pilot case study covering the observed Sol -> Terra -> Sol topology, real review findings, fail-closed terminal result, outer fixes, and limitations.

### Fixed

- Prevent format-only packet repair turns from consuming the three-attempt implementation budget or requiring their own review snapshot.
- Reject malformed, stale, actor-mismatched, out-of-scope, incomplete, or internally contradictory packets before handoff.

### Changed

- Require worker and reviewer task responses to contain exactly one raw JSON object using literal actor templates.
- Extend `routerctl`, repository checks, release contents, examples, and evaluation scenarios for packet validation and repair accounting.

## [3.0.0] - 2026-07-14

### Fixed

- Prevent route-like `task_name` labels from being mistaken for custom-agent or model selection.
- Add a Codex app control-plane backend that creates model-pinned worker and reviewer tasks in the exact saved local project, authenticates preflight and every later action turn, and reuses retained task IDs for revision.
- Fail closed before artifact edits when neither model-pinned tasks nor a native surface with the complete staged custom-agent contract is available.

### Added

- Add a privacy-minimized, cross-platform session observation script with exact model, effort, and repository-CWD checks.
- Add a privacy-minimized content snapshot for reviewer-time mutation detection, including changes that preserve `git status` categories.
- Add explicit app-task actor contracts, all-action-turn binding, no-write identity preflights, terminal task monitoring, and backend-aware protocol v3 packets.
- Add a final-record validator that requires at least one implementation attempt, complete turn evidence, and matching snapshots for every accepted review.
- Document the saved-project requirement, control-plane evidence, and model-pinned task topology.

## [2.0.0] - 2026-07-14

### Changed

- Restored the product contract to explicit Sol → Luna/Terra → Sol model routing.
- Pin the project root and independent reviewer to `gpt-5.6-sol`, deterministic work to `gpt-5.6-luna`, and everyday implementation to `gpt-5.6-terra`.
- Replace generic fast/balanced/deep role names with `luna_worker`, `terra_worker`, and `sol_reviewer`.
- Add a five-signal Luna/Terra routing score and require independent runtime model observation before a run can be called verified.
- Upgrade handoff packets to protocol v2 with configured-model and model-observation fields.
- Make installer compatibility checks require the Sol root settings and strengthen repository checks for exact role/model pins.

## [1.0.0] - 2026-07-13

### Added

- Explicit-only `$route-codex-work` skill.
- Fast, balanced, and deep worker routes with standard and deep reviewers.
- Versioned plan, worker, review, and final packet contracts.
- Root-owned state, one-writer safety, same-worker revision, and a three-attempt bound.
- Cross-platform, dependency-free Python installer, verifier, doctor, manifest, and safe uninstall commands.
- Exact payload allowlist, SHA-256 validation, Git-root checks, canonical target roots, link/reparse-point destination rejection, staged config merges, transactional writes, and ownership records.
- Windows, macOS, and Linux CI; deterministic release ZIPs; checksums; and build provenance attestations.
- Architecture, configuration, security, troubleshooting, evaluation, contribution, support, and release documentation.

[Unreleased]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/v3.0.1...HEAD
[3.0.1]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/63bfbc8...v3.0.1
[3.0.0]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/71dcead...63bfbc8
[2.0.0]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/v1.0.0...71dcead
[1.0.0]: https://github.com/jeffjhunter/codex-model-router-optimization/releases/tag/v1.0.0
