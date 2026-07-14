# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and semantic versioning.

## [Unreleased]

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

[Unreleased]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/jeffjhunter/codex-model-router-optimization/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/jeffjhunter/codex-model-router-optimization/releases/tag/v1.0.0
