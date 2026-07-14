# Releasing

Only maintainers should publish releases.

## Prepare

1. Confirm the worktree is clean and on the default branch.
2. Update `VERSION`, `CHANGELOG.md`, and `CITATION.cff`.
3. If the payload changed, run `python scripts/build_manifest.py`.
4. Run:

   ```bash
   python -m compileall -q routerctl.py scripts tests
   python -m unittest discover -s tests -v
   python scripts/check_repo.py
   ```

5. Review provenance, third-party rights, model compatibility, and security-impacting changes.

## Build locally

After all release files are committed:

```bash
python scripts/build_release.py
```

The builder uses tracked files, a single versioned top-level directory, forward-slash ZIP entries, fixed timestamps, deterministic ordering, and normalized permissions. It writes the archive and `dist/SHA256SUMS`.

Extract the archive into a disposable directory, run repository checks from the extraction, install into a disposable Git repository, verify, and uninstall.

## Tag and publish

Create an annotated `vMAJOR.MINOR.PATCH` tag that matches `VERSION` and push it. The release workflow:

- requires the tagged commit to be on `main` and the tag to be annotated;
- reruns repository checks and tests on Windows, macOS, and Linux with Python 3.11 and 3.13;
- builds the deterministic ZIP in a read-only job;
- round-trips the extracted archive on all three operating systems;
- creates a GitHub build-provenance attestation;
- publishes the ZIP and `SHA256SUMS`; and
- generates release notes from the tag.

The final attestation/publish job uses the protected `release` environment and does not check out or execute repository code. Configure that environment with a required maintainer review before publishing tags.

Verify the public release is marked non-draft, its tag matches the commit, assets download correctly, checksums match, and provenance is visible.

## Rollback

Do not silently replace a published asset. If a release is broken or compromised, mark it clearly, publish a fixed patch version, and document the impact and remediation. Preserve the audit trail.
