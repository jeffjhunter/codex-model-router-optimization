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
- rejects destination paths that cross links or escape the root;
- preflights managed-file conflicts before writing;
- stages an incompatible config instead of rewriting it;
- marks its `AGENTS.md` block for exact verification and removal;
- stages writes and restores backups if a batch commit fails;
- records file ownership; and
- preserves changed or pre-existing files during uninstall.

SHA-256 detects corruption and supports release verification; it does not authenticate an untrusted repository by itself. Prefer a tagged GitHub release, verify `SHA256SUMS`, and inspect the GitHub build-provenance attestation.

## Runtime boundaries

### Permissions inherit from the parent

Codex subagents inherit parent tools and live permission choices. A reviewer file requests `sandbox_mode = "read-only"`, but parent runtime overrides can supersede that default. The reviewer prompt also forbids file and external mutations; this is defense in depth, not an unbreakable sandbox.

Choose the least permissive parent mode compatible with the task. High reasoning effort never grants additional authority.

### One writer is a coordination rule

CMRO permits one write-capable worker at a time to avoid races in a shared working tree. This rule does not lock the filesystem against other processes, users, hooks, or background tools. Review current diffs and repository status at the final gate.

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
