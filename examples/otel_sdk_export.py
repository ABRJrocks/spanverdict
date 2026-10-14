"""Produce real Python SDK spans with synthetic refund-agent operations.

No model, payment or network calls occur. This is an instrumentation example,
not a refund implementation. Requires requirements-integration.txt.
"""

import argparse
import base64
import json
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import Status, StatusCode


def otlp_json(spans):
    value = MessageToDict(encode_spans(spans),use_integers_for_enums=True)
    # Protobuf's generic JSON encoder uses base64; OTLP JSON requires hex IDs.
    def convert(item):
        if isinstance(item,list):
            for child in item: convert(child)
        elif isinstance(item,dict):
            for key,child in item.items():
                if key in ('traceId','spanId','parentSpanId'):
                    item[key] = base64.b64decode(child).hex()
                else:
                    convert(child)
    convert(value)
    return value


def write_example(path, *, broken=False):
    provider = TracerProvider(sampler=ALWAYS_ON)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer('spanverdict.refund-example','1.0')
    for index,case in enumerate(('refund-standard','refund-partial','refund-escalated')):
        for repeat in range(3):
            start = 1_700_000_000_000_000_000 + (index*3+repeat+1)*1_000_000_000
            ns = lambda ms: start + ms*1_000_000
            root = tracer.start_span('refund workflow',start_time=ns(0),attributes={
                'gen_ai.operation.name':'invoke_agent','spanverdict.case_id':case})
            with trace.use_span(root,end_on_exit=False):
                model_attrs = {'gen_ai.operation.name':'chat','gen_ai.usage.input_tokens':300+repeat*10,
                               'gen_ai.usage.output_tokens':60,'gen_ai.request.model':'synthetic-model'}
                if broken and case == 'refund-partial': model_attrs['gen_ai.usage.input_tokens'] = 8000
                if broken and case == 'refund-escalated': del model_attrs['gen_ai.usage.input_tokens']
                model = tracer.start_span('model generation',start_time=ns(1),attributes=model_attrs)
                model.set_status(Status(StatusCode.OK))
                model.end(end_time=ns(12))
                tools = [('lookup_customer',15,25),('check_eligibility',30,40),
                         ('escalate_case' if case == 'refund-escalated' else 'apply_refund',45,60)]
                if broken and case == 'refund-standard': tools[2] = ('apply_refund',5,10)
                if broken and case == 'refund-escalated': tools[2] = ('delete_customer',45,60)
                for name,begin,end in tools:
                    tool = tracer.start_span(name,start_time=ns(begin),attributes={
                        'gen_ai.operation.name':'execute_tool','gen_ai.tool.name':name})
                    tool.set_status(Status(StatusCode.OK))
                    tool.end(end_time=ns(end))
            root.set_status(Status(StatusCode.OK))
            root.end(end_time=ns(250 if broken and case == 'refund-partial' else 90+repeat*3))
    provider.force_flush()
    value = otlp_json(exporter.get_finished_spans())
    provider.shutdown()
    Path(path).write_text(json.dumps(value,separators=(',',':'))+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--broken',action='store_true')
    args = parser.parse_args()
    write_example(args.output,broken=args.broken)
