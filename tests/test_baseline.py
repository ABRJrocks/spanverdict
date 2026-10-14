import copy
import unittest

from spanverdict.baseline import capture_baseline
from spanverdict.engine import evaluate
from spanverdict.jsonio import InputError
from spanverdict.otlp import parse_batches
from helpers import attr, raw_spans, run
from test_policy import policy


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.p = policy(regressions={'input_tokens':{'relative':.1,'absolute':5}})
        self.spans = parse_batches([run()])
        self.baseline = capture_baseline(self.p, self.spans)

    def candidate(self, tokens):
        value = run()
        attrs = raw_spans(value)[1]['attributes']
        raw_spans(value)[1]['attributes'] = [a if a['key'] != 'gen_ai.usage.input_tokens'
                                           else attr(a['key'],tokens) for a in attrs]
        return parse_batches([value])

    def test_baseline_required_and_unchanged_passes(self):
        with self.assertRaises(InputError):
            evaluate(self.p,self.spans)
        self.assertTrue(evaluate(self.p,self.spans,baseline=self.baseline)['passed'])

    def test_relative_and_absolute_allowance_boundary(self):
        self.assertTrue(evaluate(self.p,self.candidate(110),baseline=self.baseline)['passed'])
        self.assertFalse(evaluate(self.p,self.candidate(111),baseline=self.baseline)['passed'])

    def test_case_average_cannot_hide_broken_case(self):
        p = policy(cases=['refund','faq'],regressions={'input_tokens':{'relative':0,'absolute':0}})
        base = capture_baseline(p,parse_batches([run(),run(case='faq',trace=2)]))
        value = run(case='faq',trace=2)
        raw_spans(value)[1]['attributes'] = [attr('gen_ai.operation.name','chat'),
                                           attr('gen_ai.usage.input_tokens',0),attr('gen_ai.usage.output_tokens',0)]
        result = evaluate(p,self.candidate(101)+parse_batches([value]),baseline=base)
        self.assertFalse(result['passed'])
        self.assertEqual([c['id'] for c in result['cases'] if c['issues']],['refund'])

    def test_fingerprint_case_set_and_missing_measurement(self):
        for change in ('fingerprint','cases','usage','version','boolean'):
            value = copy.deepcopy(self.baseline)
            if change == 'fingerprint': value['policy_sha256'] = '0'*64
            if change == 'cases': value['cases'] = {}
            if change == 'usage': value['cases']['refund']['p95']['input_tokens'] = None
            if change == 'version': value['measurement_version'] = 2
            if change == 'boolean': value['cases']['refund']['runs'] = True
            with self.subTest(change=change), self.assertRaises(InputError):
                evaluate(self.p,self.spans,baseline=value)

    def test_failing_candidate_cannot_become_baseline(self):
        with self.assertRaises(InputError):
            capture_baseline(policy(limits={'input_tokens':1}),self.spans)

    def test_missing_usage_cannot_become_regression_baseline(self):
        value = run()
        raw_spans(value)[1]['attributes'] = [attr('gen_ai.operation.name','chat')]
        with self.assertRaises(InputError):
            capture_baseline(self.p,parse_batches([value]))

    def test_baseline_does_not_mutate_on_comparison(self):
        previous = copy.deepcopy(self.baseline)
        evaluate(self.p,self.candidate(111),baseline=self.baseline)
        self.assertEqual(previous,self.baseline)

    def test_evidence_hash_ignores_export_order_and_private_content(self):
        value = run()
        raw_spans(value).reverse()
        raw_spans(value)[0]['attributes'].append(attr('gen_ai.input.messages','private'))
        other = capture_baseline(self.p,parse_batches([value]))
        self.assertEqual(other['evidence_sha256'],self.baseline['evidence_sha256'])
