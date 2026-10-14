# Changelog

## 0.1.0

Initial public prerelease:

- Bounded OTLP JSON/JSONL imports with hexadecimal identity handling and repeated-delivery deduplication.
- Complete root/parent reconstruction, cycle checks and evaluation case coverage.
- Inclusive per-run budgets/minimums, explicit token coverage and nested-generation rejection.
- Executed tool allow lists, attempt limits, successful execution requirements and completion-before-start rules.
- Reviewed per-case p95 baselines tied to contract and measurement fingerprints.
- Dependency-free CLI and Python API, plus a package-free composite GitHub Action.
- Private atomic JSON/JUnit/offline HTML report writes with protected input destinations.
- Synthetic refund-agent examples and real OpenTelemetry Python SDK/OTLP encoder integration.
- Cross-platform unit CI, installed-wheel checks and actual Action acceptance/rejection verification.

The tool checks recorded telemetry. It does not run agents, judge answer quality or enforce runtime permissions. See the contract reference and security policy for the supported profile and limits.
