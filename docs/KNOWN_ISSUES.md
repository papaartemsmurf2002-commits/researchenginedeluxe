# Known Issues

Last updated: 2026-05-30

This registry is the blocking issue source for orchestrator stage gates.

Severity levels:

- P0: safety, data leakage, live trading risk, corrupt data, branch boundary violation.
- P1: invalid backtest assumption, non-deterministic experiment, broken artifact contract, severe performance blocker.
- P2: incomplete docs, minor missing tests, non-blocking refactor debt.
- P3: polish and convenience.

Stage advancement stop rule:

- Any open P0 blocks stage advancement.
- Four or more unresolved P1 issues block stage advancement.
- P2/P3 can carry forward only with explicit orchestrator note and owner.

## Current summary

| Severity | Open | In progress | Resolved | Accepted debt |
| --- | ---: | ---: | ---: | ---: |
| P0 | 0 | 0 | 1 | 0 |
| P1 | 1 | 0 | 15 | 0 |
| P2 | 0 | 0 | 2 | 0 |
| P3 | 0 | 0 | 1 | 0 |

## ISSUE-R104-001: Durable R104 fixtures are too compact for candidate-ready brute-force evidence

Severity: P1
Stage discovered: Stage R104 - candidate validation on durable evidence
Owner: Codex Research Agent
Status: open
Paths affected: `data/research/fixtures/**`, `configs/discovery/**`, `configs/research/**`, `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/research_cycle/**`

### Problem

The current BTCUSDT and ETHUSDT durable public-archive fixture packs are
checksum-verified and suitable for compact screening, but each pack contains
only 32 primary 15m bars. Deep discovery runs therefore complete with very low
trade counts and many fail-closed blockers such as
`independent_event_count_below_floor`, even when the search budget is expanded.
This is not a UI failure; it is insufficient primary-bar evidence for a
candidate-ready empirical claim.

### Evidence

R104 investigation found completed BTC/ETH durable historical cycles with 17
candidates each and all gates blocked. Latest discovery runs completed 360 to
5000 trials with zero current interesting candidates; the newest BTC deep run
blocked 5000/5000 rows and produced maximum trade counts near five. Feature
matrices from the compact fixtures have only 32 rows, causing long-window
feature columns and independent-event accounting to fail closed.

### Required resolution

Run the R106 Historical Data Catalog refresh for expanded BTCUSDT and ETHUSDT
public-archive fixture packs with materially more primary 15m bars, preserved
source archive hashes, checksum evidence, and provider capability metadata.
The catalog is the source of truth for active readiness, cycle, and discovery
spec paths. Rerun catalog readiness, then rerun the required deep historical
cycles and exact bounded discovery sweeps from the generated active specs.
Keep all artifacts `research_only`, `observe_only`, and
`promotion_ready: false` until candidate gates pass.

### Resolution notes

Open. WPR104-04 adds truthful brute-force-scale run profiles and UI/progress
wiring, but it does not fabricate additional durable data or claim candidate
readiness from the compact screening fixture. WPR105-104 hardens the operator
surface so the compact BTC/ETH fixtures are reported as integrity-ready
screening windows, not candidate-depth-ready evidence; old/simple artifacts no
longer complete the required checklist while this issue remains open.
WPR105-106 adds the missing runnable Step 0 collection pipeline and operator
button, validates Binance Vision checksum sidecars plus fixture integrity, and
wires generated candidate-depth packs into readiness, cycle, and discovery
defaults. This issue remains open until the full collection is run and the
resulting deep cycles, exact sweeps, and candidate eligibility review complete.
WPR106-01 supersedes the one-off button with the Historical Data Catalog as the
single required data source of truth and keeps Bybit, Crypto Lake, and
Hyperliquid provider slots visible without treating unimplemented ingestion as
candidate-depth evidence. WPR106-02 hardens the long-running catalog refresh
after a failed five-hour partial run: verified archive downloads are reusable
through a central cache, prior partial operator downloads can seed that cache,
collection progress is journaled with ETA, and generated fixture Parquet files
are streamed by archive partition to reduce memory pressure. It also hardens
operator job-log appends against queue/worker races that can crash the API with
duplicate log sequence inserts. WPR106-03 adds bounded transient Binance Vision
fetch retry and completed per-symbol fixture-pack reuse after interruption.
WPR106-04 expands that retry path for longer DNS/VPN outages with env-tunable
attempt and backoff defaults while keeping checksum mismatches fail-fast. The
issue remains open until the refreshed catalog, deep cycles, exact sweeps, and
eligibility review complete on candidate-depth evidence.

## ISSUE-R106-007: Large exact-discovery eligibility can stall before writing output

