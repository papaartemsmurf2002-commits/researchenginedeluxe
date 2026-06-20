# WPR106-379 - Sandbox Source Discovery Bounds

## Status

closed

## Objective

Close the post-audit M5 discovery-cost gap for the sandbox by replacing
full-tree recursive sorting in strategy catalog materialization, archive
manifest building, and global leaderboard run discovery with deterministic
bounded traversal that stops after the configured limit.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`
- `docs/work_packets/WPR106-378-sandbox-workbook-intake-bounds-and-xls-policy.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/discovery.py`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `src/tradingbotsuite/research_sandbox/leaderboard.py`
- `src/tradingbotsuite/research_sandbox/strategy_catalog_materializer.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-379-sandbox-source-discovery-bounds.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_SOURCE_DISCOVERY_BOUNDS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve deterministic local traversal order for accepted small roots.
- Preserve explicit skipped-source and skipped-file repair rows.
- Preserve existing artifact schemas except for safer discovery behavior and
  related documentation.
- Do not add provider downloads, source mutation, sandbox sweep semantic
  changes, strict-validation execution, candidate-pack writes, paper/live
  behavior, sizing, order placement, runtime-mode changes, live config writes,
  candidate-evidence claims, or promotion claims.

## Acceptance criteria

- Strategy catalog materialization honors `max_files` without sorting the full
  recursive file tree.
- Archive manifest building honors `max_files` without sorting the full
  recursive file tree.
- Global leaderboard discovery honors `max_runs` without sorting all run
  manifests first.
- Bounded traversal remains deterministic by sorting entries within each
  directory only.
- Focused tests prove truncation and deterministic first-N behavior for all
  three discovery paths.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "discovery_bound or max_files or max_runs" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --check
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "discovery_bound" -q`
  - `3 passed, 195 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `219 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`

## Stop conditions

- Traversal becomes non-deterministic for the same local directory tree.
- Source rows or manifest rows disappear without an explicit truncated flag.
- The change requires broad archive loading, backtest engine, or artifact
  schema rewrites.
