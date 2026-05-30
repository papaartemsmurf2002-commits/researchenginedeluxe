# WPR106-21 Full Repo Data Code Crosscheck

Status: closed

## Scope

Run a stage-governed full repo audit on current `main`, treating it as the
migrated R106 branch. This packet is audit/report only; it must not edit
research code, configs, fixtures, generated artifacts, live runtime behavior,
or candidate-pack outputs.

The audit answers:

- whether the R106-required BTCUSDT/ETHUSDT data is present, reproducible, and
  correctly labeled research-only;
- whether all provider surfaces are truthfully represented, including inactive
  expansion providers;
- whether the codebase is clean, efficient, and boundary-safe enough for the
  next empirical R106 work.

## Allowed paths

- `docs/work_packets/WPR106-21-full-repo-data-code-crosscheck.md`
- `docs/stage_reports/STAGE_R106_FULL_REPO_DATA_CODE_CROSSCHECK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

`docs/KNOWN_ISSUES.md` may be changed only if a new blocking or tracked issue
is discovered.

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Do not regenerate, rewrite, or normalize fixture packs, catalog artifacts,
  cycle outputs, discovery ledgers, or generated specs in this packet.
- Do not make candidate-ready performance, profitability, promotion, or live
  readiness claims.
- Treat current `main` as the migrated R106 branch, while documenting the stale
  branch-name mismatch in stage docs.

## Acceptance

- Stage report states whether R106 candidate-depth data is present for BTCUSDT
  and ETHUSDT.
- Stage report lists remaining empirical gates before candidate-ready claims.
- Stage report classifies Binance Vision, Binance REST, Crypto Lake, Bybit
  archive, and Hyperliquid archive provider surfaces.
- Stage report records validation commands and outcomes.
- Any new P0/P1 blocker is added to `docs/KNOWN_ISSUES.md`; lower-severity debt
  is recorded only if it materially affects handoff.
- No source/runtime behavior or generated research evidence is changed.

## Planned validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\historical -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\live -q`

## Closeout

- Validated the current checkout mirror of the active R106 historical-data
  catalog and BTCUSDT/ETHUSDT candidate-depth fixture manifests.
- Confirmed both symbols are durable-public-archive ready in the current
  checkout mirror, with required `15m` bars, `1m` lower-timeframe bars, and
  aggTrade trade-flow proxy evidence.
- Classified all registered provider surfaces and confirmed inactive providers
  remain truthfully non-active for candidate-depth evidence.
- Registered `ISSUE-R106-003` for active catalog handoff drift: stale absolute
  paths outside this checkout and missing local modern-window profile artifacts.
- Static scans found no new live-boundary, order-placement, runtime-mode,
  sizing, or unsafe promotion-readiness regression.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\historical -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\live -q`
