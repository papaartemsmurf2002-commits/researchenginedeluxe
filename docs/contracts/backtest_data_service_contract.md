# V2 Backtest Data Service Contract

Status: v2 Phase 9 service contract with Phase 19 cross-venue fixture support and explicit durable load-worker support
Audit IDs: `V2-AUD-BTDATA-001`, `V2-AUD-BTDATA-005`, `V2-AUD-XVENUE-001`

## Purpose

The backtest data service is the only accepted read path for v2 backtests.

## Schema Names

- `BacktestDataRequest`
- `BacktestDataManifest`
- `BacktestDataSlice`
- `BacktestEvidenceMode`
- `LockboxPolicy`
- `ValidationConfig`
- `BacktestCoverageGate`

## Required Rules

- Start date must be on or after 2024-01-01 for accepted evidence.
- Usable history must be at least 6 months; 12 months are preferred.
- Dynamic latest full-calendar-month lockbox must be excluded from ordinary
  iteration.
- Coverage must be at least 0.98.
- Accepted evidence requires as-of universe and archive snapshot IDs.
- Requests overlapping lockbox fail before strategy code runs.
- Backtest-data reads must call the coverage gate before strategy code can see
  the requested panel.
- Coverage reports with `sandbox_diagnostic_non_evidence`, failed quality
  status, blocker reasons, or coverage below `0.98` must fail accepted-evidence
  reads.
- `load_panel` reads only from local silver archive Parquet files included in
  the referenced archive snapshot.
- The service may read internal timestamp fields needed for filtering, but the
  returned panel must expose only `requested_fields`.
- Warmup rows may be loaded before `start_ts`, but usable-month checks and
  reported PnL counts use only `[start_ts, end_ts)`.
- Each successful request returns and records a deterministic
  `BacktestDataManifest` with archive snapshot, universe snapshot, coverage
  report, source file IDs, loaded fields, and row counts.
- Durable `backtest_data_load` worker jobs must create a
  `BacktestDataRequest` from declared worker input, require
  `write_manifest=true`, call `BacktestDataService.load_panel()`, write the
  canonical backtest-data manifest, and surface archive snapshot, universe
  snapshot, coverage report, data manifest, manifest path, and manifest hash
  refs for later bounded-cycle bindings.
- Current universe snapshots are allowed only when
  `BacktestEvidenceMode.sandbox_diagnostic` is requested. Accepted/reported
  evidence must use `UniverseMode.as_of`.
- Non-Hyperliquid venue rows may be loaded only when the archive snapshot,
  universe snapshot, coverage report, silver file manifest, and requested venue
  all agree on the same explicit venue and instrument provenance.
- Cross-venue bars and funding rows must preserve venue and instrument fields
  in the silver table and may expose them only when explicitly requested.
- Funding-family reads use the same local silver archive, coverage, universe,
  and lockbox gates as bar-family reads.
- Hyperliquid remains the default universe and venue unless a request explicitly
  asks for another venue with matching v2 manifests.

## Forbidden

- Direct venue/API reads from backtests.
- Current-universe accepted evidence.
- Silent fallback to synthetic data.
- Bypassing coverage reports or treating sandbox diagnostics as accepted
  evidence.
- Treating durable backtest-data load refs as strategy performance,
  validation, ledger, Lead Book, accepted research, or readiness evidence by
  themselves.
- Returning unrequested columns to downstream strategy code.
- Counting warmup rows as reported PnL-window rows.
- Falling back from one venue to another venue when a cross-venue request has no
  matching files, universe rows, or coverage reports.
