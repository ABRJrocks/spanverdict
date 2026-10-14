"""Evaluate complete case coverage and per-run execution contracts."""

from collections import Counter, defaultdict

from .graph import build_runs
from .metrics import measure, summarize
from .otlp import OP, TOOL
from .ordering import check_order
from .policy import fingerprint, validate_policy


def check_run(run, values, policy):
    issues = []
    for metric, maximum in sorted(policy["limits"].items()):
        actual = values[metric]
        if actual is None:
            issues.append({"code": "missing_measurement", "metric": metric})
        elif actual > maximum:
            issues.append({"code": "budget_exceeded", "metric": metric, "actual": actual, "limit": maximum})
    tools = [span for span in run.spans if span.attrs.get(OP) == "execute_tool"]
    calls = Counter(span.attrs[TOOL] for span in tools)
    successful = Counter(span.attrs[TOOL] for span in tools if span.status == 1)
    tool_policy = policy["tools"]
    if "allow" in tool_policy:
        allowed = set(tool_policy["allow"])
        for span in tools:
            if span.attrs[TOOL] not in allowed:
                issues.append({"code": "tool_not_allowed", "tool": span.attrs[TOOL], "span_id": span.span_id})
    for name, minimum in sorted(tool_policy["required"].items()):
        if successful[name] < minimum:
            issues.append({"code": "required_tool_missing", "tool": name,
                           "actual": successful[name], "minimum": minimum})
    for name, maximum in sorted(tool_policy["max_calls"].items()):
        if calls[name] > maximum:
            issues.append({"code": "tool_calls_exceeded", "tool": name,
                           "actual": calls[name], "limit": maximum})
    return issues + check_order(run, policy["order"])


def evaluate(policy, spans):
    policy = validate_policy(policy)
    runs = build_runs(spans, root_operation=policy["root_operation"])
    grouped = defaultdict(list)
    for run in runs:
        values = measure(run, set(policy["model_operations"]))
        grouped[run.case_id].append({"trace_id": run.trace_id, "metrics": values,
                                     "issues": check_run(run, values, policy)})
    cases = []
    expected = set(policy["cases"])
    for case_id in sorted(expected | set(grouped)):
        recorded = grouped[case_id]
        issues = []
        if case_id not in expected:
            issues.append({"code": "unexpected_case"})
        elif len(recorded) < policy["min_runs_per_case"]:
            issues.append({"code": "case_coverage", "actual": len(recorded),
                           "minimum": policy["min_runs_per_case"]})
        cases.append({"id": case_id, "runs": recorded, "p95": summarize([r["metrics"] for r in recorded]),
                      "issues": issues})
    result = {"version": 1, "measurement_version": 1, "name": policy["name"],
              "policy_sha256": fingerprint(policy), "cases": cases}
    return finalize(result)


def finalize(result):
    failures = sum(len(case["issues"]) + sum(len(run["issues"]) for run in case["runs"])
                   for case in result["cases"])
    result["passed"] = failures == 0
    result["summary"] = {"cases": len(result["cases"]),
                         "runs": sum(len(case["runs"]) for case in result["cases"]), "failures": failures}
    return result
