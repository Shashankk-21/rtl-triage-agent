"""Optional OpenAI Responses API integration."""

from __future__ import annotations

import json
import os
from typing import Any


def request_diagnosis(rtl: str, log: str, findings: str, model: str | None = None) -> dict[str, Any]:
    """Request a structured diagnosis; errors are returned explicitly to the CLI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; use --offline for deterministic triage.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is not installed.") from exc
    schema = {
        "type": "object",
        "properties": {
            "classification": {"type": "string"},
            "root_cause": {"type": "string"},
            "remediation": {"type": "string"},
            "candidate_rtl": {"type": ["string", "null"]},
            "uncertainties": {"type": "string"},
        },
        "required": ["classification", "root_cause", "remediation", "candidate_rtl", "uncertainties"],
        "additionalProperties": False,
    }
    prompt = (
        "Diagnose this RTL failure. Return only JSON matching the schema. "
        "Do not claim a patch is validated. Link reasoning to source lines where possible.\n\n"
        f"RTL:\n{rtl[:100_000]}\n\nLOG:\n{log[:30_000]}\n\nPARSED FINDINGS:\n{findings}"
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt,
        text={"format": {"type": "json_schema", "name": "rtl_diagnosis", "schema": schema, "strict": True}},
    )
    try:
        result = json.loads(response.output_text)
    except (AttributeError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenAI returned a malformed structured response.") from exc
    if not isinstance(result, dict) or any(key not in result for key in schema["required"]):
        raise RuntimeError("OpenAI response did not match the required diagnosis shape.")
    return result
