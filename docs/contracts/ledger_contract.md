# V2 Ledger Contract

Status: v2 Phase 13 append-only ledger contract
Audit IDs: `V2-AUD-LEDGER-001`, `V2-AUD-LEDGER-004`,
`V2-AUD-LEDGER-005`

## Purpose

The canonical experiment ledger is append-only Parquet. CSV/XLSX are generated
views only.

## Initial Schema Names

- `LedgerRow`
- `LedgerAppendRequest`
- `LeaderboardRow`

## Required Rules

- Every passed, failed, rejected, and blocked trial can be logged.
- Ledger rows include run ID, hashes, archive/universe snapshots, cost model,
  validation status, net metrics, blocker reasons, and boundary metadata.
- Accepted-research appends enforce 2024+ start, at least 6 usable months,
  as-of universe mode, no lockbox overlap, validation status, and net metrics.
- If a ledger append supplies a `validation_manifest_path`, the ledger must
  validate the manifest schema, run ID, run-manifest SHA-256, pass/fail blocker
  consistency, and research boundary flags before using it as the authoritative
  source for validation status, walk-forward pass, validation blockers, fold
  summary fields, and cost-fragility warnings.
- Duplicate run IDs fail.
- Manual edits are rejected by hash/index validation.
- Canonical rows are written to Parquet with deterministic row hashes and
  ledger indexes.
- CSV and XLSX files are generated views from canonical Parquet only.
- Durable `ledger_append_export` worker jobs delegate row creation to
  `append_run_to_ledger`, preserve the duplicate-run and accepted-research
  gates, and may only write generated CSV/XLSX views after the canonical
  Parquet append succeeds.
- Leaderboards exclude sandbox/current-universe rows when requested and rank
  costed net results using the `composite_v1` report.
- Leaderboard rows include trial count, fold count, fold stability, and overfit
  warning fields when available from validation/ledger evidence.

## Forbidden

- Manual spreadsheet as source of truth.
- Hiding failed trials.
- Ignoring a bound validation gate manifest while logging a trial.
- Promotion-ready ledger rows.
- Gross-only leaderboard rows.
- Current-universe evidence claims in accepted-research mode.
- Leaderboards hiding trial-family size or fold instability.
