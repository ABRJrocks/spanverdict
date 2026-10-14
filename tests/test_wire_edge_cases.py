import json
from pathlib import Path
import tempfile
import unittest

from spanverdict import InputError, load_spans
from spanverdict.jsonio import decode
from helpers import attr, batch, span


class WireEdgeTests(unittest.TestCase):
    def test_unicode_line_separator_in_ignored_prompt_is_not_a_batch_boundary(self):
        value = span(op='chat',tokens=(10,10))
        value['attributes'].append(attr('gen_ai.input.messages','before\u2028after\u0085end'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'traces.jsonl'
            path.write_text(json.dumps(batch(value),ensure_ascii=False)+'\n',encoding='utf-8')
            self.assertEqual(len(load_spans(path)),1)

    def test_crlf_and_optional_final_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'traces.jsonl'
            for ending in ('','\n','\r\n'):
                path.write_bytes((json.dumps(batch(span()))+ending).encode())
                self.assertEqual(len(load_spans(path)),1)

    def test_numeric_exponent_overflow(self):
        with self.assertRaises(InputError):
            decode('{"value":1e9999}')

    def test_empty_and_internal_blank_lines_block(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'traces.jsonl'
            for text in ('','\n',json.dumps(batch(span()))+'\n\n'):
                path.write_text(text)
                with self.assertRaises(InputError):
                    load_spans(path)
