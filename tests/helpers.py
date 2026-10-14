import copy


def attr(key, value):
    return {"key": key, "value": {"intValue" if type(value) is int else "stringValue": str(value)}}


def span(number=1, *, trace=1, parent=None, start=1_000_000, end=10_000_000, op=None, tool=None, case=None, tokens=None, status=1):
    value = {"traceId": f"{trace:032x}", "spanId": f"{number:016x}",
             "startTimeUnixNano": str(start), "endTimeUnixNano": str(end),
             "status": {"code": status}, "attributes": []}
    if parent:
        value['parentSpanId'] = f"{parent:016x}"
    for key, item in (("gen_ai.operation.name", op), ("gen_ai.tool.name", tool), ("spanverdict.case_id", case)):
        if item is not None:
            value['attributes'].append(attr(key, item))
    if tokens is not None:
        for key, item in zip(('gen_ai.usage.input_tokens', 'gen_ai.usage.output_tokens'), tokens):
            value['attributes'].append(attr(key, item))
    return value


def batch(*spans):
    return {"resourceSpans": [{"scopeSpans": [{"spans": list(copy.deepcopy(spans))}]}]}


def run(*, case='refund', trace=1):
    return batch(span(case=case, trace=trace, op='invoke_agent', end=100_000_000),
                 span(2, parent=1, trace=trace, op='chat', tokens=(100, 20)),
                 span(3, parent=1, trace=trace, op='execute_tool', tool='lookup', start=11_000_000, end=20_000_000),
                 span(4, parent=1, trace=trace, op='execute_tool', tool='update', start=21_000_000, end=30_000_000))


def raw_spans(value):
    return value['resourceSpans'][0]['scopeSpans'][0]['spans']
