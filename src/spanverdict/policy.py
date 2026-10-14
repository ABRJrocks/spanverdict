"""Strict versioned policies; misspelled checks never disappear silently."""

import copy
import hashlib
import json
import math

from .jsonio import InputError, read_json
from .otlp import LABEL, MODEL_OPS

METRICS = {"duration_ms", "input_tokens", "output_tokens", "model_calls", "tool_calls", "error_spans"}


def obj(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise InputError("Policy object has unknown or missing fields")


def label(value):
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise InputError("Policy labels must be safe identifiers of 1 to 128 characters")


def labels(value, *, empty=False):
    if not isinstance(value, list) or (not value and not empty) or len(value) > 1000:
        raise InputError("Policy requires a bounded identifier list")
    for item in value:
        label(item)
    if len(set(value)) != len(value):
        raise InputError("Duplicate policy identifier")


def count(value, *, minimum=0, maximum=100_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError("Policy count is outside its integer bounds")


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10**18:
        raise InputError("Policy measurement must be finite, nonnegative and bounded")


def validate_policy(document):
    obj(document, {"version", "name", "cases", "min_runs_per_case", "root_operation",
                   "model_operations", "limits", "tools", "order", "regressions"},
        {"version", "name", "cases"})
    if type(document["version"]) is not int or document["version"] != 1:
        raise InputError("Unsupported policy version")
    label(document["name"])
    labels(document["cases"])
    result = copy.deepcopy(document)
    result.setdefault("min_runs_per_case", 1)
    count(result["min_runs_per_case"], minimum=1, maximum=1000)
    result.setdefault("root_operation", "invoke_agent")
    label(result["root_operation"])
    result.setdefault("model_operations", sorted(MODEL_OPS))
    labels(result["model_operations"])
    if result["root_operation"] in result["model_operations"] or "execute_tool" in result["model_operations"]:
        raise InputError("Model operations cannot include the root or execute_tool")
    result.setdefault("limits", {})
    obj(result["limits"], METRICS)
    for key, value in result["limits"].items():
        number(value)
        if key != "duration_ms":
            count(value, maximum=10**18)
    result.setdefault("tools", {})
    obj(result["tools"], {"allow", "required", "max_calls"})
    tools = result["tools"]
    if "allow" in tools:
        labels(tools["allow"], empty=True)
    for field in ("required", "max_calls"):
        tools.setdefault(field, {})
        if not isinstance(tools[field], dict):
            raise InputError("Tool counts must be an object")
        if len(tools[field]) > 1000:
            raise InputError("Too many tool rules")
        for name, value in tools[field].items():
            label(name)
            count(value, minimum=1 if field == "required" else 0)
            if "allow" in tools and name not in tools["allow"]:
                raise InputError("Required or limited tool must appear in allow list")
    for name, minimum in tools["required"].items():
        if name in tools["max_calls"] and minimum > tools["max_calls"][name]:
            raise InputError("Tool minimum exceeds maximum")
    result.setdefault("order", [])
    if not isinstance(result["order"], list) or len(result["order"]) > 100:
        raise InputError("Policy order must be a bounded rule array")
    for rule in result["order"]:
        obj(rule, {"before", "after", "same_parent"}, {"before", "after"})
        label(rule["before"])
        label(rule["after"])
        rule.setdefault("same_parent", True)
        if type(rule["same_parent"]) is not bool or rule["before"] == rule["after"]:
            raise InputError("Invalid tool ordering rule")
        if "allow" in tools and not {rule["before"], rule["after"]} <= set(tools["allow"]):
            raise InputError("Ordered tool must appear in allow list")
    result.setdefault("regressions", {})
    obj(result["regressions"], METRICS)
    for allowance in result["regressions"].values():
        obj(allowance, {"relative", "absolute"}, {"relative", "absolute"})
        number(allowance["relative"])
        number(allowance["absolute"])
    if not (result["limits"] or tools.get("allow") is not None or tools["required"]
            or tools["max_calls"] or result["order"] or result["regressions"]):
        raise InputError("Policy must declare at least one behavioral or metric check")
    return result


def fingerprint(policy):
    data = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(data).hexdigest()


def load_policy(path):
    return validate_policy(read_json(path))