Severity: P1
Stage discovered: Stage R106 - candidate eligibility large-run stall
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/research_discovery/test_candidate_pack_bridge.py`

### Problem

The latest autopilot run remained `running` for about 16 hours after skipping
completed BTC/ETH prerequisite artifacts. It stopped logging immediately after
BTCUSDT `frozen_entry_exit_lab` and never created a
`candidate_pack_eligibility` output directory. The BTC exact-discovery run has
570,240 completed trial JSON records and 22,560 interesting candidates. The
eligibility bridge opened every completed trial JSON twice before candidate
evaluation, then called the historical-cycle candidate gate once per discovery
candidate.

### Evidence

Operator job
`run-research-autopilot-9a4ce549dd1c4ffba99ab54449ef2a0b` was still marked
`running`, with its last log at `2026-05-29T17:47:55Z`. Direct profiling showed
the large-run bridge path could be reduced to seconds by avoiding exhaustive
trial rereads and by caching historical-cycle ranking membership. With the
fixed checkout and `$env:PYTHONPATH='src'`, real BTC eligibility evaluation
completed in `9.234` seconds, produced 22,560 rows, and found 0 eligible
candidates because all BTC discovery candidate IDs were missing from the
63-row historical-cycle ranking table.

### Required resolution

Keep exhaustive trial-record validation for small discovery runs. For large
completed discovery runs, use count checks, completed-trial ID coverage,
vectorized ledger `record_sha256` checks against run-state hashes, and a
deterministic sample of trial JSON records. Reuse a historical-cycle gate
context across all discovery candidates so unranked candidates are blocked
from cached ranking evidence instead of reloading cycle evidence per row.

### Resolution notes

Resolved by WPR106-27. The eligibility bridge now uses targeted
`required_outputs` normalization for huge discovery manifests, sampled
large-run trial-record auditing, and a reusable candidate-gate context. Focused
regressions cover sampled large-run auditing and avoiding full cycle-gate calls
for unranked discovery candidates. Generated artifacts and runtime DB rows were
not rewritten. The existing running server must be stopped and restarted with
`PYTHONPATH=src` for this fix to take effect.

## ISSUE-R106-006: Nested migrated artifact metadata can still point at old checkout paths

Severity: P1
Stage discovered: Stage R106 - full repo mismatch and bug audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/operator_runs/**`, `src/tradingbotsuite/data/historical_data_catalog.py`, `tests/tradingbotsuite/test_market_data_collection.py`

### Problem

WPR106-24 and WPR106-25 made active `required_outputs` portable, but a broader
audit found nested metadata fields in generated manifests that still carried
old checkout paths after read-time normalization. Examples included
`data_source.*`, archive download paths, `cycle.data_window.dataset_path`,
`feature_column_set_evidence.manifest_path`, and
`resolved_paths.repo_root`. These fields are not always used by the immediate
operator root guard, but they are part of artifact provenance and can become
the next handoff mismatch when downstream code reads source evidence,
feature-column metadata, or repo-root metadata.

### Evidence

The WPR106-26 targeted operator-run manifest audit checked 22 current
operator-run JSON manifests across catalog, cycle, discovery, analysis, delta,
exit-lab, eligibility, and autopilot outputs. Before this fix, 16 manifests
contained raw old-root strings, and 15 normalized payloads still retained at
least one `C:\Users\papaa\Music\tradingbotsuite` string outside
`required_outputs`. Required outputs were already portable, but nested
provenance and resolved-path fields were not fully rebased.

### Required resolution

Broaden read-time operator-run normalization so old-checkout absolute strings
that point to repo-root-relative locations such as `data/...`, `configs/...`,
`docs/...`, `src/...`, or `tests/...` are rebased to the current checkout when
the mirrored path or parent exists. Rebase `repo_root` metadata to the current
checkout root. Preserve generated artifacts unchanged.

### Resolution notes

Resolved by WPR106-26. The shared normalizer now rebases repo-root-relative
old paths and `repo_root` metadata in addition to same-run artifact paths. The
post-fix manifest audit reports 22 manifests checked, 16 raw old-root
manifests, 0 normalized old-root manifests, 0 missing required outputs, 0
outside required outputs, and 0 read errors. Regression coverage proves
`data/...`, `configs/...`, and `repo_root` old-checkout strings are rebased to
the current repo without rewriting generated artifacts.

## ISSUE-R106-005: Migrated historical-cycle evidence outputs block candidate eligibility

