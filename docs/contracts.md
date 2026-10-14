# Contract reference

## Evaluation export profile

SpanVerdict reads uncompressed OTLP trace JSONL by default, or one complete OTLP trace JSON document with `--format json`. This is a documented evaluation profile, not a general-purpose OTLP server or full semantic-convention validator.

- Each trace is one independent evaluation run with exactly one parentless root.
- The root records `spanverdict.case_id` and the configured `gen_ai.operation.name`.
- Every non-root parent must exist within the same trace. Cycles, ambiguous roots and children outside the root's start/end interval block evaluation.
- Every span has nonzero hexadecimal trace/span IDs and finite completed nanosecond timestamps. Trace IDs have 32 hex characters; span IDs have 16. Decimal-string and integer timestamps are accepted. End time must be at or after start time. Status code is a numeric OTLP enum: 0 unset, 1 OK, 2 error.
- Repeated deliveries of the same normalized span are deduplicated. Conflicting relevant data for the same trace/span identity blocks evaluation. Deduplication compares the retained measurement projection, not prompt or message contents.
- Any positive `droppedAttributesCount` blocks the profile. Missing parents detect some incomplete exports, but undelivered leaf spans cannot be discovered from recorded data alone.
- Unknown OTLP message fields and unselected attributes are ignored. Metrics and logs exports are rejected. Empty exports and blank JSONL lines are rejected.

Use complete unsampled evaluation traces, one canonical generation span per model request, and a root interval that covers all measured work. Do not mix unrelated production traces into the evaluation file. Distributed clock skew and asynchronous work that outlives its root require corrected instrumentation; this profile deliberately refuses to infer completion.

## Policy

`version`, `name` and `cases` are required. Version is integer 1. `cases` declares the exact expected set, with no duplicates. Safe identifiers contain ASCII letters, digits, `_`, `.`, `:`, `/` or `-`, begin with a letter or digit, and have at most 128 characters. Labels are metadata, not fields for prompts or private customer identifiers.

Unknown policy fields are rejected at every level. At least one metric or behavioral check must exist.

| Field | Meaning |
| --- | --- |
| `min_runs_per_case` | Minimum independent traces per case, default 1, maximum 1000 |
| `root_operation` | Required operation on the evaluation root, defaults to `invoke_agent` |
| `model_operations` | Operations counted as generations, defaults to `chat`, `generate_content`, `text_completion` |
| `limits` | Inclusive upper bounds on each individual run |
| `minimums` | Inclusive lower bounds on each individual run, useful for detecting absent instrumentation |
| `tools.allow` | Allowed executed tool names; omitted means no allow-list check, empty array forbids all recorded tool calls |
| `tools.required` | Minimum successful executions by tool name; requires explicit status OK |
| `tools.max_calls` | Inclusive maximum attempts by tool name, including failed and unset-status calls |
| `order` | Completion-before-start requirements for recorded tool calls |
| `regressions` | Per-case p95 comparison allowances; requires a reviewed baseline when checking a candidate |

Metric keys are `duration_ms`, `input_tokens`, `output_tokens`, `model_calls`, `tool_calls` and `error_spans`. Counter thresholds are nonnegative integers; duration thresholds can be finite nonnegative numbers. Thresholds are bounded at 10^18. A minimum cannot exceed its corresponding limit.

`duration_ms` is the root's wall-clock duration. It is not the sum of overlapping child durations. `error_spans` counts every recorded span with status 2, including recovered errors. Unset status is not an error, but does not satisfy a required successful tool or an ordering prerequisite.

Generation tokens come only from `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` on the selected model operations. Values require OTLP `intValue` and nonnegative int64 range. Missing usage is **unmeasured**, never an inferred zero. Requested usage limits, minimums or regressions fail when any selected generation is missing that direction's count.

No model calls means zero measured generation tokens. Require `minimums.model_calls` when a case must contain generation activity. Unsupported operations such as `embeddings` are excluded by default; add them to `model_operations` and record both token directions, with explicit zero output where appropriate. Usage on an unclassified operation blocks evaluation. Aggregate usage on an agent/root span is rejected rather than counted twice. Nested selected model spans are rejected to avoid client/server double counting.

Executed tools use `gen_ai.operation.name=execute_tool` and `gen_ai.tool.name`. A tool name on an unclassified operation, or an executed tool with no name, blocks evaluation.

## Tool order

```json
{"before": "check_eligibility", "after": "apply_refund", "same_parent": true}
```

For **each** recorded `apply_refund` attempt, at least one `check_eligibility` span must have status OK and end at or before that attempt starts. By default both spans must share the same immediate parent. With `same_parent: false`, a prerequisite anywhere in the same trace can satisfy the rule.

This is not an exact tool sequence: unrelated tools can occur between the pair. The same earlier successful prerequisite may satisfy several later attempts. Absence of the `after` tool does not fail an order rule by itself; add a `tools.required` rule if execution is mandatory. Failed and unset-status prerequisites do not satisfy the rule. Export line order has no effect.

Timing order is a recorded observation. It does not prove data dependency, that a user consented, that an action was authorized, or that a tool caused the intended side effect.

## Baselines and regressions

Every baseline carries the policy SHA-256, measurement version, evidence-projection SHA-256 and per-case run count/p95 metrics. Policy defaults are materialized before hashing, and object keys are sorted. A changed policy requires a newly captured, reviewed baseline. Evidence hashing covers the normalized retained spans, including identities and timing; it excludes arbitrary attributes, prompts, events, links and responses. It is not a signature or raw-file authenticity proof.

Nearest-rank p95 sorts all runs for a case and selects position `ceil(0.95 * run_count)`. A missing measurement makes that metric's p95 unmeasured rather than dropping the run. With small samples, p95 is usually the maximum. This is not a confidence interval or significance test.

```json
"regressions": {
  "input_tokens": {"relative": 0.1, "absolute": 20}
}
```

The accepted upper threshold is `baseline + max(baseline * relative, absolute)`. `relative: 0.1` means 10 percent; `absolute` uses the metric's units. An actual value equal to the threshold passes. Decimal arithmetic computes the allowance comparison. A zero baseline uses the absolute allowance. Case coverage and individual run budgets still apply independently.

Baseline capture checks coverage, declared budgets, minimums and behavioral rules before emitting the artifact. It does not compare to a previous baseline. Reviewing and approving the new measurements belongs to your normal code-review process.

## Resource and output limits

Default export limits: 64 MiB and 100,000 received spans, including repeated deliveries before deduplication. CLI maxima are 256 MiB and 200,000 spans. Policies are limited to 1 MiB, baselines to 8 MiB. Policies allow at most 1000 case/tool identifiers and 100 ordering rules.

Inputs are memory-resident after bounded reads. Graph and classification traversal avoid Python recursion; parsing deeply nested hostile JSON may still be rejected. File limits bound ordinary workloads, not total RAM, CPU time or report size. Apply an outer timeout and memory/disk limits in CI. Files must be immutable while read. No file locks or live ingestion are provided.

Reports preserve case/trace identifiers, tool labels, row-independent rule codes and measured metrics. They omit raw input paths and arbitrary span data. JSON/JUnit/HTML are individually atomic outputs; writing multiple reports is not one filesystem transaction. The Python writer requires protected input paths from its caller. CLI supplies them and checks collisions between reports, symlink destinations and hard-linked input aliases.
