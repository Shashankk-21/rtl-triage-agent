"""Command-line entry point for the independent RTL Triage Agent MVP."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import os
import shutil
import sys

from rtl_triage.llm import request_diagnosis
from rtl_triage.log_parser import parse_log, summarize_findings
from rtl_triage.validator import validate_rtl


def _offline_diagnosis(findings: list) -> dict:
    categories = ", ".join(dict.fromkeys(item.category for item in findings)) or "no recognized category"
    return {
        "classification": categories,
        "root_cause": "Deterministic triage identified the categories above from the supplied log; no AI diagnosis was performed.",
        "remediation": "Inspect the referenced RTL lines and address the reported diagnostic. No repair was generated in offline mode.",
        "candidate_rtl": None,
        "uncertainties": "A simulator and functional testbench are required to establish behavior.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose Verilog/SystemVerilog failures safely.")
    parser.add_argument("--rtl", required=True, help="Input Verilog/SystemVerilog source.")
    parser.add_argument("--log", required=True, help="Simulation/compiler log.")
    parser.add_argument("--outdir", default="output", help="Directory for report and proposed source.")
    parser.add_argument("--offline", action="store_true", help="Skip the OpenAI API and produce deterministic triage.")
    args = parser.parse_args(argv)
    rtl_path, log_path, outdir = Path(args.rtl), Path(args.log), Path(args.outdir)
    if not rtl_path.is_file():
        parser.error(f"RTL file does not exist: {rtl_path}")
    if not log_path.is_file():
        parser.error(f"log file does not exist: {log_path}")
    try:
        rtl = rtl_path.read_text(encoding="utf-8", errors="replace")
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        parser.error(str(exc))
    findings = parse_log(log, rtl_path)
    parsed = summarize_findings(findings)
    try:
        diagnosis = _offline_diagnosis(findings) if args.offline else request_diagnosis(rtl, log, parsed)
    except RuntimeError as exc:
        print(f"LLM diagnosis unavailable: {exc}", file=sys.stderr)
        return 2
    outdir.mkdir(parents=True, exist_ok=True)
    candidate = diagnosis.get("candidate_rtl")
    candidate_path: Path | None = None
    if args.offline:
        validation_text = "Skipped: offline mode did not generate a candidate RTL file."
        if not (shutil.which("iverilog") or shutil.which("verilator")):
            validation_text += " No Icarus Verilog or Verilator executable was found."
    else:
        validation_text = "Skipped: no candidate RTL was returned by the model."
    if isinstance(candidate, str) and candidate.strip():
        candidate_path = outdir / f"{rtl_path.stem}.proposed{rtl_path.suffix}"
        candidate_path.write_text(candidate, encoding="utf-8")
        result = validate_rtl(candidate_path)
        validation_text = f"{result.detail} Status: {result.status}. Tool: {result.tool or 'none'}.\n"
        if result.stdout or result.stderr:
            validation_text += f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    report_path = outdir / "triage_report.md"
    report = f"""# RTL Triage Report

## Input
- RTL: `{rtl_path}`
- Log: `{log_path}`
- Mode: {"offline" if args.offline else "OpenAI Responses API"}

## Parsed findings
{parsed}

## Diagnosis
- Classification: {diagnosis["classification"]}
- Root cause: {diagnosis["root_cause"]}
- Proposed remediation: {diagnosis["remediation"]}
- Uncertainties: {diagnosis["uncertainties"]}

## Patch status
{"Proposed RTL written to `" + str(candidate_path) + "`. It is not trusted or automatically applied." if candidate_path else "No candidate RTL was generated."}

## Validation
{validation_text}

Compilation/lint success does not establish simulation success or functional correctness.
"""
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written: {report_path}")
    if candidate_path:
        print(f"Proposed RTL written: {candidate_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
