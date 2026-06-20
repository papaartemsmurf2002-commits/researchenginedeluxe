# WPR106-229 Rapid Strategy Sandbox CLI And Archive Loader

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the WPR106-228 Rapid Strategy Iteration Sandbox runnable from the canonical
CLI using local 2024+ market data and strategy/venue descriptor files. Add a
research-only workflow path that loads normalized archive-backed market frames,
parses sandbox run specs, runs vectorized fixed-hold sweeps, and writes compact
Parquet/JSON sandbox artifacts under the configured research output root.

This packet is still sandbox-only. It does not add operator UI wiring, network
downloads, candidate-pack writes, live/paper signals, sizing, order placement,
runtime-mode changes, or promotion behavior.

## Scope

- Add sandbox market-frame loading for local CSV, TSV, JSON, JSONL, Parquet, and
  simple Binance Vision kline ZIP/CSV archive files.
- Add sandbox run-spec loading from JSON and preserve the hard `2024-01-01`
  minimum data-window rule.
- Add a `run-rapid-strategy-sandbox` CLI command that:
  - is registered as a research command;
  - rejects live mode through the existing preflight guard;
  - resolves output directories under the configured research output root;
  - loads strategy catalogs and venue archive descriptors;
  - runs the sandbox sweep and prints artifact paths/counts as JSON.
- Add focused tests for loader behavior, CLI output-root enforcement, live-mode
  registration, and end-to-end CLI command execution with local files.
- Update the sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-229-rapid-strategy-sandbox-cli-and-archive-loader.md`
- `docs/stage_reports/STAGE_R106_RAPID_STRATEGY_SANDBOX_CLI_AND_ARCHIVE_LOADER_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- CLI command `run-rapid-strategy-sandbox` appears in the research command
  registry and boundary contract.
- The command rejects output paths outside `TBS_RESEARCH_OUTPUT_DIR`.
- Local market-frame loader supports normalized CSV/TSV/JSON/JSONL/Parquet and
  Binance Vision kline ZIP/CSV rows.
- Loaded market rows are timestamp-sorted and compatible with existing sandbox
  fixed-hold sweep inputs.
- End-to-end CLI command writes a manifest, summary Parquet, rankings Parquet,
  evidence-request JSON, and evidence-request Parquet.
- All outputs remain `research_only`, `observe_only`, `promotion_ready: false`,
  `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, CLI boundary tests touched by the
  command, package compile, and contract baseline.

## Boundary

The CLI only runs local sandbox triage. It does not download venue data, place
orders, write live configuration, create candidate packs, or bypass strict
candidate gates. Evidence requests are descriptors for later validation only.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added local market-frame
loaders, sandbox run-spec parsing, the `run-rapid-strategy-sandbox` CLI command,
research-command registry coverage, boundary-contract coverage, and focused
tests for loader and CLI behavior.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 13 sandbox tests passed, 8 CLI boundary tests passed, 11
import-boundary tests passed, package compile passed, and 461 contract tests
passed. The first contract run hit a transient Windows socket/event-loop setup
error (`WinError 10055`) before a test body ran; an immediate rerun passed.
