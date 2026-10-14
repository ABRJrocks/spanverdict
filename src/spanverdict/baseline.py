"""Reviewed per-case baselines bound to policy and measurement versions."""

from decimal import Decimal
import math
import re

from .jsonio import InputError
from .policy import METRICS, fingerprint, obj, validate_policy


def capture_baseline(policy, spans):
    from .engine import assess_runs
    policy = validate_policy(policy)
    result = assess_runs(policy, spans)
    if not result["passed"]:
        raise InputError("Cannot capture a baseline from a failing or incomplete run")
    return {"version": 1, "measurement_version": 1,
            "policy_sha256": result["policy_sha256"], "evidence_sha256": result["evidence_sha256"],
            "cases": {case["id"]: {"runs": len(case["runs"]), "p95": case["p95"]}
                      for case in result["cases"]}}


def validate_baseline(value, policy):
    obj(value, {"version", "measurement_version", "policy_sha256", "evidence_sha256", "cases"},
        {"version", "measurement_version", "policy_sha256", "evidence_sha256", "cases"})
    for field in ("version", "measurement_version"):
        if type(value[field]) is not int or value[field] != 1:
            raise InputError("Unsupported baseline or measurement version")
    for field in ("policy_sha256", "evidence_sha256"):
        if not isinstance(value[field], str) or not re.fullmatch(r"[0-9a-f]{64}", value[field]):
            raise InputError("Invalid baseline fingerprint")
    if value["policy_sha256"] != fingerprint(policy):
        raise InputError("Baseline policy fingerprint does not match")
    obj(value["cases"], policy["cases"], policy["cases"])
    for case in value["cases"].values():
        obj(case, {"runs", "p95"}, {"runs", "p95"})
        if type(case["runs"]) is not int or not policy["min_runs_per_case"] <= case["runs"] <= 100_000:
            raise InputError("Baseline has insufficient or invalid run coverage")
        obj(case["p95"], METRICS, METRICS)
        for metric, actual in case["p95"].items():
            if actual is None:
                if metric in policy["regressions"] or metric in policy["limits"]:
                    raise InputError("Baseline is missing a requested measurement")
                continue
            if type(actual) not in (int, float) or not math.isfinite(actual) or not 0 <= actual <= 10**30:
                raise InputError("Invalid baseline measurement")
            if metric != "duration_ms" and type(actual) is not int:
                raise InputError("Baseline counters must be integers")
    return value


def compare(result, policy, baseline):
    baseline = validate_baseline(baseline, policy)
    for case in result["cases"]:
        if case["id"] not in baseline["cases"] or not case["runs"]:
            continue
        for metric, allowance in sorted(policy["regressions"].items()):
            actual = case["p95"][metric]
            if actual is None:
                continue  # Per-run missing_measurement already blocks the verdict.
            previous = baseline["cases"][case["id"]]["p95"][metric]
            base = Decimal(str(previous))
            limit = base + max(Decimal(str(allowance["absolute"])), base * Decimal(str(allowance["relative"])))
            if Decimal(str(actual)) > limit:
                case["issues"].append({"code": "regression", "metric": metric,
                                       "actual": actual, "baseline": previous, "limit": float(limit)})