Severity: P1
Stage discovered: Stage R106 - cycle manifest evidence portability
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/operator_runs/historical_cycles/**`, `src/tradingbotsuite/data/historical_data_catalog.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/tradingbotsuite/test_operator_ui.py`, `tests/research_artifacts/test_candidate_pack.py`

### Problem

After WPR106-24 resolved migrated discovery-manifest handoff paths, the next
autopilot run got further and failed during BTC candidate eligibility on the
completed BTC historical-cycle manifest. Its generated `required_outputs`
fields such as `ablation_report` still pointed at the old checkout root
`C:\Users\papaa\Music\tradingbotsuite`, even though mirrored evidence files
exist under `C:\Users\papaa\Music\researchenginedeluxe`.

### Evidence

Operator job `run-research-autopilot-d77072dd939744e296edbddac253e29b` failed
at `2026-05-29T15:13:41Z` with
`research manifest required output must stay inside the configured research output directory: ablation_report`.
The job skipped completed historical catalog, BTC/ETH cycle, BTC/ETH exact
discovery, BTC analysis, BTC analysis delta, and BTC frozen-entry exit-lab
artifacts before failing in BTC `candidate_eligibility`. That proves the prior
`blocked_candidates` discovery-manifest portability failure was cleared and the
remaining blocker moved to historical-cycle evidence outputs.

### Required resolution

Normalize migrated absolute operator-run paths in historical-cycle manifests
at read time before operator candidate-eligibility root checks and before
candidate-pack gate evaluation resolves `required_outputs`. Preserve generated
artifacts unchanged, and keep genuinely outside output paths fail-closed.

### Resolution notes

Resolved by WPR106-25. The shared operator-run artifact normalizer now rebases
any exact absolute local path string when it matches a mirrored operator-run
anchor in the current checkout, instead of relying only on narrow path-like key
names. Candidate-pack gate manifest reads use the same normalizer, so
historical-cycle evidence such as `ablation_report`, rankings, split/cost
metrics, stability regions, and overfit/trial-budget reports resolve under the
current checkout. Regression coverage keeps non-mirrored outside paths
rejected.

## ISSUE-R106-004: Migrated discovery manifests block candidate eligibility

Severity: P1
Stage discovered: Stage R106 - discovery manifest handoff portability
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/operator_runs/discovery_runs/**`, `src/tradingbotsuite/data/historical_data_catalog.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `tests/tradingbotsuite/test_operator_ui.py`, `tests/research_discovery/test_candidate_pack_bridge.py`

### Problem

The latest autopilot retry completed the expensive ETH exact discovery run, but
then failed during BTC candidate eligibility. The completed BTC discovery
manifest exists in the current checkout, while its generated `required_outputs`
still point at the old checkout root
`C:\Users\papaa\Music\tradingbotsuite`. The operator candidate-eligibility
guard correctly rejected those stale paths as outside the configured research
output root, but that prevented downstream eligibility review from consuming
mirrored discovery evidence.

### Evidence

Operator job
`run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1`
failed at `2026-05-28T22:15:17Z` with
`research manifest required output must stay inside the configured research output directory: blocked_candidates`.
The same run completed ETH exact discovery to `570240/570240` trials. The BTC
manifest's `required_outputs.blocked_candidates` pointed to
`C:\Users\papaa\Music\tradingbotsuite\...`, while the mirrored
`blocked_candidates.parquet` file exists under
`C:\Users\papaa\Music\researchenginedeluxe\...`.

### Required resolution

Rebase migrated operator-run paths from discovery manifests at read time for
operator candidate-eligibility validation and for discovery candidate-pack
bridge ledger loading. Preserve generated artifacts unchanged, and keep truly
outside paths rejected.

### Resolution notes

Resolved by WPR106-24. The shared operator-run path normalizer now recognizes
discovery manifest `required_outputs` keys such as `run_state`,
`blocked_candidates`, `interesting_candidates`, `filter_blockers`, `snapshots`,
and `trials`. Operator candidate eligibility and the discovery candidate-pack
bridge normalize migrated operator-run paths from discovery manifests before
validating/reading `required_outputs`. Regression coverage keeps non-mirrored
outside paths fail-closed and proves mirrored migrated discovery manifests can
be consumed without rewriting generated artifacts.

## ISSUE-R106-003: Active R106 catalog handoff metadata is not portable after repo migration

Severity: P1
Stage discovered: Stage R106 - full repo data/code crosscheck
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/operator_runs/historical_data/**`, `src/tradingbotsuite/data/historical_data_catalog.py`, `src/tradingbotsuite/data/durable_public_archive.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`

### Problem

The current `main` checkout is being treated as the migrated R106 branch, but
the active completed catalog
`refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb` records
absolute artifact paths under `C:\Users\papaa\Music\tradingbotsuite` instead
of the current checkout root `C:\Users\papaa\Music\researchenginedeluxe`.
The mirrored fixture packs, readiness configs, cycle specs, discovery specs,
and source summary exist under the current checkout and validate, but the
catalog's source-of-truth path fields still point outside the current repo.
The same local operator-run tree also has no discovered
`modern_window_profile.json` artifacts, despite later R106 workflow docs
describing modern-window profile artifacts/spec links as part of the completed
workflow.

### Evidence

WPR106-21 validated the current checkout mirror of the active catalog and found
BTCUSDT/ETHUSDT candidate-depth fixture manifests valid and durable-public-
archive ready. It also found every catalog symbol path field
(`fixture_manifest_path`, `readiness_config_path`, `cycle_spec_path`,
`discovery_spec_path`, and `source_summary_path`) declared outside the current
repo root. A recursive search under `data/research/operator_runs` found no
`modern_window_profile.json` artifacts in the current local operator data tree.

### Required resolution

Resolved by WPR106-22. Active historical-data catalog reads now rebase stale
absolute operator-run artifact paths to the current mirrored catalog run
directory when the local mirrored path exists. Operator artifact indexing and
R104 readiness diagnostics use the rebased catalog payload, and isolated
historical-cycle/discovery job specs are written from rebased source specs so
embedded dataset/readiness paths no longer point at the old checkout.

WPR106-22 does not mutate generated fixture packs, catalog artifacts, cycle
outputs, discovery ledgers, or generated active specs. The migrated pre-profile
catalog remains truthful when it reports no local modern-window profile
artifacts; future refreshed catalogs still write/index profile paths when they
are produced, and the same read-time rebase covers nested profile path fields.

### Resolution notes

Resolved by WPR106-22. Regression coverage proves migrated catalog path fields
are rebased at read time and migrated active cycle/discovery specs are rebased
before operator isolated specs are written. `ISSUE-R104-001` remains open as an
empirical evidence gate; WPR106-22 makes no candidate-ready, promotion-ready,
profitability, or live-readiness claim.

## ISSUE-R106-001: Exact discovery runtime is not proven under the 30-hour target

Severity: P1
Stage discovered: Stage R106 - active candidate-depth evidence runs
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `configs/discovery/**`

### Problem

The R106 candidate-depth exact discovery specs schedule 570240 trials per
symbol. Prior completed R105/R104 telemetry for the same trial budget measured
about 31.2 wall-clock hours and roughly one busy core of effective utilization
despite nominal 48-worker execution. The current specs use process workers and
durable snapshot/resume, but no scheduler/effective-work optimization has
proven sub-30-hour runtime on the expanded candidate-depth fixture packs.

### Evidence

`STAGE_R105_DISCOVERY_PROCESSOR_UTILIZATION_TELEMETRY_REPORT.md` recorded
570240 trials, 112216.3899596 wall seconds, 304.8966377577983 trials/minute,
and noted that the packet did not claim a performance fix. The active R106
exact specs still declare 570240 max trials with process executor and 48
workers.

### Required resolution

Before claiming exact discovery is comfortably under 30 hours, run a measured
candidate-depth exact-discovery probe or implement the scheduler/effective-work
reduction recommended by R105, then record manifest telemetry showing worker
capacity, trial rate, ETA, and durable resume behavior. Keep exact discovery
snapshots and progress visible while this remains open.

### Resolution notes

Resolved by WPR106-08. The failed BTC exact-discovery process-pool run was
recovered in place, process workers are capped safely by default, completed
chunks are persisted as they return, and exact discovery now schedules
production no-stop runs by cache group instead of tiny randomized chunks. KNN
screening now reuses relaxed exact base predictions, cached threshold metric
arrays, and no-regime baselines, and defers heavy inline artifacts for
`interesting_only` sweeps. Bounded BTC resume probes advanced the active run
from 128 to 512 persisted trial records. The final 64-trial probe completed in
610.7 seconds with 8 workers, base KNN misses averaging 365.2 seconds, and
base-hit non-artifact threshold trials averaging 0.379 seconds. With 108 cache
groups and full cache-group chunks, the measured full-run estimate is roughly
9 to 12 wall-clock hours on this machine, below the 30-hour target.

WPR106-09 follow-up: the later full BTC run still stopped after roughly
14 hours with 407669 durable trial files, while state lagged by 249 records
and the manifest remained stale. The run was recovered in place without
restarting completed work. Large resumes now avoid hydrating the full trial
corpus before useful work, recover only lagging trial files, skip real-context
allocation for zero-trial metadata recovery, and preserve existing ledgers
until a full completion rebuild can be performed. WPR106-10 restores the
default real-discovery process worker cap to 8 by operator direction because
throughput is preferred over stability for this prolonged study; operators can
still lower it with `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS` if needed. The
active BTC exact-discovery run remains incomplete at 407669/570240 trials; no
candidate-ready claim exists until it finishes and downstream eligibility review
passes.

WPR106-11 follow-up: operator job
`run-discovery-5b8013f779ef43c28a8c3567a14d14a4` later advanced durable BTC
exact-discovery trial files to 531077, then failed on Windows while atomically
replacing `run_state.json`. `atomic_write_json()` now retries transient
`PermissionError` replace failures. A zero-trial resume reconciled state to
531077 completed IDs/hashes with 39163 trials remaining. The active run is
still incomplete; the failed job record remains failed, but its durable progress
is preserved.

WPR106-12 follow-up: operator job
`run-discovery-40cb1c90d0f8487a859a23e05d21e656` completed BTC exact-discovery
compute, then failed during final Parquet ledger materialization because absent
numeric ledger fields were represented as empty strings and mixed with integer
metric values such as `accepted_bar_count`. Final ledgers now normalize integer,
float, and boolean columns to pandas nullable dtypes, and completed-run resume
can rebuild stale, missing, row-count mismatched, or unreadable final
ledgers/manifests from durable trial JSONs without restarting compute. The BTC
exact-discovery output is finalized at 570240/570240 trial records with 22560
interesting rows, 547680 blocked rows, and 0 filter-blocked rows. Candidate
eligibility review is still required before any candidate-ready claim.

## ISSUE-R106-002: Long research runs lack mandatory post-run analytics and one-button sequencing

Severity: P1
Stage discovered: Stage R106 - active candidate-depth evidence runs
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `configs/research/**`, `configs/discovery/**`, `docs/stage_reports/**`

### Problem

The completed BTC candidate-depth cycle and exact discovery produce durable
evidence, but the operator still cannot run the full BTC/ETH research sequence
as a single resumable workflow that automatically writes feature/filter/exit
analytics, run-to-run comparisons, and candidate eligibility evidence. Without
that layer, a 10-30 hour run can finish with artifacts that are technically
complete but not useful enough for deciding the next research mutation.

### Evidence

WPR106-13 analysis of the completed BTC artifacts shows the cycle is
fixed-holding only, no candidate is pack eligible, no non-baseline candidate has
positive pure ROI, exact discovery has 22560 interesting KNN rows but 547680
blocked rows, orderflow feature sets were not active in the current specs, the
operator's requested simple runner exit policy is not implemented as a
first-class policy, and there is no explicit modern-window holdout profile for
the current-market concern. The Research UI also still requires manual sequencing
instead of one master resumable autopilot.

### Required resolution

Add a master research workflow that reuses the central historical data catalog,
runs missing BTC/ETH cycle and exact-discovery jobs, writes mandatory analysis
artifacts for each symbol, compares results against previous runs, runs
candidate eligibility, and exposes clear progress/ETA in the UI. Add a
frozen-entry exit lab for the strongest exact-discovery rows, including the
simple runner semantics requested by the operator or an explicit documented
replacement. Include modern-window profiles alongside full-window evidence.

### Resolution notes

Resolved by WPR106-16. WPR106-13 adds the first repeatable analysis helper and
next-agent handoff. WPR106-14 wires that helper into the operator job API,
artifact index, progress checklist, and required UI path before candidate
eligibility review. WPR106-15 adds a bounded master BTC/ETH operator sequencer
that reuses current artifacts, runs missing required steps through existing
helpers, and writes an autopilot manifest. WPR106-16 adds modern-window profile
artifacts/spec links, run-to-run delta artifacts, `simple_runner_v1`,
bridge-compatible frozen-entry exit-lab artifacts, and operator/API/UI/autopilot
sequencing through eligibility. Existing exact-discovery ledgers may still
write a blocked frozen-entry lab when per-entry timestamps are unavailable, but
that is now explicit fail-closed evidence rather than missing workflow
machinery. Candidate-ready evidence remains blocked by empirical gates under
`ISSUE-R104-001`; no promotion claim is made.

## ISSUE-R101-001: Fixture source provider capability mismatch is not validated

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/data/historical_fixture_pack.py`, `tests/contracts/test_historical_fixture_pack_contract.py`

### Problem

WPR100 added provider capability metadata to generated fixture-pack source and
context entries, but fixture validation only checks provider capability payloads
on context families. A tampered top-level fixture `source.provider_capability`
can claim the wrong durability class or source identity without failing
`validate_historical_fixture_pack_manifest()`.

### Evidence

Review found `_provider_source_metadata()` attaches provider capability
metadata, while `_validate_provider_capability_metadata()` is only called from
`_validate_context_family_metadata()` for context-family entries. Existing
tests assert source capability is present and reject context mismatches, but
there is no source mismatch regression.

### Required resolution

Validate top-level fixture `source.provider_capability` against the fixture
source name and primary data family, add a regression that tampers the source
capability, and ensure candidate-pack provenance evidence cannot inherit a
tampered source capability as trusted truth.

### Resolution notes

Resolved by WPR102-01. Top-level fixture `source.provider_capability`
metadata is now revalidated against the declared source and primary data
family, with regressions for tampered source identity and durability class.

## ISSUE-R101-002: Direct research CLI output-directory allowlist is incomplete

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/main.py`, `tests/live/**`, `tests/tradingbotsuite/**`

### Problem

The operator UI now isolates historical-cycle and discovery output under the
configured research output root, and the discovery candidate-pack bridge uses a
central output-dir resolver. Many direct CLI research commands still pass
`--output-dir` values through as raw `Path(args.output_dir)` values. This leaves
the direct CLI boundary weaker than the operator boundary and keeps alive the
R98-deferred risk that research commands can write outside the research output
tree.

### Evidence

Review found `_resolve_research_output_dir()` in `src/tradingbotsuite/main.py`,
but most research CLI handlers still pass `Path(args.output_dir)` directly.
WPR98 explicitly deferred wholesale output-directory allowlist hardening.

### Required resolution

Create a dedicated CLI output-root allowlist packet. Route all research command
output directories through a shared resolver, keep input/source paths separate,
add command-level tests for each `--output-dir`, and preserve existing operator
UI isolated-output behavior.

### Resolution notes

Resolved by WPR102-01. Direct research CLI output directories are routed
through the shared research output-root resolver, command tests cover the
allowlist boundary, and input/source paths remain separate from output
resolution.

## ISSUE-R101-003: Candidate-ready empirical evidence is still blocked by durable multi-window data gaps

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `configs/research/**`, `configs/discovery/**`, `data/research/fixtures/**`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/research_discovery/**`

### Problem

The branch has strong machinery for fixture validation, discovery, backtesting,
gates, and candidate-pack rejection, but it still lacks durable multi-window
BTCUSDT/ETHUSDT evidence sufficient for candidate-ready empirical claims. The
latest-window REST context fixtures and Crypto Lake free-sample liquidation
fixture are correctly diagnostic-only, so they cannot complete candidate-ready
research by themselves.

### Evidence

Configs and fixture manifests continue to label latest-window context and free
sample evidence as diagnostic or non-promotable. Recent stage reports and the
branch technology reference defer durable BTC/ETH multi-window evidence,
liquidation candidate eligibility, true L2/depth evidence, and Stage 13
execution.

### Required resolution

Build durable BTCUSDT/ETHUSDT multi-window fixture packs from public archive or
vendor-backed sources with capability metadata, run historical-cycle and
discovery validation on those packs, and keep all candidate packs blocked until
validation floors, exit lab, multiple-testing, side/split/regime, stability,
cost-stress, and source-capability evidence pass.

### Resolution notes

Resolved by WPR102-01 and WPR103-01. WPR102 made provider capability and
durable public archive readiness first-class blockers in research-cycle,
discovery validation-floor, bridge, and candidate-pack gates. WPR103 added
checksum-verified BTCUSDT and ETHUSDT Binance Vision multi-window fixture
packs under `data/research/fixtures/*_public_archive_multi_window_v1`, each
with 15m bars, 1m lower-timeframe bars, 1m aggregated aggTrade trade-flow
proxy context, source archive hashes, provider capability metadata, window
selection metadata, and durable public-archive readiness validation. No
candidate pack, promotion artifact, latest-window-only evidence, or fabricated
data was promoted; candidate validation remains a later research-only stage.

## ISSUE-R101-004: Import-boundary tests omit several live-adjacent research packages

Severity: P2
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `tests/contracts/test_import_boundaries.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_artifacts/**`

### Problem

Import-boundary tests cover `research`, `research_discovery`, `data`,
`features`, `backtesting`, and `strategies`, but do not cover
`research_cycle`, `optimization`, or `research_artifacts`. These packages are
central to candidate gates and live-adjacent artifact handling, so future import
regressions could bypass the current contract test.

### Evidence

Static review found no forbidden order-placement imports in those packages, but
`tests/contracts/test_import_boundaries.py` does not enumerate them.

### Required resolution

Extend import-boundary tests to include `research_cycle`, `optimization`, and
`research_artifacts`, and keep the forbidden import list aligned with the
boundary contract.

### Resolution notes

Resolved by WPR102-01. Import-boundary tests now cover `research_cycle`,
`optimization`, and `research_artifacts`, and the boundary contract documents
those roots as research/live-adjacent surfaces that must not import
order-placement adapters.

## ISSUE-R101-005: Provider capabilities are not yet consumed by readiness and pack gates

Severity: P2
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/data/contracts.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `src/tradingbotsuite/research_discovery/**`

### Problem

Provider capability metadata is now emitted and partially validated, but
candidate-readiness logic still primarily relies on older latest-window,
free-sample, diagnostic, and fixture-evidence flags. The new durability class,
health policy, and candidate-ready-default fields are not yet first-class gate
inputs.

### Evidence

Static scans found `candidate_ready_default` and `provider_capability` usage in
the data/fixture layers, but not as decision inputs in historical-cycle gates,
discovery validation floors, or candidate-pack eligibility.

### Required resolution

Promote provider capability metadata into data-source evidence, public-archive
readiness, historical-cycle rankings, discovery validation floors, and
candidate-pack gate reasons so diagnostic/default-false capabilities cannot be
treated as candidate-ready by omission.

### Resolution notes

Resolved by WPR102-01. Provider capability and durable public archive readiness
are now carried into research-cycle data-source evidence, candidate gate
reports, discovery validation floors, and candidate-pack source evidence so
diagnostic/default-false sources block candidate readiness unless durable
archive readiness proves the source is usable.

## ISSUE-R101-006: Distribution name still points at the legacy package identity

Severity: P3
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `pyproject.toml`, `README.md`, packaging/install documentation, CI or release metadata if added later

### Problem

R98 added the canonical `tradingbotsuite` console script, but the project
distribution name remains `tradingbot-framework`. This is not a runtime safety
blocker, but it is a handoff and packaging weak point for a branch that now
orients users around the active `tradingbotsuite` package.

### Evidence

`pyproject.toml` still declares `name = "tradingbot-framework"` while docs and
the new console entrypoint use `tradingbotsuite`.

### Required resolution

Open a packaging-only packet before any release or external handoff. Decide
whether to rename the distribution, preserve an alias/compatibility story, and
update docs/tests without breaking editable local installs.

### Resolution notes

Resolved by WPR102-01. The active distribution name is now `tradingbotsuite`;
the legacy `tradingbot` console/package compatibility path is retained for
existing local workflows.

## ISSUE-R98-001: Legacy replay metrics could report promotion readiness

Severity: P0
Stage discovered: Stage R98 - Research boundary validation hardening
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research/dataset.py`, `src/tradingbotsuite/research/modeling.py`, `src/tradingbotsuite/research/evaluation.py`, `src/tradingbotsuite/research/live_readiness.py`, `tests/tradingbotsuite/test_research.py`

### Problem

The legacy BTC research dataset/model/replay path did not consistently emit the
full research boundary metadata, and `replay_eval()` could set
`promotion_ready: true` when local metric thresholds passed. That contradicted
the branch invariant that research outputs are observe-only and not promotion
artifacts.

### Evidence

Subagent boundary review found dataset manifests carrying only
`research_only: true`, train/artifact manifests omitting the full trio, and
`src/tradingbotsuite/research/evaluation.py` deriving promotion readiness from
local replay failures.

### Required resolution

Normalize the legacy research artifacts to emit `research_only: true`,
`observe_only: true`, `promotion_ready: false`, and non-live boundary metadata;
make replay metrics include an explicit research-only non-promotable failure.

### Resolution notes

Resolved by WPR98-01. The shared `research_artifact_boundary_metadata()` helper
is used by legacy dataset/model/replay outputs, and replay metrics now remain
non-promotable even when local diagnostic thresholds pass.

## ISSUE-R1-001: Research branch still contains live execution surfaces

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Live Safety Agent
Status: resolved
Paths affected: `run_manual.py`, `run_live_smoke.py`, `src/tradingbotsuite/adapters/execution.py`, `src/tradingbotsuite/core/engine.py`, `src/tradingbotsuite/runtime.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbot/live.py`, `src/tradingbot/data/hyperliquid.py`

### Problem

The research branch carries live-adjacent launchers and execution adapters. This does not prove research modules are placing orders, but it increases branch-boundary risk and must be isolated or guarded before any later research artifact can be interpreted as live-ready.

### Evidence

Stage 1 cartography identified Hyperliquid execution adapters, manual runtime launchers, operator commands, and legacy `tradingbot` live paths on `research/v3-experimental-engine`.

### Required resolution

Stage 2 must formalize import and artifact contracts. Stage 10/11 must keep live execution on the live branch and require promotion/shadow validation before any research output reaches live runtime behavior.

### Resolution notes

Stage 2 added `docs/contracts/boundary_contract.md` and `tests/contracts/test_import_boundaries.py` to prevent research modules from importing order-placement paths. Stage 10/11 added live preflight and promotion/shadow validation so research outputs cannot become live execution inputs without explicit later approval.

## ISSUE-R1-002: Research CLI and live/operator CLI are coupled in one entry module

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Documentation Agent
Status: resolved
Paths affected: `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`

### Problem

`src/tradingbotsuite/main.py` exposes live/operator commands and research commands in the same module, and the operator UI can queue research jobs. This needs explicit contract documentation and later enforcement so live mode cannot run research jobs.

### Evidence

Stage 1 command inventory found `serve`, `manual`, `smoke-live`, `build-dataset`, `train-model`, `calibrate-model`, `replay-eval`, HMM/KNN commands, provider fetch commands, and experiment commands in the same CLI module.

### Required resolution

Stage 2 should document command ownership and boundary rules. Stage 10 should enforce live-mode rejection of research jobs.

### Resolution notes

Stage 2 documented command ownership in `docs/contracts/boundary_contract.md`. Stage 10 added `src/tradingbotsuite/live/preflight.py`, CLI guards in `src/tradingbotsuite/main.py`, and tests in `tests/live/test_preflight.py` so live mode rejects research commands before execution. Stage 12.1 added the new `plan-feature-ablation` research command to the same live rejection set.

## ISSUE-R44-001: Final crosscheck found research evidence hygiene blockers

Severity: P1
Stage discovered: Stage R44 - Final crosscheck hardening
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/optimization/stability.py`, `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/research/feature_ablation.py`, `.gitignore`, `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`

### Problem

The final crosscheck found several issues that could weaken reproducibility or evidence truthfulness before push: relative benchmark output paths could recurse under generated spec locations, provider benchmark evidence depended on an ignored fixture, non-contiguous holdout splits could include unrelated rows, stability and ablation grouping omitted exit-policy identity, fixed-interval context manifests did not detect gaps, and generic feature-ablation runs could be labeled validation-incomplete when all configured evidence was executable.

### Evidence

Independent agent review and full-suite validation identified the benchmark path risk, ignored provider fixture risk, split/evidence grouping issues, context gap reporting issue, and failing tests in benchmark artifact accounting, removed-source boundaries, and feature-ablation execution scope.

### Required resolution

Before commit/push, make provider fixture evidence durable, resolve benchmark paths to absolute directories, use short generated backtest run directory names, preserve exact holdout membership, include exit-policy identity in stability/ablation grouping, make context gap checks interval-aware, and rerun focused plus full validation.

### Resolution notes

Stage R44 fixes implemented all required changes and added regression coverage. The provider latest-month fixture pack is unignored for commit. Focused validation passed, WPR42 provider benchmark was rerun without filename-length warnings, and full validation is recorded in the R44 stage report.

## ISSUE-R58-001: OI contraction exit accepted non-finite context

Severity: P1
Stage discovered: Stage R58 - OI contraction exit policy
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/backtesting/exits.py`, `tests/backtesting/test_exit_policy_expansion.py`

### Problem

The new `oi_contraction_exit_v1` policy initially treated infinite OI values as valid row-level context. A row with infinite OI notional and negative-infinite OI delta/z-score could trigger an exit instead of failing closed to the normal time exit.

### Evidence

Final review of the WPR58 diff reproduced an `oi_contraction_exit_v1` trigger on non-finite OI context, contradicting the stage report's row-level missing or non-finite context behavior.

### Required resolution

Reject non-finite values in optional numeric context conversion and add regression coverage for `inf` and `-inf` OI rows.

### Resolution notes

Stage R58 updated `_optional_numeric` to return no context for non-finite numbers and added `test_oi_contraction_exit_skips_non_finite_oi_context`. Focused validation passed after the fix.

## ISSUE-R95-001: CUDA backtest backend absent for NVIDIA acceleration path

Severity: P1
Stage discovered: Stage R95 - Performance candidate-selection engine crosscheck
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`

### Problem

The research-cycle candidate-selection path can now record NVIDIA/CUDA preference and run aggregate candidate backtests with bounded CPU workers, but no concrete CUDA/GPU backtest backend is registered. GPU acceleration therefore cannot truthfully be claimed for candidate search or stability-region evaluation yet.

### Evidence

WPR95 crosscheck found only reference and fixed-holding vector CPU backtest backends. The performance plan reports `blocked_no_cuda_backtest_backend_registered` whenever GPU acceleration is requested.

### Required resolution

Add a validated CUDA-capable research backtest or feature-evaluation backend with backend evidence, parity checks against the reference engine, deterministic artifact identity, and fallback behavior before any NVIDIA speedup claim is allowed.

### Resolution notes

Resolved by WPR96. The branch now has an optional `cuda_fixed_holding`
research backend with lazy CuPy import, runtime smoke evidence, support reason
codes, CPU fallback behavior, fake-CuPy parity tests, local CUDA parity tests
when hardware is available, benchmark evidence, and stability-region
acceleration counters. The backend remains diagnostic and `speed_claimed: false`;
split/cost-stress validation is forced back to CPU/reference when GPU routing is
requested. Rich exits, lower-timeframe paths, KNN overlays, candidate-pack
promotion, live readiness, sizing, and order placement remain out of scope.

## Issue template

```markdown
## ISSUE-ID: Short title

Severity: P0/P1/P2/P3
Stage discovered:
Owner:
Status: open | in_progress | resolved | accepted_debt
Paths affected:

### Problem

### Evidence

### Required resolution

### Resolution notes
```
