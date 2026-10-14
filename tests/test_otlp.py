import json
import tempfile
import unittest
from pathlib import Path

from spanverdict.jsonio import InputError
from spanverdict.otlp import load_spans, parse_batches, parse_span
from helpers import attr, batch, span


class OtlpTests(unittest.TestCase):
    def test_string_and_number_timestamps(self):
        a = span()
        b = dict(a, startTimeUnixNano=1_000_000, endTimeUnixNano=10_000_000)
        self.assertEqual(parse_span(a), parse_span(b))

    def test_hex_is_case_insensitive(self):
        value = span(15, trace=15)
        value['traceId'] = value['traceId'].upper()
        self.assertEqual(parse_span(value).trace_id, f'{15:032x}')

    def test_bad_ids_and_times(self):
        for field, value in [('traceId', '0'*32), ('spanId', 'bad'), ('parentSpanId', 'abc'),
                             ('startTimeUnixNano', True), ('endTimeUnixNano', '0'),
                             ('startTimeUnixNano', '-1'), ('startTimeUnixNano', str(2**64)),
                             ('status', {'code': 'STATUS_CODE_OK'})]:
            with self.subTest(field=field), self.assertRaises(InputError):
                parse_span(dict(span(), **{field: value}))

    def test_ignores_prompt_and_unknown_fields(self):
        value = span(op='chat', tokens=(0, 0))
        value['attributes'].append(attr('gen_ai.input.messages', 'private-value'))
        value['unknownFutureField'] = 3
        self.assertNotIn('private-value', repr(parse_span(value)))

    def test_duplicate_attributes_and_oneof(self):
        value = span(op='chat')
        value['attributes'].append(attr('gen_ai.operation.name', 'chat'))
        with self.assertRaises(InputError):
            parse_span(value)
        value = span(op='chat')
        value['attributes'][0]['value']['intValue'] = '1'
        with self.assertRaises(InputError):
            parse_span(value)

    def test_invalid_usage(self):
        for value in (-1, True, 1.5):
            raw = span(op='chat')
            raw['attributes'].append({'key': 'gen_ai.usage.input_tokens', 'value': {'intValue': value}})
            with self.assertRaises(InputError):
                parse_span(raw)

    def test_identical_delivery_deduplicated_conflicts_block(self):
        self.assertEqual(len(parse_batches([batch(span(), span())])), 1)
        with self.assertRaises(InputError):
            parse_batches([batch(span(), span(end=20_000_000))])

    def test_empty_wrong_signal_and_limit(self):
        for value in (batch(), {}, {'resourceMetrics': []}):
            with self.assertRaises(InputError):
                parse_batches([value])
        with self.assertRaises(InputError):
            parse_batches([batch(span(), span())], max_spans=1)

    def test_document_and_unordered_jsonl_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'traces'
            path.write_text(json.dumps(batch(span(2)))+'\n'+json.dumps(batch(span(1)))+'\n')
            self.assertEqual(len(load_spans(path)), 2)
            path.write_text(json.dumps(batch(span())))
            self.assertEqual(len(load_spans(path, format='json')), 1)
            path.write_text('\n'+json.dumps(batch(span())))
            with self.assertRaises(InputError):
                load_spans(path)
