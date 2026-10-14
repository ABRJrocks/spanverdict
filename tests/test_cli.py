import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from helpers import run
from test_policy import policy


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.p = self.root/'policy.json'
        self.traces = self.root/'traces.jsonl'
        self.p.write_text(json.dumps(policy()))
        self.traces.write_text(json.dumps(run())+'\n')

    def cli(self,*args):
        return subprocess.run([sys.executable,'-m','spanverdict',*map(str,args)],capture_output=True,text=True)

    def test_lint_and_version(self):
        self.assertEqual(self.cli('lint',self.p).returncode,0)
        self.assertIn('SpanVerdict',self.cli('--version').stdout)

    def test_check_reports_and_rejection(self):
        report = self.root/'out.json'
        xml = self.root/'out.xml'
        html = self.root/'out.html'
        result = self.cli('check',self.p,self.traces,'--json-report',report,'--junit',xml,'--html-report',html)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(report.read_text())['passed'])
        self.assertTrue(xml.exists() and html.exists())
        self.p.write_text(json.dumps(policy(limits={'input_tokens':1})))
        result = self.cli('check',self.p,self.traces,'--json-report',report,'--quiet')
        self.assertEqual(result.returncode,1)
        self.assertEqual(result.stdout,'')
        self.assertFalse(json.loads(report.read_text())['passed'])

    def test_invalid_input_is_not_a_regression(self):
        self.traces.write_text('bad-private-input')
        result = self.cli('check',self.p,self.traces)
        self.assertEqual(result.returncode,2)
        self.assertNotIn('bad-private-input',result.stderr)

    def test_baseline_exclusive_and_replacement_explicit(self):
        baseline = self.root/'baseline.json'
        self.assertEqual(self.cli('baseline',self.p,self.traces,'--output',baseline).returncode,0)
        self.assertEqual(self.cli('baseline',self.p,self.traces,'--output',baseline).returncode,2)
        self.assertEqual(self.cli('baseline',self.p,self.traces,'--output',baseline,'--replace').returncode,0)

    def test_regression_requires_matching_baseline(self):
        baseline = self.root/'baseline.json'
        self.p.write_text(json.dumps(policy(regressions={'input_tokens':{'relative':0,'absolute':0}})))
        self.assertEqual(self.cli('check',self.p,self.traces).returncode,2)
        self.assertEqual(self.cli('baseline',self.p,self.traces,'--output',baseline).returncode,0)
        self.assertEqual(self.cli('check',self.p,self.traces,'--baseline',baseline).returncode,0)

    def test_output_cannot_overwrite_inputs(self):
        before = self.traces.read_bytes()
        result = self.cli('check',self.p,self.traces,'--json-report',self.traces)
        self.assertEqual(result.returncode,2)
        self.assertEqual(self.traces.read_bytes(),before)

    def test_invalid_resource_limits(self):
        result = self.cli('check',self.p,self.traces,'--max-spans','0')
        self.assertEqual(result.returncode,2)
