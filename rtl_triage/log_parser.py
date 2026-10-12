"""Deterministic parsing for common Verilog/SystemVerilog diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any


@dataclass
class Finding:
    category: str
    severity: str
    message: str
    source_file: str | None = None
    line: int | None = None
    context: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_LOCATION = re.compile(r"(?P<file>[\w./\\-]+\.(?:svh?|vh?|v))(?::|\()(?P<line>\d+)")
_RULES = [
    ("syntax_error", "error", re.compile(r"\b(syntax error|parse error|unexpected token|malformed statement)\b", re.I)),
    ("compilation_error", "error", re.compile(r"\b(error|fatal)\b.*\b(compile|compil|elaborat|iverilog|verilator)\b", re.I)),
    ("width_mismatch", "warning", re.compile(r"\b(width mismatch|truncat|too few bits|too many bits|width)\b", re.I)),
    ("undeclared_identifier", "error", re.compile(r"\b(undeclared|not declared|unknown identifier|unresolved)\b", re.I)),
    ("assertion_failure", "error", re.compile(r"\b(assertion|assert)\b.*\b(fail|error|violat)", re.I)),
    ("fatal_error", "error", re.compile(r"\bsimulation fatal\b|\bfatal error\b|\b\$fatal\b", re.I)),
    ("timeout", "error", re.compile(r"\b(timeout|timed out|watchdog)\b", re.I)),
]


def _context(rtl_lines: list[str] | None, line: int | None, radius: int = 2) -> list[str] | None:
    if not rtl_lines or line is None or line < 1 or line > len(rtl_lines):
        return None
    start = max(1, line - radius)
    end = min(len(rtl_lines), line + radius)
    return [f"{number}: {rtl_lines[number - 1]}" for number in range(start, end + 1)]


def parse_log(log_text: str, rtl_path: str | Path | None = None) -> list[Finding]:
    """Parse log text without raising on empty or malformed input."""
    if not log_text or not log_text.strip():
        return []
    rtl_lines: list[str] | None = None
    if rtl_path:
        try:
            rtl_lines = Path(rtl_path).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            rtl_lines = None

    findings: list[Finding] = []
    for raw_line in log_text.splitlines():
        text = raw_line.strip()
        if not text:
            continue
        location = _LOCATION.search(text)
        source_file = location.group("file") if location else None
        line = int(location.group("line")) if location else None
        matched = False
        for category, severity, pattern in _RULES:
            if pattern.search(text):
                findings.append(Finding(category, severity, text, source_file, line, _context(rtl_lines, line)))
                matched = True
                break
        if not matched and re.search(r"\b(error|warning|fatal|fail(?:ed|ure)?|timeout)\b", text, re.I):
            findings.append(Finding("unknown", "error", text, source_file, line, _context(rtl_lines, line)))
    return findings


def summarize_findings(findings: list[Finding]) -> str:
    if not findings:
        return "No recognizable diagnostics were found in the log."
    return "\n".join(
        f"- {finding.category} ({finding.severity})"
        f"{f' at {finding.source_file}:{finding.line}' if finding.source_file and finding.line else ''}: "
        f"{finding.message}"
        for finding in findings
    )
