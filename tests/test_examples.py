import json
from pathlib import Path
import unittest

from spanverdict import evaluate, load_policy, load_spans


ROOT = Path(__file__).resolve().parents[1]


class ExampleTests(unittest.TestCase):
    def test_good_refund_suite_has_nine_complete_runs(self):
        p = load_policy(ROOT/'examples/refund-policy.json')
        baseline = json.loads((ROOT/'examples/approved-baseline.json').read_text())
        result = evaluate(p,load_spans(ROOT/'examples/good.jsonl'),baseline=baseline)
        self.assertTrue(result['passed'])
        self.assertEqual(result['summary'],{'cases':3,'runs':9,'failures':0})

    def test_broken_suite_identifies_three_distinct_failure_modes(self):
        p = load_policy(ROOT/'examples/refund-policy.json')
        baseline = json.loads((ROOT/'examples/approved-baseline.json').read_text())
        result = evaluate(p,load_spans(ROOT/'examples/broken.jsonl'),baseline=baseline)
        self.assertFalse(result['passed'])
        self.assertEqual(result['summary']['failures'],17)
        cases = {case['id']:case for case in result['cases']}
        self.assertEqual([i['code'] for r in cases['refund-standard']['runs'] for i in r['issues']],['tool_order']*3)
        self.assertEqual([i['code'] for i in cases['refund-partial']['issues']],['regression','regression'])
        self.assertEqual(cases['refund-escalated']['p95']['input_tokens'],None)
