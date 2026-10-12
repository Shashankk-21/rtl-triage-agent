"""Safe, best-effort RTL candidate validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass
class ValidationResult:
    status: str
    tool: str | None
    command: list[str] | None
    stdout: str
    stderr: str
    detail: str


def validate_rtl(rtl_file: str | Path, timeout: int = 15) -> ValidationResult:
    """Lint/elaborate a candidate using an installed simulator, never a shell."""
    path = Path(rtl_file)
    tool = shutil.which("iverilog") or shutil.which("verilator")
    if not tool:
        return ValidationResult("skipped", None, None, "", "", "No Icarus Verilog or Verilator executable was found.")
    name = Path(tool).name.lower()
    command = [tool, "-g2012", "-tnull", str(path)] if name.startswith("iverilog") else [tool, "--lint-only", "-Wall", str(path)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ValidationResult("failed", name, command, "", str(exc), "Validator could not complete.")
    status = "passed" if completed.returncode == 0 else "failed"
    detail = "Compilation/lint check passed." if status == "passed" else "Compilation/lint check failed."
    return ValidationResult(status, name, command, completed.stdout, completed.stderr, detail)
