import unittest

from spanverdict.engine import evaluate
from spanverdict.otlp import parse_batches
from helpers import raw_spans, run, span
from test_policy import policy


class OrderTests(unittest.TestCase):
    def evaluate(self, value, *, same_parent=True):
        p = policy(order=[{'before':'lookup','after':'update','same_parent':same_parent}])
        return evaluate(p, parse_batches([value]))

    def test_completed_lookup_passes_in_unordered_export(self):
        value = run()
        raw_spans(value).reverse()
        self.assertTrue(self.evaluate(value)['passed'])

    def test_overlapping_prerequisite_does_not_pass(self):
        value = run()
        raw_spans(value)[2]['endTimeUnixNano'] = '22000000'
        self.assertFalse(self.evaluate(value)['passed'])

    def test_failed_and_unknown_status_prerequisite(self):
        for status in (0,2):
            value = run()
            raw_spans(value)[2]['status']['code'] = status
            self.assertFalse(self.evaluate(value)['passed'])

    def test_unrelated_branch_cannot_satisfy_same_parent(self):
        value = run()
        raw_spans(value)[2]['parentSpanId'] = f'{2:016x}'
        self.assertFalse(self.evaluate(value)['passed'])
        self.assertTrue(self.evaluate(value, same_parent=False)['passed'])

    def test_every_mutation_checked_including_early_attempt(self):
        value = run()
        raw_spans(value).append(span(5,parent=1,op='execute_tool',tool='update',start=2_000_000,end=3_000_000))
        result = self.evaluate(value)
        issues = result['cases'][0]['runs'][0]['issues']
        self.assertEqual([i['span_id'] for i in issues], [f'{5:016x}'])

    def test_absent_after_tool_is_not_required_by_order_alone(self):
        value = run()
        raw_spans(value).pop()
        self.assertTrue(self.evaluate(value)['passed'])
