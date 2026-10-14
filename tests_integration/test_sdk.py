import json
from pathlib import Path
import runpy
import tempfile
import unittest

from spanverdict import evaluate, load_policy, load_spans

ROOT = Path(__file__).resolve().parents[1]


class SdkIntegrationTests(unittest.TestCase):
    def test_actual_sdk_and_otlp_encoder_accept_and_reject(self):
        write = runpy.run_path(str(ROOT/'examples/otel_sdk_export.py'))['write_example']
        p = load_policy(ROOT/'examples/refund-policy.json')
        baseline = json.loads((ROOT/'examples/approved-baseline.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            for broken in (False,True):
                path = Path(directory)/'traces.jsonl'
                write(path,broken=broken)
                spans = load_spans(path)
                self.assertEqual(len(spans),45)
                result = evaluate(p,spans,baseline=baseline)
                self.assertEqual(result['passed'],not broken)
                self.assertEqual(result['summary']['failures'],17 if broken else 0)
