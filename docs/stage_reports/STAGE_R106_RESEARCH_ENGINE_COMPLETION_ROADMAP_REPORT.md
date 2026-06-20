# Stage R106 Research Engine Completion Roadmap Report

Date: 2026-06-20
Packet: `WPR106-360-research-engine-completion-roadmap`

## Summary

WPR106-360 adds
`docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` as the authoritative
research-only roadmap for finishing ResearchEngineDeluxe. The roadmap starts
from the current dirty-tree and targeted red-test reality, makes Phase 0
repo-state stabilization mandatory, and only then sequences sandbox
safety/provenance repairs, local venue-expansion materialization, closed-loop
smoke evidence, strict-validation descriptor preflight, performance proof, and
reviewable delivery.

This packet is documentation-only. It does not implement future commands or
change sandbox, backtest, discovery, archive, candidate-pack, live, paper,
sizing, order, runtime, or promotion behavior.

## Files Updated

- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-360-research-engine-completion-roadmap.md`
- `docs/stage_reports/STAGE_R106_RESEARCH_ENGINE_COMPLETION_ROADMAP_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_search_space_expansion.py::test_holding_window_search_space_includes_metadata_and_window_defaults -q`
  failed as expected from the audit: `spacing_bars` currently returns
  `(4, 8, 12, 16)` instead of the test expectation `(8, 12, 16)`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration -q`
  failed as expected from the audit: the manifest reports
  `counts.completed_trials == 1` after resume state recovered two completed
  trial IDs.
- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed with
  461 tests passing.
- `git diff --check` passed with only existing LF-to-CRLF working-copy warnings.

The targeted failures are not introduced by this documentation packet. They
remain Phase 0 repair requirements in the roadmap.

## Boundary Statement

No candidate pack, paper/live artifact, order-placement behavior, sizing
instruction, runtime-mode change, live configuration write, provider download,
archive manifest/source mutation, strict-validation execution, or promotion
claim was created by this packet.

