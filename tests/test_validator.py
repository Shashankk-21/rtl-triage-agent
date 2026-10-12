import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rtl_triage.validator import validate_rtl


class ValidatorTests(unittest.TestCase):
    def test_skips_without_simulator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.v"
            path.write_text("module x; endmodule\n", encoding="utf-8")
            with patch("rtl_triage.validator.shutil.which", return_value=None):
                result = validate_rtl(path)
        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.tool)

    def test_successful_safe_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.v"
            path.write_text("module x; endmodule\n", encoding="utf-8")
            with patch("rtl_triage.validator.shutil.which", return_value="iverilog.exe") as which:
                with patch("rtl_triage.validator.subprocess.run") as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = "ok"
                    run.return_value.stderr = ""
                    result = validate_rtl(path)
        self.assertEqual(result.status, "passed")
        self.assertEqual(run.call_args.kwargs["check"], False)
        self.assertNotIn("shell", run.call_args.kwargs)
        which.assert_called()

    def test_failed_subprocess_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.v"
            path.write_text("bad\n", encoding="utf-8")
            with patch("rtl_triage.validator.shutil.which", return_value="iverilog"):
                with patch("rtl_triage.validator.subprocess.run") as run:
                    run.return_value.returncode = 1
                    run.return_value.stdout = ""
                    run.return_value.stderr = "syntax error"
                    result = validate_rtl(path)
        self.assertEqual(result.status, "failed")
        self.assertIn("syntax error", result.stderr)
