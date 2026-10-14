"""Run measurements and nearest-rank p95 with explicit missing usage."""

import math

from .jsonio import InputError
from .otlp import INPUT, OP, OUTPUT, TOOL
from .policy import METRICS


def measure(run, model_operations):
    models = [span for span in run.spans if span.attrs.get(OP) in model_operations]
    tools = [span for span in run.spans if span.attrs.get(OP) == "execute_tool"]
    for span in run.spans:
        if (INPUT in span.attrs or OUTPUT in span.attrs) and span.attrs.get(OP) not in model_operations:
            raise InputError("Token usage on an unclassified operation; review model_operations")
    if any(TOOL not in span.attrs for span in tools):
        raise InputError("execute_tool span is missing gen_ai.tool.name")
    values = {"duration_ms": (run.root.end_ns - run.root.start_ns) / 1_000_000,
              "model_calls": len(models), "tool_calls": len(tools),
              "error_spans": sum(span.status == 2 for span in run.spans)}
    for metric, key in (("input_tokens", INPUT), ("output_tokens", OUTPUT)):
        values[metric] = (sum(span.attrs[key] for span in models)
                          if all(key in span.attrs for span in models) else None)
    return values


def p95(values):
    if not values or any(value is None for value in values):
        return None
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * .95) - 1]


def summarize(measurements):
    return {metric: p95([values[metric] for values in measurements]) for metric in sorted(METRICS)}
