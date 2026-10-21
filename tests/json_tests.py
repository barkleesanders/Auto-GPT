"""Original parser scenarios with provider responses supplied by fixtures."""

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
import json_parser


class TestParseJson(unittest.TestCase):
    def test_valid_json(self):
        self.assertEqual(
            json_parser.fix_and_parse_json('{"name":"John"}'), {"name": "John"}
        )

    def test_minor_error_requires_enabled_repair(self):
        with self.assertRaises(ValueError):
            json_parser.fix_and_parse_json('{"name":"John",}', False)

    def test_minor_error_with_provider_fixture(self):
        with patch.object(
            json_parser, "call_ai_function", return_value='{"name":"John"}'
        ):
            self.assertEqual(
                json_parser.fix_and_parse_json('{"name":"John",}'), {"name": "John"}
            )

    def test_major_error_with_provider_fixture(self):
        with patch.object(
            json_parser, "call_ai_function", return_value='{"name":"John"}'
        ):
            self.assertEqual(
                json_parser.fix_and_parse_json("BEGIN: name-John :END"),
                {"name": "John"},
            )

    def test_major_error_without_provider(self):
        with self.assertRaises(ValueError):
            json_parser.fix_and_parse_json("BEGIN: name-John :END", False)

    def test_leading_sentence(self):
        expected = {
            "command": {
                "name": "browse_website",
                "args": {"url": "https://example.com"},
            }
        }
        with patch.object(
            json_parser,
            "call_ai_function",
            side_effect=AssertionError("provider called"),
        ):
            self.assertEqual(
                json_parser.fix_and_parse_json(
                    "Leading sentence " + json.dumps(expected), False
                ),
                expected,
            )

    def test_failed_provider_repair_returns_original_text(self):
        with patch.object(json_parser, "call_ai_function", return_value="invalid"):
            self.assertEqual(json_parser.fix_and_parse_json("not json"), "not json")


if __name__ == "__main__":
    unittest.main()
