# Research and scope

Research checked on 15 October 2026.

## Why this tool

Agent changes affect execution as well as final answers: model calls, token usage, tools, errors and latency. SpanVerdict checks local recorded evidence against reviewed contracts. It does not run agents or judge answer quality.

- [OpenTelemetry OTLP](https://opentelemetry.io/docs/specs/otlp/) specifies lowerCamelCase fields, hexadecimal trace/span IDs, numeric enums and decimal strings for 64-bit integers. This determines the import format.
- [OpenTelemetry file serialization](https://opentelemetry.io/docs/specs/otel/protocol/file-exporter/) permits unordered JSONL batches. Spans must be joined by trace and span IDs rather than line order.
- [Collector file exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/fileexporter) provides a practical uncompressed OTLP JSONL export path. Its traces support is alpha. SpanVerdict is not an OTLP receiver or Collector replacement.
- [GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) have moved to a separate repository. The tool documents the operation and usage attribute subset it reads, rather than claiming full semantic-convention conformance.
- [Langfuse CI experiments](https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd) recommends reviewed baselines and per-case verdicts, because an improving aggregate can hide a newly failing case. SpanVerdict requires complete case coverage and binds baselines to the contract fingerprint.
- [Phoenix evals in CI](https://arize.com/blog/evals-in-ci-how-to-write-llm-evals-as-tests/) integrates richer code and model evaluations with test frameworks. Use Phoenix or Langfuse for answer evaluation, datasets and experiment management. SpanVerdict adds a local dependency-free telemetry contract check.
- [TracePact](https://github.com/dcdeve/tracepact) already provides agent behavior contracts and cassette replay. SpanVerdict does not reproduce its replay engine. Its scope is OTLP graph integrity, measured run budgets and per-case telemetry regressions.

## Design decisions

Input is a complete, unsampled evaluation export. Each trace has one root with a stable `spanverdict.case_id`; repeated runs share that case ID. Policies declare the exact expected cases. Missing parents, ambiguous roots, malformed spans and missing requested measurements block evaluation instead of silently reducing the denominator.

Timing order checks use completed successful prerequisite tools. They are observations in recorded clocks, not a runtime permission boundary, proof of human consent or proof that the action had the intended effect.

Regression checks compare per-case nearest-rank p95 metrics against a reviewed baseline with relative and absolute allowance. This is an operational threshold, not a statistical significance test. There is no model-price table: token counts are measured usage, not an invoice or inferred currency cost.

No claim of novelty, broad framework compatibility or production certification is made. The integration example will use the actual OpenTelemetry Python SDK and OTLP encoder with synthetic agent operations.
