# RTL Triage Agent

An independent, small MVP that parses Verilog/SystemVerilog compiler or
simulation logs, optionally requests a structured diagnosis through the OpenAI
Responses API, saves any model-generated RTL separately, and performs a safe
best-effort lint/elaboration check.

## Setup

From this directory, optionally create a virtual environment and install
`python -m pip install -r requirements.txt`. Set `OPENAI_API_KEY` (and
optionally `OPENAI_MODEL`) only for online diagnosis. Credentials are never
printed or committed.

## Commands

```text
python run_agent.py --help
python run_agent.py --rtl examples/broken_counter.v --log examples/failing_sim.log --offline
python run_agent.py --rtl examples/broken_counter.v --log examples/failing_sim.log --outdir output
python -m unittest discover -s tests -v
```

Offline mode is deterministic, needs no API key, parses the log, and does not
generate or claim a repair. Online mode uses `client.responses.create`, asks
for structured JSON, and treats candidate RTL as an untrusted proposal.

## Output and validation

The output directory contains `triage_report.md` and, only when the model
returns candidate RTL, `<input>.proposed.v` (or the input suffix). The original
RTL is never modified. Icarus Verilog (`iverilog`) is preferred; otherwise
Verilator is detected. Validation is a syntax/elaboration or lint check only:
passing compilation does not prove simulation success or functional correctness.
If neither tool is installed, the report explicitly says validation was skipped.

## Limitations and troubleshooting

The parser is heuristic and intentionally handles common diagnostics rather
than every simulator's format. There is no waveform analysis, testbench
execution, automated patch acceptance, Anthropic integration, Slurm support, or
regression hook. Online calls require a compatible OpenAI SDK and valid
credentials. A malformed model response is rejected. Check the report for
validation status and preserve the proposed source for manual review.

See [UPSTREAM_ATTRIBUTION.md](UPSTREAM_ATTRIBUTION.md) for research inspiration
and attribution.
