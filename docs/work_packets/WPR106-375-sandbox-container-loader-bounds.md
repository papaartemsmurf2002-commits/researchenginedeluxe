# WPR106-375 - Sandbox Container Loader Bounds

## Status

closed

## Objective

Add bounded-read guardrails to sandbox ZIP/TAR market-data container loading so
large or compressed local archive members fail closed with explicit loader
blockers instead of being read/decompressed without limits.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-372-sandbox-throughput-telemetry-report.md`
- `docs/work_packets/WPR106-374-sandbox-catalog-exit-profile-semantics.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/market_data.py`
- `tests/research_sandbox/test_market_data_container_limits.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-375-sandbox-container-loader-bounds.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_LOADER_BOUNDS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve local-only archive loading; do not add provider downloads or source
  archive mutation.
- Preserve 2024+ normalization/filtering and source-integrity behavior for
  accepted inputs.
- Block unsafe oversized container reads with clear loader errors instead of
  silently truncating or fabricating evidence.
- Do not execute sweeps, strict validation, replay commands, candidate-pack
  writes, paper/live behavior, sizing, order placement, runtime mode changes,
  live config writes, candidate-evidence claims, or promotion claims.

## Acceptance criteria

- ZIP/TAR selected member count is bounded.
- ZIP/TAR selected member raw byte size and total selected raw byte size are
  bounded before member parsing.
- Gzip-compressed container members are decompressed through a bounded path.
- Oversized containers raise explicit `ValueError` messages that audit,
  preflight, and materializer paths can surface as blockers.
- Accepted container metadata records the active loader limits for
  reproducibility diagnostics.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_market_data_container_limits.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_market_data_container_limits.py -q`
  - `4 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `212 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `462 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Stop conditions

- The loader silently truncates data.
- The guard changes accepted small archive semantics.
- A failed oversized archive can still look like a successful sandbox result.
