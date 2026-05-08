# WPR82-01 Candidate Pack Bridge

## Status

Closed.

## Owner

Codex Research Agent.

## Scope

Implement a research-only discovery candidate-pack eligibility bridge. The bridge
allows strict-gate discovery candidates to be evaluated against the existing
historical-cycle candidate-pack validator without changing, weakening, or
directly writing candidate packs.

## Allowed Paths

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `configs/discovery/**`
- `tests/research_discovery/**`
- `tests/live/test_preflight.py`
- `docs/work_packets/WPR82-01-candidate-pack-bridge.md`
- `docs/stage_reports/STAGE_R82_CANDIDATE_PACK_BRIDGE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Non-Goals

- Do not write research candidate packs from discovery code.
- Do not change `tradingbotsuite.research_artifacts.candidate_pack` gates.
- Do not change historical-cycle semantics or checked cycle configs.
- Do not create promotion-ready, live-signal, sizing, runtime, or order inputs.

## Exit Criteria

- Discovery bridge writes observe-only eligibility and rejection artifacts.
- Eligibility requires a completed discovery run and an existing historical-cycle
  manifest candidate that passes `evaluate_research_candidate_gate`.
- Discovery-only candidates fail closed with explicit reasons.
- The bridge CLI is registered as a research command and rejected in live
  preflight.
- Focused tests and baseline validation pass.

## Exit Evidence

- Added `tradingbotsuite.research_discovery.candidate_pack_bridge` to write
  observe-only eligibility and rejection artifacts.
- Added `evaluate-discovery-candidate-pack-eligibility` as an audit command and
  registered it as a research command for live-preflight rejection.
- Preserved existing candidate-pack ownership: the bridge does not call
  `write_research_candidate_pack` and always records `candidate_pack_written:
  false`.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
