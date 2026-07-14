# Security policy

## Supported versions

Security fixes are provided for the latest released major version.

## Report a vulnerability

Please use GitHub’s private vulnerability reporting for this repository. Do not open a public issue containing exploit details, secrets, private paths, or sensitive logs.

Include:

- affected version and operating system;
- the command or workflow involved;
- a minimal reproduction using disposable data;
- impact and required preconditions; and
- any safe mitigation already known.

## Scope

Relevant issues include payload tampering, path traversal, symlink or junction escapes, unsafe overwrite or removal, instruction-injection weaknesses, permission-boundary confusion, secret exposure in evidence packets, and false verification results.

Model quality disagreements without a reproducible safety or integrity impact belong in a normal issue. OpenAI account, product, entitlement, or platform vulnerabilities should be reported through OpenAI’s own security channels.

See [docs/security-model.md](docs/security-model.md) for the project’s explicit trust boundaries.
