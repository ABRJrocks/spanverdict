"""Read the documented OTLP JSON trace profile without retaining content."""

from dataclasses import dataclass
from pathlib import Path
import re

from .jsonio import InputError, decode, read_text

CASE = "spanverdict.case_id"
OP = "gen_ai.operation.name"
TOOL = "gen_ai.tool.name"
INPUT = "gen_ai.usage.input_tokens"
OUTPUT = "gen_ai.usage.output_tokens"
MODEL_OPS = frozenset({"chat", "generate_content", "text_completion"})
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
SELECTED = {CASE, OP, TOOL, INPUT, OUTPUT}


@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_id: str
    start_ns: int
    end_ns: int
    status: int
    attrs: dict
    dropped: int = 0


def integer(value, *, maximum=2**64 - 1):
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,20}", value):
        value = int(value)
    if type(value) is not int or not 0 <= value <= maximum:
        raise InputError("Expected a nonnegative bounded integer")
    return value


def identifier(value, length, *, parent=False):
    if parent and value in (None, "", "0" * length):
        return ""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{%d}" % length, value):
        raise InputError("Invalid OTLP trace or span identifier")
    if value == "0" * length:
        raise InputError("Zero OTLP identifier")
    return value.lower()


def object_value(value, label):
    if not isinstance(value, dict):
        raise InputError(f"Expected {label} object")
    return value


def array(value, label):
    if not isinstance(value, list):
        raise InputError(f"Expected {label} array")
    return value


def attributes(values):
    result, seen = {}, set()
    for item in array(values, "attributes"):
        item = object_value(item, "attribute")
        key = item.get("key")
        if not isinstance(key, str) or not key or key in seen:
            raise InputError("Invalid or duplicate OTLP attribute key")
        seen.add(key)
        if key not in SELECTED:
            continue
        value = object_value(item.get("value"), "attribute value")
        if key in {INPUT, OUTPUT}:
            if "intValue" not in value:
                raise InputError("Token usage requires OTLP intValue")
            result[key] = integer(value["intValue"], maximum=2**63 - 1)
        else:
            text = value.get("stringValue")
            if not isinstance(text, str) or not LABEL.fullmatch(text):
                raise InputError("Case, operation and tool labels require safe identifiers")
            result[key] = text
        # AnyValue is a protobuf oneof, not a collection of alternative values.
        alternatives = set(value) & {"stringValue", "boolValue", "intValue", "doubleValue",
                                     "arrayValue", "kvlistValue", "bytesValue"}
        if len(alternatives) != 1:
            raise InputError("Ambiguous OTLP attribute value")
    return result


def parse_span(value):
    value = object_value(value, "span")
    start = integer(value.get("startTimeUnixNano"))
    end = integer(value.get("endTimeUnixNano"))
    if not start or end < start:
        raise InputError("Missing or reversed span timestamps")
    status = object_value(value.get("status", {}), "status").get("code", 0)
    if type(status) is not int or status not in (0, 1, 2):
        raise InputError("Status code must be a numeric OTLP enum")
    return Span(identifier(value.get("traceId"), 32), identifier(value.get("spanId"), 16),
                identifier(value.get("parentSpanId"), 16, parent=True), start, end, status,
                attributes(value.get("attributes", [])),
                integer(value.get("droppedAttributesCount", 0), maximum=2**32 - 1))


def parse_batches(batches, *, max_spans=100_000):
    spans, seen, received = [], {}, 0
    for batch in batches:
        batch = object_value(batch, "trace batch")
        if "resourceSpans" not in batch or "resourceMetrics" in batch or "resourceLogs" in batch:
            raise InputError("Expected an OTLP trace export")
        for resource in array(batch["resourceSpans"], "resourceSpans"):
            for scope in array(object_value(resource, "resource").get("scopeSpans", []), "scopeSpans"):
                for raw in array(object_value(scope, "scope").get("spans", []), "spans"):
                    received += 1
                    if received > max_spans:
                        raise InputError("Export exceeds span limit")
                    span = parse_span(raw)
                    key = (span.trace_id, span.span_id)
                    if key in seen:
                        if seen[key] != span:
                            raise InputError("Conflicting repeated span identifier")
                        continue
                    seen[key] = span
                    spans.append(span)
    if not spans:
        raise InputError("Export contains no spans")
    return spans


def load_spans(path, *, format="jsonl", max_bytes=64 * 1024 * 1024, max_spans=100_000):
    text = read_text(Path(path), max_bytes)
    if format == "json":
        batches = [decode(text)]
    elif format == "jsonl":
        lines = text.split("\n")
        if lines and not lines[-1]:
            lines.pop()
        if any(not line.strip() for line in lines):
            raise InputError("Blank JSONL lines are not trace batches")
        batches = (decode(line) for line in lines)
    else:
        raise InputError("Export format must be json or jsonl")
    return parse_batches(batches, max_spans=max_spans)
