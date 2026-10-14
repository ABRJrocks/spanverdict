import unittest

from spanverdict.graph import build_runs
from spanverdict.jsonio import InputError
from spanverdict.metrics import measure, p95, summarize
from spanverdict.otlp import MODEL_OPS, parse_batches
from helpers import attr, raw_spans, run


class MetricTests(unittest.TestCase):
    def measure(self, value):
        return measure(build_runs(parse_batches([value]))[0], MODEL_OPS)

    def test_root_duration_not_sum_of_children(self):
        values = self.measure(run())
        self.assertEqual(values, {'duration_ms':99., 'model_calls':1, 'tool_calls':2,
                                  'error_spans':0, 'input_tokens':100, 'output_tokens':20})

    def test_missing_usage_not_zero(self):
        value = run()
        raw_spans(value)[1]['attributes'] = [attr('gen_ai.operation.name', 'chat')]
        self.assertIsNone(self.measure(value)['input_tokens'])

    def test_unclassified_usage_and_missing_tool_name(self):
        for index, attrs in ((0,[attr('gen_ai.usage.input_tokens',100)]),
                             (2,[attr('gen_ai.operation.name','execute_tool')])):
            value = run()
            raw_spans(value)[index]['attributes'].extend(attrs) if index == 0 else None
            if index == 2:
                raw_spans(value)[index]['attributes'] = attrs
            with self.assertRaises(InputError):
                self.measure(value)

    def test_nearest_rank_and_missing_samples(self):
        self.assertEqual(p95(range(1,21)), 19)
        self.assertEqual(p95([1]), 1)
        self.assertIsNone(p95([1,None]))
        self.assertIsNone(p95([]))

    def test_recovered_errors_are_still_counted(self):
        value = run()
        raw_spans(value)[1]['status']['code'] = 2
        self.assertEqual(self.measure(value)['error_spans'], 1)

    def test_summary_retains_missing_direction(self):
        value = self.measure(run())
        self.assertEqual(summarize([value])['input_tokens'], 100)
        value['input_tokens'] = None
        self.assertIsNone(summarize([value])['input_tokens'])
