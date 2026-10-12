import tempfile
import unittest
from pathlib import Path

from rtl_triage.log_parser import parse_log


class LogParserTests(unittest.TestCase):
    def test_categories_locations_and_context(self):
        with tempfile.TemporaryDirectory() as directory:
            rtl = Path(directory) / "x.v"
            rtl.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
            findings = parse_log(
                "x.v:3: syntax error\nx.v:4: warning: width mismatch\n"
                "x.v:5: undeclared identifier foo\nSIM: assertion failed\nSIM: timeout\n"
                "compiler: mystery error\n",
                rtl,
            )
        self.assertEqual([f.category for f in findings], ["syntax_error", "width_mismatch", "undeclared_identifier", "assertion_failure", "timeout", "unknown"])
        self.assertEqual(findings[0].line, 3)
        self.assertTrue(findings[0].context)

    def test_empty_and_missing_rtl_are_safe(self):
        self.assertEqual(parse_log(""), [])
        findings = parse_log("missing.v:2: syntax error", "does-not-exist.v")
        self.assertIsNone(findings[0].context)
