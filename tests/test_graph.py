import unittest

from spanverdict.graph import build_runs
from spanverdict.jsonio import InputError
from spanverdict.otlp import parse_batches
from helpers import batch, raw_spans, run, span


class GraphTests(unittest.TestCase):
    def test_unordered_spans_and_multiple_traces(self):
        a, b = run(), run(case='faq', trace=2)
        raw_spans(a).reverse()
        runs = build_runs(parse_batches([b, a]))
        self.assertEqual([r.case_id for r in runs], ['refund', 'faq'])

    def test_missing_parent(self):
        value = run()
        raw_spans(value)[1]['parentSpanId'] = f'{999:016x}'
        with self.assertRaisesRegex(InputError, 'Missing parent'):
            build_runs(parse_batches([value]))

    def test_duplicate_roots_or_missing_case(self):
        for value in (batch(span(case='one'), span(2, case='one')),
                      batch(span(op='invoke_agent'))):
            with self.assertRaises(InputError):
                build_runs(parse_batches([value]))

    def test_disconnected_cycle_with_root(self):
        value = batch(span(case='one', op='invoke_agent'), span(2, parent=3), span(3, parent=2))
        with self.assertRaisesRegex(InputError, 'Cycle'):
            build_runs(parse_batches([value]))

    def test_outside_root_and_dropped_attributes(self):
        for change in ({'endTimeUnixNano': '100000001'}, {'droppedAttributesCount': 1}):
            value = run()
            raw_spans(value)[1].update(change)
            with self.assertRaises(InputError):
                build_runs(parse_batches([value]))

    def test_conflicting_case_and_cross_trace_parent(self):
        for value in (batch(span(case='one', op='invoke_agent'), span(2, parent=1, case='two')),
                      batch(span(case='one', op='invoke_agent'), span(2, trace=2, parent=1))):
            with self.assertRaises(InputError):
                build_runs(parse_batches([value]))

    def test_deep_graph_without_python_recursion(self):
        value = batch(span(case='one', op='invoke_agent'), *[span(i, parent=i-1) for i in range(2, 2000)])
        self.assertEqual(len(build_runs(parse_batches([value]))[0].spans), 1999)
