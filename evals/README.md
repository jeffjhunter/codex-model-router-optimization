# Behavioral evaluations

This directory contains public fixtures and result schemas, not claims of model performance.

`scenarios.jsonl` defines starter routing cases. Each line contains an ID, task summary, expected worker route, expected reviewer route, and expected terminal behavior. Run them only in disposable repositories with explicit permission boundaries.

When publishing results, add a separate dated JSONL file containing environment metadata and observed outcomes described in [the evaluation guide](../docs/evaluation.md). Redact secrets, personal paths, and proprietary content. A result without environment and evidence metadata should be labeled illustrative, not benchmark data.
