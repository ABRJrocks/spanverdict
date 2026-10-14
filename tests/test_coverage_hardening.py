import unittest

from spanverdict import InputError, evaluate, parse_batches, validate_policy
from helpers import attr, raw_spans, run, span
from test_policy import policy


class CoverageHardeningTests(unittest.TestCase):
    def test_removed_model_instrumentation_does_not_pass_minimum(self):
        value = run()
        raw_spans(value)[1]['attributes'] = []
        result = evaluate(policy(minimums={'model_calls':1}),parse_batches([value]))
        self.assertFalse(result['passed'])
        self.assertEqual(result['cases'][0]['runs'][0]['issues'][0]['code'],'below_minimum')

    def test_tool_name_requires_classified_operation(self):
        value = run()
        raw_spans(value)[2]['attributes'] = [attr('gen_ai.tool.name','lookup')]
        with self.assertRaises(InputError):
            evaluate(policy(),parse_batches([value]))

    def test_nested_models_rejected_through_intermediate_spans(self):
        value = run()
        raw_spans(value).extend([span(6,parent=2),span(7,parent=6,op='chat',tokens=(10,10))])
        with self.assertRaisesRegex(InputError,'Nested model'):
            evaluate(policy(),parse_batches([value]))

    def test_many_independent_model_calls_not_rejected(self):
        value = run()
        raw_spans(value).append(span(6,parent=1,op='chat',tokens=(10,10)))
        self.assertTrue(evaluate(policy(),parse_batches([value]))['passed'])

    def test_huge_numbers_and_contradictory_bounds(self):
        for value in (policy(limits={'duration_ms':10**1000}),
                      policy(minimums={'model_calls':3},limits={'model_calls':2}),
                      policy(minimums={'unknown':1})):
            with self.assertRaises(InputError):
                validate_policy(value)
