# Work Packet: WP1-02-tradingview-archive-map

Stage: Stage 1 - Repo cartography
Owner agent: Documentation Agent
Reviewer agent: Orchestrator Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_1_EXIT_REPORT.md`

Forbidden paths:

- `src/**`
- `tests/**`
- `configs/**`
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Classify TradingView, Pine, marker-parity, and chart-export material without moving code in Stage 1.

## Required source files to read first

- `README.md`
- `tests/test_removed_source_boundaries.py`
- `src/tradingbot/**`
- `docs/tradingbotsuite_runtime/**`

## Implementation tasks

- Identify removed TradingView/parity surfaces.
- Identify remaining legacy references.
- Identify active LC/reference modules that are not TradingView parity commands.
- Define archive recommendations for Stage 2 documentation.

## Tests and validation commands

```powershell
git grep -n "TradingView\|Pine\|parity\|tv_\|lorentz_tv\|features_tv\|kernels_tv\|lc_marker" research/v3-experimental-engine -- .
$env:PYTHONPATH='src'; python -m pytest tests/test_removed_source_boundaries.py -q
```

## Acceptance evidence

- `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`
- `docs/stage_reports/STAGE_1_EXIT_REPORT.md`

## Handoff notes

The research branch already removed the active TradingView source pipeline. Remaining references are mostly historical docs, label names, and removed-source boundary tests.
