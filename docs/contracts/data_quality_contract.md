# V2 Data Quality Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-QUAL-001`, `V2-AUD-QUAL-004`

## Purpose

Data quality reports determine whether archive slices can support accepted
research evidence.

## Initial Schema Names

- `CoverageReport`
- `DataQualityCheck`
- `CoverageManifestStore`

## Required Rules

- Default accepted-evidence coverage minimum is `0.98`.
- Reports include expected rows, observed rows, coverage ratio, gaps,
  duplicates, stale segments, outliers, parse failures, and source caveats.
- Quality failures are blocker evidence, not hidden warnings.
- Coverage is scoped by venue, instrument, family, timeframe, and time range.
- Bar coverage uses deterministic expected-row calculators by timeframe and a
  `[start_ts, end_ts)` window.
- Coverage ratio uses unique observed timestamps so duplicates cannot inflate
  coverage.
- Missing days must be reported explicitly in `missing_days`.
- Coverage manifests are stored as local archive manifest Parquet tables and
  must be queryable by venue, instrument, date, family, and timeframe.
- Accepted or reported evidence below `0.98` must include
  `coverage_below_minimum` and must not be evidence eligible.
- Sandbox diagnostics with insufficient coverage are allowed only when labeled
  `sandbox_diagnostic_non_evidence`.
- `redx data coverage` and `redx data quality-report` read local archive or
  fixture files only; they do not fetch venue data and do not run strategies.
- Phase 8 silver bar builds must write/update coverage manifests for generated
  silver bar files.
- Archive snapshots that include silver bars should include coverage and
  quality manifest hashes when available.
- Durable `coverage_audit` worker jobs read local archive manifest rows and
  silver bar Parquet files only.
- Coverage-audit worker outputs must write coverage and quality-check
  manifests and return coverage report IDs, quality-check IDs, coverage ratio,
  quality status, evidence eligibility, and blocker reasons.
- A successful coverage-audit job can report low coverage or quality blockers;
  those blockers are research evidence and must not be hidden as worker-system
  failures.
- Coverage-audit worker jobs may audit an `archive_snapshot_id` against a
  `universe_snapshot_id` for a declared timeframe. In that mode the job must
  read only local archive/universe manifests and silver bars, write one
  coverage report per in-scope universe instrument, and surface missing silver
  bar files as blocker evidence instead of silently dropping instruments.

## Forbidden

- Treating missing context as zero.
- Promoting diagnostic/latest-window data to accepted evidence by omission.
- Counting duplicate timestamps as extra coverage.
- Silently repairing gaps, stale rows, zero-volume rows, or outliers without
  provenance.
- Building derived timeframe coverage while omitting incomplete-window evidence.
- Running coverage-audit worker jobs on non-silver-bars files or direct venue
  fetches.
