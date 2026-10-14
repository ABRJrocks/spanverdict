"""Check completion before execution, independently of export order."""

from .otlp import OP, TOOL


def check_order(run, rules):
    tools = [span for span in run.spans if span.attrs.get(OP) == "execute_tool"]
    issues = []
    for index, rule in enumerate(rules):
        earliest = {}
        for span in tools:
            if span.attrs[TOOL] != rule["before"] or span.status != 1:
                continue
            parent = span.parent_id if rule["same_parent"] else ""
            earliest[parent] = min(earliest.get(parent, span.end_ns), span.end_ns)
        for span in tools:
            if span.attrs[TOOL] != rule["after"]:
                continue
            parent = span.parent_id if rule["same_parent"] else ""
            if parent not in earliest or earliest[parent] > span.start_ns:
                issues.append({"code": "tool_order", "rule": index, "span_id": span.span_id,
                               "before": rule["before"], "after": rule["after"]})
    return issues
