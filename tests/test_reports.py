import os
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

from spanverdict.engine import evaluate
from spanverdict.otlp import parse_batches
from spanverdict.reports import OutputError, atomic_write, json_report, junit_report, protect_destinations
from helpers import attr, raw_spans, run
from test_policy import policy


class ReportTests(unittest.TestCase):
    def test_atomic_overwrite_and_exclusive_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'reports'/'out.json'
            atomic_write(path,'first',overwrite=False)
            with self.assertRaises(OutputError):
                atomic_write(path,'second',overwrite=False)
            self.assertEqual(path.read_text(),'first')
            atomic_write(path,'second')
            self.assertEqual(path.read_text(),'second')
            self.assertFalse(list(path.parent.glob('.spanverdict-*')))

    def test_protected_input_and_report_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'traces'
            source.write_text('original')
            with self.assertRaises(OutputError):
                atomic_write(source,'bad',protected=[source])
            with self.assertRaises(OutputError):
                protect_destinations([source,source])
            alias = Path(directory)/'alias'
            os.link(source,alias)
            with self.assertRaises(OutputError):
                atomic_write(alias,'bad',protected=[source])
            self.assertEqual(source.read_text(),'original')

    @unittest.skipIf(os.name == 'nt','Symlink creation can require Windows developer mode')
    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source'
            source.write_text('original')
            alias = Path(directory)/'alias'
            alias.symlink_to(source)
            with self.assertRaises(OutputError):
                atomic_write(alias,'bad')

    def test_junit_contains_all_failures_and_no_prompts(self):
        value = run()
        raw_spans(value)[1]['attributes'].append(attr('gen_ai.input.messages','SECRET-PROMPT'))
        result = evaluate(policy(cases=['refund','faq'],limits={'input_tokens':1}),parse_batches([value]))
        xml = junit_report(result)
        root = ET.fromstring(xml)
        self.assertEqual(root.attrib['tests'],'3')
        self.assertEqual(root.attrib['failures'],'2')
        self.assertNotIn('SECRET-PROMPT',xml+json_report(result))
