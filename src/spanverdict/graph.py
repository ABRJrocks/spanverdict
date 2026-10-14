"""Reconstruct complete evaluation runs from unordered span batches."""

from collections import defaultdict
from dataclasses import dataclass

from .jsonio import InputError
from .otlp import CASE, OP, Span


@dataclass(frozen=True)
class Run:
    case_id: str
    trace_id: str
    root: Span
    spans: tuple[Span, ...]


def build_runs(spans, *, root_operation="invoke_agent"):
    traces = defaultdict(dict)
    for span in spans:
        if span.span_id in traces[span.trace_id]:
            raise InputError("Duplicate span passed to graph builder")
        traces[span.trace_id][span.span_id] = span
    if not traces:
        raise InputError("No evaluation traces")
    runs = []
    for trace_id, nodes in sorted(traces.items()):
        roots = [span for span in nodes.values() if not span.parent_id]
        if len(roots) != 1:
            raise InputError("Evaluation trace must have exactly one root")
        root = roots[0]
        if CASE not in root.attrs or root.attrs.get(OP) != root_operation:
            raise InputError("Root needs the configured operation and spanverdict.case_id")
        complete = set()
        for span in nodes.values():
            if span.parent_id and span.parent_id not in nodes:
                raise InputError("Missing parent in evaluation trace")
            if span.dropped:
                raise InputError("Dropped span attributes make the export incomplete")
            if span.start_ns < root.start_ns or span.end_ns > root.end_ns:
                raise InputError("Span falls outside the evaluation root interval")
            if CASE in span.attrs and span.attrs[CASE] != root.attrs[CASE]:
                raise InputError("Conflicting case identifiers within a trace")
        for span_id in nodes:
            path, current = set(), span_id
            while current and current not in complete:
                if current in path:
                    raise InputError("Cycle in span parent graph")
                path.add(current)
                current = nodes[current].parent_id
            complete.update(path)
        runs.append(Run(root.attrs[CASE], trace_id, root, tuple(
            sorted(nodes.values(), key=lambda span: (span.start_ns, span.span_id)))))
    return runs
