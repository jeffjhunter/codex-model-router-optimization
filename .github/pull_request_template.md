## Summary

Describe the outcome and why it is needed.

## Trust-boundary impact

Describe any change to permissions, paths, payload integrity, external data movement, agent authority, model routing, or completion claims. Write “None” when not applicable.

## Validation

- [ ] Regenerated `router/MANIFEST.json` if the payload changed.
- [ ] Ran `python -m unittest discover -s tests -v`.
- [ ] Ran `python scripts/check_repo.py`.
- [ ] Updated documentation and `CHANGELOG.md` when behavior changed.
- [ ] Used only disposable or sanitized fixtures.

List exact commands and results:

```text

```

## Compatibility and rollback

Explain affected platforms/versions and how a user can safely revert.
