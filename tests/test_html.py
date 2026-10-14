from html.parser import HTMLParser
import unittest

from spanverdict.engine import evaluate
from spanverdict.html_report import html_report
from spanverdict.otlp import parse_batches
from helpers import run
from test_policy import policy


class TagReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag,dict(attrs)))


class HtmlTests(unittest.TestCase):
    def test_script_free_report_has_no_remote_assets(self):
        html = html_report(evaluate(policy(),parse_batches([run()])))
        reader = TagReader()
        reader.feed(html)
        self.assertFalse(any(tag in ('script','img','iframe','link') for tag,_ in reader.tags))
        self.assertIn('Content-Security-Policy',html)
        self.assertIn('Recorded runs meet the contract.',html)

    def test_failure_details_visible_and_unmeasured_not_zero(self):
        html = html_report(evaluate(policy(cases=['refund','faq'],limits={'input_tokens':1}),parse_batches([run()])))
        self.assertIn('This release needs attention.',html)
        self.assertIn('Unmeasured',html)
        self.assertIn('<details open>',html)

    def test_metadata_is_escaped_even_for_api_generated_results(self):
        result = evaluate(policy(),parse_batches([run()]))
        result['name'] = '<script>alert(1)</script>'
        html = html_report(result)
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
