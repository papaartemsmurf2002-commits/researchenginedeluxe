# V2 Data Quality Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-QUAL-001`, `V2-AUD-QUAL-002`

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

## Forbidden

- Treating missing context as zero.
- Promoting diagnostic/latest-window data to accepted evidence by omission.
- Counting duplicate timestamps as extra coverage.
- Silently repairing gaps, stale rows, zero-volume rows, or outliers without
  provenance.
- Building derived timeframe coverage while omitting incomplete-window evidence.
