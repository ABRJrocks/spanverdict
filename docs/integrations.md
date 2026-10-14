# Integration recipes

## CLI release check

Requires Python 3.10+. Install the wheel or repository into your own virtual environment. The core package has no runtime dependencies.

```sh
spanverdict lint contracts/agent.json
spanverdict check contracts/agent.json artifacts/candidate.jsonl \
  --baseline contracts/approved-baseline.json \
  --json-report reports/verdict.json --junit reports/verdict.xml \
  --html-report reports/verdict.html
```

Exit 0 means the recorded runs meet the contract. Exit 1 means recorded behavior violates it. Exit 2 means invalid input, missing baseline, incomplete trace graph or I/O/configuration failure. Argparse also returns 2 for invalid command arguments.

Use a fresh report directory for each CI run. An input/configuration failure does not produce a new report and does not delete an old one. Normal contract violations still produce reports. Never treat the existence of an artifact as a passing verdict.

## GitHub Actions

```yaml
name: Agent execution contract
on: [push, pull_request]
permissions:
  contents: read
jobs:
  contract:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1
        with:
          python-version: '3.12'
      - run: python scripts/run_agent_evaluations.py
      - uses: ABRJrocks/spanverdict@v0.1.0
        with:
          policy: contracts/agent.json
          traces: artifacts/candidate.jsonl
          baseline: contracts/approved-baseline.json
          report-prefix: reports/agent
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        if: always()
        with:
          name: agent-contract
          path: reports/
```

The evaluation script is your application-specific producer. SpanVerdict does not run the agent. Pin a reviewed release commit SHA instead of a tag for reproducible workflows.

Inputs: `policy` and `traces` are required. `baseline` is optional unless the policy declares regressions. `format` defaults to `jsonl` and can be `json`. `report-prefix` defaults to `reports/spanverdict`.

The composite Action uses the selected Python interpreter and temporarily sets PYTHONPATH for its own step. It installs no packages, requires no API token, uploads no artifacts itself and makes no validation network calls. Python 3.10+ must be on PATH. Artifact publication is controlled by your workflow.

## Capture an approved baseline

```sh
spanverdict baseline contracts/agent.json artifacts/reviewed-run.jsonl \
  --output contracts/approved-baseline.json
```

Review the run outputs with your answer evaluators and inspect the execution measurements before committing the baseline. The command refuses failing/incomplete runs and refuses to overwrite an existing baseline. Explicit `--replace` permits replacement. Do not run baseline capture automatically on the candidate you are checking. The tool cannot verify that a human actually reviewed an artifact.

## Python API

```python
import json
from spanverdict import evaluate, load_policy, load_spans

policy = load_policy('contracts/agent.json')
spans = load_spans('artifacts/candidate.jsonl')
with open('contracts/approved-baseline.json', encoding='utf-8') as file:
    baseline = json.load(file)
result = evaluate(policy, spans, baseline=baseline)
assert result['passed'], result['summary']
```

Use the bounded `spanverdict.jsonio.read_json` loader when the baseline is untrusted. `parse_batches` accepts decoded OTLP trace batches. `capture_baseline` returns an artifact for review. Call `atomic_write` with all input paths in `protected` when writing from Python; the CLI supplies those protections automatically.

## OpenTelemetry SDK and Collector

The verified SDK example emits real spans around synthetic operations. It makes no model or refund calls:

```sh
python -m pip install -r requirements-integration.txt
python examples/otel_sdk_export.py --output candidate.jsonl
spanverdict check examples/refund-policy.json candidate.jsonl \
  --baseline examples/approved-baseline.json
```

The example uses OpenTelemetry Python 1.45.1 and the actual OTLP encoder. Generic Protobuf JSON encodes byte IDs as base64, so the example converts ID fields to hexadecimal as required by OTLP JSON. Do not feed generic Protobuf JSON or SDK console text directly into the CLI.

For an existing Collector, add an uncompressed JSON file exporter to the trace pipeline:

```yaml
exporters:
  file/evaluation:
    path: /artifacts/candidate.jsonl
    format: json
    append: false
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: []
      exporters: [file/evaluation]
```

Merge this fragment with your existing receiver configuration. Flush and stop export before checking the file. Disable sampling for evaluation runs and include the complete parent graph. Collector deployment is a documented recipe; the real SDK/encoder integration is the executable verification in this repository.

Attach `spanverdict.case_id` only to the evaluation root with `gen_ai.operation.name=invoke_agent` by default. Use non-sensitive stable case IDs. Each independent repeated run needs a distinct trace ID. Configure `root_operation` for `invoke_workflow` roots.
