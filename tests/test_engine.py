import unittest

from spanverdict.engine import evaluate
from spanverdict.otlp import parse_batches
from helpers import attr, raw_spans, run
from test_policy import policy


class EngineTests(unittest.TestCase):
    def evaluate(self, p=None, value=None):
        return evaluate(p or policy(), parse_batches([value or run()]))

    def codes(self, result):
        return [issue['code'] for case in result['cases'] for issue in
                case['issues'] + [i for r in case['runs'] for i in r['issues']]]

    def test_accepted_contract(self):
        self.assertTrue(self.evaluate()['passed'])

    def test_each_run_budget_not_average(self):
        value = run(trace=2)
        raw_spans(value)[1]['attributes'].append(attr('private.prompt', 'secret-value'))
        raw_spans(value)[1]['attributes'] = [a if a['key'] != 'gen_ai.usage.input_tokens'
                                            else attr(a['key'], 1000) for a in raw_spans(value)[1]['attributes']]
        result = evaluate(policy(limits={'input_tokens':150}), parse_batches([run(), value]))
        self.assertFalse(result['passed'])
        self.assertEqual(self.codes(result), ['budget_exceeded'])
        self.assertNotIn('secret-value', str(result))

    def test_missing_or_unexpected_case(self):
        for p in (policy(cases=['refund','faq']), policy(cases=['faq'])):
            self.assertFalse(self.evaluate(p)['passed'])

    def test_minimum_repeated_runs(self):
        self.assertIn('case_coverage', self.codes(self.evaluate(policy(min_runs_per_case=2))))
        result = evaluate(policy(min_runs_per_case=2), parse_batches([run(),run(trace=2)]))
        self.assertTrue(result['passed'])

    def test_missing_measured_tokens(self):
        value = run()
        raw_spans(value)[1]['attributes'] = [attr('gen_ai.operation.name','chat')]
        self.assertIn('missing_measurement', self.codes(self.evaluate(policy(limits={'input_tokens':500}),value)))

    def test_tools_allowlist_counts_and_required_success(self):
        self.assertIn('tool_not_allowed', self.codes(self.evaluate(policy(tools={'allow':['lookup']}))))
        self.assertIn('tool_calls_exceeded', self.codes(self.evaluate(policy(tools={'max_calls':{'update':0}}))))
        value = run()
        raw_spans(value)[2]['status']['code'] = 0
        result = self.evaluate(policy(tools={'required':{'lookup':1}}),value)
        self.assertIn('required_tool_missing', self.codes(result))

    def test_zero_usage_and_exact_limit(self):
        result = self.evaluate(policy(limits={'input_tokens':100,'duration_ms':99,'tool_calls':2}))
        self.assertTrue(result['passed'])
