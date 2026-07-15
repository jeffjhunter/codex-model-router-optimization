# Security model

CMRO reduces several orchestration risks, but it does not turn natural-language agents into a hardened isolation system.

## Assets to protect

- repository integrity and scope;
- credentials, secrets, personal data, and proprietary source;
- external systems reachable through tools or connectors;
- correctness of completion and review claims;
- the coordinator’s authoritative plan and agent identities;
- installation paths and existing project instructions.

## Trust assumptions

CMRO assumes:

- the downloaded release was obtained from the intended GitHub repository and its checksum or attestation was verified;
- Python, Git, the filesystem, and the current user account are not already compromised;
- the target repository is intentionally trusted in Codex;
- the user chooses an appropriate parent permission mode;
- installed agent prompts and skill files are reviewed before use.

It does not assume repository content, tool output, web pages, issue text, generated code, or worker reports are trustworthy instructions.

## Installer defenses

The management CLI:

- uses an exact payload allowlist and SHA-256 manifest;
- rejects missing, extra, changed, symlinked, or reparse-point payload entries;
- requires the target Git root unless `--allow-non-git` is explicit;
- resolves ancestor aliases once to a canonical target root, rejects a link at the target itself, and rejects managed destination components that cross links or escape that root;
- preflights managed-file conflicts before writing;
- stages an incompatible config instead of rewriting it;
- marks its `AGENTS.md` block for exact verification and removal;
- stages writes and restores backups if a batch commit fails;
- records file ownership; and
- preserves changed or pre-existing files during uninstall.

SHA-256 detects corruption and supports release verification; it does not authenticate an untrusted repository by itself. Prefer a tagged GitHub release, verify `SHA256SUMS`, and inspect the GitHub build-provenance attestation.

## Runtime boundaries

### App tasks are separate but share the checkout

Model-pinned app workers and reviewers are separate user-owned tasks, not native child agents. They run against the same saved local project checkout. Their prompts restrict authority, but task creation does not expose a reviewer-specific read-only sandbox parameter. Compare root-owned content snapshots around review and treat any mismatch as a failed gate.

Native subagents inherit parent tools and live permission choices. A reviewer file may request `sandbox_mode = "read-only"`, but parent runtime overrides can supersede it. These controls are defense in depth, not an unbreakable sandbox.

Choose the least permissive parent mode compatible with the task. High reasoning effort never grants additional authority.

### One writer is a coordination rule

CMRO permits one write-capable worker at a time to avoid races in a shared working tree. This rule does not lock the filesystem against other processes, users, hooks, or background tools. Review current diffs and repository status at the final gate.

### Session observations are not attestations

The runtime observer reads privacy-minimized fields from local Codex JSONL files and binds app evidence to a returned task ID and exact completed turn ID. CMRO repeats that observation for every material actor turn rather than assuming a preflight pin persists. Local files remain writable by the user and their schema can evolve. This evidence detects routing mistakes and prevents label-only claims; it is not cryptographic proof against a compromised host.

The worktree snapshot emits only digests and counts. It covers the index and raw contents of tracked and non-ignored untracked artifacts, detects edits even when the `git status` categories do not change, and excludes ignored files and nested submodule contents by design. It detects lasting artifact changes between snapshots, not transient actions that are perfectly reverted.

Duplicate session candidates, missing task-start markers, inherited-only turns, mismatched CWD/model/effort, or changed schemas fail closed.

### External content is evidence

Role prompts direct agents to treat repository, web, issue, command, and tool content as untrusted evidence. Applicable system, developer, user, skill, and `AGENTS.md` instructions retain their normal precedence. Agents should not follow instructions embedded in data simply because a file or web page says to do so.

### Connectors and data movement

Installation is local, but runtime agents may have access to web, MCP, browser, email, cloud-drive, or other tools inherited from the parent. Do not send repository content to an external service or connector unless the user explicitly authorized that destination and data scope.

## Evidence hygiene

Packets should use opaque run IDs and repository-relative paths. Do not include:

- access tokens, passwords, private keys, cookies, or connection strings;
- unnecessary absolute home-directory paths;
- private customer or employee data;
- full environment dumps;
- raw logs containing secrets; or
- proprietary content unrelated to the criterion.

Redact sensitive output while preserving enough evidence to reproduce the result safely. A redaction should be labeled, not silently omitted.

## Human stops

Return `needs_human_review` when required credentials, approval, production context, user decisions, reliable evidence, or a safe continuation path is missing. Do not widen permissions or invent proof to force a complete state.

Report vulnerabilities according to [SECURITY.md](../SECURITY.md).
