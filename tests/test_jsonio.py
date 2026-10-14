import tempfile
import unittest
from pathlib import Path

from spanverdict.jsonio import InputError, decode, read_json, read_text


class JsonTests(unittest.TestCase):
    def test_duplicate_members(self):
        for value in ('{"a": 1, "a": 2}', '{"nested": {"a": 1, "a": 2}}'):
            with self.assertRaises(InputError):
                decode(value)

    def test_invalid_and_nonfinite(self):
        for value in ('NaN', 'Infinity', '-Infinity', '{', '\ufeff{}', '[' * 2000):
            with self.assertRaises(InputError):
                decode(value)

    def test_limits_and_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'{"a":1}')
            self.assertEqual(read_json(path), {"a": 1})
            with self.assertRaises(InputError):
                read_text(path, 6)
            path.write_bytes(b'\xff')
            with self.assertRaises(InputError):
                read_text(path)

    def test_errors_do_not_echo_input(self):
        with self.assertRaises(InputError) as error:
            decode('{"secret":"private-value", BAD}')
        self.assertNotIn('private-value', str(error.exception))
