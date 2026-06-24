# V2 Data Quality Contract

Status: v2 contract foundation
Audit IDs: `V2-AUD-QUAL-001`, `V2-AUD-QUAL-004`, `V2-AUD-QUAL-006`

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
- Timestamped non-bar coverage for raw `trades`, raw `bbo`, raw `l2`, and
  silver `asset_contexts` uses a declared bucket timeframe and counts unique
  nonempty `[start_ts, end_ts)` buckets rather than event rows.
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
- Coverage-audit worker jobs may also audit timestamped raw microstructure
  (`trades`, `bbo`, `l2`) or silver `asset_contexts` files directly or by
  archive snapshot plus universe snapshot. Missing per-instrument files must be
  blocker evidence.
- Raw microstructure bucket coverage is measurement evidence only and must
  remain non-evidence by default with an explicit caveat until a later packet
  proves continuous source coverage and any required queue/fill realism.
- Historical-perps collection reports may include `technical_coverage_pass`
  for collected candle slices when coverage ratio meets the configured floor
  and duplicates/parse failures are absent. That technical pass is archive data
  quality only; reports must still set `accepted_research_ready=false` when the
  universe is current-public rather than historical as-of.

## Forbidden

- Treating missing context as zero.
- Promoting diagnostic/latest-window data to accepted evidence by omission.
- Counting duplicate timestamps as extra coverage.
- Silently repairing gaps, stale rows, zero-volume rows, or outliers without
  provenance.
- Building derived timeframe coverage while omitting incomplete-window evidence.
- Running coverage-audit worker jobs on unsupported file families or direct
  venue fetches.
- Treating raw trades/BBO/L2 bucket coverage as proof of event completeness,
  volume completeness, queue/fill realism, accepted evidence, live execution,
  paper trading, order readiness, or promotion readiness.
