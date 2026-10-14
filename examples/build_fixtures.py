"""Reproducible synthetic OTLP fixtures; performs no model or business calls."""

import json
from pathlib import Path


def attribute(key, value):
    return {"key": key, "value": {"intValue" if type(value) is int else "stringValue": str(value)}}


def make_span(trace, number, start, end, operation, *, case=None, tool=None, tokens=None):
    attrs = [attribute("gen_ai.operation.name",operation)]
    for key, value in (("spanverdict.case_id",case),("gen_ai.tool.name",tool)):
        if value is not None:
            attrs.append(attribute(key,value))
    if tokens is not None:
        attrs.extend([attribute("gen_ai.usage.input_tokens",tokens[0]),attribute("gen_ai.usage.output_tokens",tokens[1])])
    value = {"traceId":f"{trace:032x}","spanId":f"{number:016x}","name":operation,
             "startTimeUnixNano":str(start),"endTimeUnixNano":str(end),"attributes":attrs,"status":{"code":1}}
    if number != 1:
        value["parentSpanId"] = f"{1:016x}"
    return value


def fixture(broken=False):
    batches = []
    for index, case in enumerate(("refund-standard","refund-partial","refund-escalated")):
        for repeat in range(3):
            trace = index * 3 + repeat + 1
            start = 1_700_000_000_000_000_000 + trace * 1_000_000_000
            ns = lambda ms: start + ms * 1_000_000
            duration = 250 if broken and case == "refund-partial" else 90 + repeat * 3
            spans = [make_span(trace,1,ns(0),ns(duration),"invoke_agent",case=case),
                     make_span(trace,2,ns(1),ns(12),"chat",tokens=(8000 if broken and case == "refund-partial" else 300+repeat*10,60)),
                     make_span(trace,3,ns(15),ns(25),"execute_tool",tool="lookup_customer"),
                     make_span(trace,4,ns(30),ns(40),"execute_tool",tool="check_eligibility"),
                     make_span(trace,5,ns(45),ns(60),"execute_tool",tool="escalate_case" if case == "refund-escalated" else "apply_refund")]
            if broken and case == "refund-standard":
                spans[4]["startTimeUnixNano"], spans[4]["endTimeUnixNano"] = str(ns(5)),str(ns(10))
            if broken and case == "refund-escalated":
                spans[4]["attributes"] = [attribute("gen_ai.operation.name","execute_tool"),attribute("gen_ai.tool.name","delete_customer")]
                spans[1]["attributes"] = [a for a in spans[1]["attributes"] if a["key"] != "gen_ai.usage.input_tokens"]
            spans.reverse()  # Export order is intentionally unrelated to workflow order.
            batches.append({"resourceSpans":[{"resource":{"attributes":[attribute("service.name","synthetic-refund-agent")]},"scopeSpans":[{"scope":{"name":"spanverdict.examples"},"spans":spans}]}]})
    return '\n'.join(json.dumps(value,separators=(',',':')) for value in batches) + '\n'


if __name__ == "__main__":
    directory = Path(__file__).parent
    for filename, broken in (("good.jsonl",False),("broken.jsonl",True)):
        (directory/filename).write_text(fixture(broken),encoding="utf-8")
