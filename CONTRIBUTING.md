# Contributing

Thank you for improving CMRO. Contributions should make the workflow safer, clearer, more portable, or more measurable.

## Before opening a change

1. Search existing issues.
2. For behavioral changes, describe the failure mode and a concrete scenario.
3. Keep model availability claims sourced and date-stamped.
4. Do not include secrets, private repository content, production traces, or copyrighted third-party packages.

## Local checks

Use Python 3.11 or newer:

```bash
python scripts/build_manifest.py
python -m compileall -q routerctl.py scripts tests
python -m unittest discover -s tests -v
python scripts/check_repo.py
```

If you changed the routed payload, commit the regenerated `router/MANIFEST.json`. Test installation only against a disposable Git repository.

## Pull requests

- Keep the change focused.
- Explain user impact and trust-boundary changes.
- Add or update tests for installer and protocol changes.
- Update documentation and `CHANGELOG.md` when behavior changes.
- Report the exact validation commands and results.

Behavioral evaluation data is welcome when it includes the Codex version, model IDs, reasoning levels, permission mode, date, task fixture, expected route, actual route, terminal state, and limitations. Do not present illustrative traces as authenticated results.

By contributing, you agree that your contribution is licensed under the repository’s MIT License.
