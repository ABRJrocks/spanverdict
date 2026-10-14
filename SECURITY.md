# Security and support

## Vulnerability reporting

Use GitHub private vulnerability reporting for this repository. Include the affected version, a synthetic reproduction and expected impact. Do not post prompts, API keys, customer data or private trace exports in public issues.

## Trust boundary

SpanVerdict is a local recorded-evidence checker. It does not execute tools, run a model, repair traces, approve deployments, establish user consent or enforce runtime authorization. Its checks are only as complete and accurate as the supplied telemetry. An unrecorded operation or forged status can evade observed-behavior checks.

Policy and baseline artifacts must be reviewed in version control. Fingerprints detect a mismatch with the contract; they do not authenticate a producer or prove human review. A candidate must not automatically approve its own baseline. Root timing and immediate-parent matching are observation rules, not causal proofs.

## Data handling and resources

The core package and composite Action make no validation network requests. Installing the Python package can contact a configured package index for build tooling. The optional SDK integration dependencies are separate from the core runtime.

Inputs can contain prompts, responses and personal information even when the reports omit them. Limit access to raw exports. JSON/JUnit/HTML reports keep case/trace IDs, tool labels, counts, token usage and latency. Do not use private customer identifiers as case IDs or put secrets in tool labels. Review artifact visibility before sharing reports.

Bounded reads and span counts limit ordinary input size. Apply an external execution timeout and memory/disk quotas to untrusted exports. Python JSON decoding creates objects in memory and has no process-level memory sandbox. Files must be immutable during checking. Output protections do not defend against an adversarial concurrent filesystem writer or replace operating-system access controls.

Reports use a private temporary file and atomic replacement per destination; exclusive baseline creation refuses an existing destination. Temporary files are removed after ordinary handled failures. Abrupt termination can leave a temporary artifact. This is not secure erasure or encryption. Windows ACLs and filesystem capabilities depend on the caller's environment.

## Support

The 0.1.x line is an early public release. The executable integration verifies the documented OTLP profile using OpenTelemetry Python SDK 1.45.1 and synthetic operations. Collector configuration is a recipe, and real production agent integrations are not certified. No SLA, formal audit or production-readiness guarantee is offered.

For ordinary bugs, use [GitHub Issues](https://github.com/ABRJrocks/spanverdict/issues) with synthetic data. For instrumentation/profile questions, include relevant attribute names and expected behavior without private content.
