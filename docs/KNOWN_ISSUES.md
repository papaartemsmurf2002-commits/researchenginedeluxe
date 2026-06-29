# Known Issues

Last updated: 2026-06-29

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
| P0 | 0 | 0 | 8 | 0 |
| P1 | 0 | 0 | 31 | 0 |
| P2 | 0 | 0 | 9 | 0 |
| P3 | 0 | 0 | 1 | 0 |

## ISSUE-R106-035: Central archive lacks v2 snapshot bridge for larger-panel benchmark evidence

Severity: P1
Stage discovered: WPR106-569 - V2 autonomous research systems closure
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/central_market_history/**`,
`src/tradingbotsuite/v2/archive_inventory/**`,
`src/tradingbotsuite/v2/backtest_engine/**`,
`docs/work_packets/WPR106-570-v2-central-archive-snapshot-bridge-and-benchmark-closure.md`,
`docs/work_packets/WPR106-569-v2-autonomous-research-end-to-end-systems-closure.md`,
`docs/stage_reports/STAGE_R106_WPR106_569_SYSTEMS_CLOSURE_REPORT.md`

### Problem

The local central archive can be inventoried and feature-cataloged, but it
does not currently expose the v2 snapshot-backed manifest records required by
the benchmark runner. This blocks real larger-local-panel benchmark evidence
and any speedup claim for the current fast/reference path.

### Evidence

On 2026-06-29, `archive-inventory --summary` reported 492 local research
records and 8,633,194 rows across `binance_usdm` and `hyperliquid`.
`archive-inventory --feature-catalog --summary` reported 251 feature-catalog
entries and 256,523 feature rows.

The BTCUSDT/ETHUSDT six-month strategy data-requirement resolver run exited
non-zero with `ready=false` and emitted bounded `DataGapRequest` objects for
missing usable `bars` and `coverage` windows. A direct
`fast-lane benchmark-run` against `data/research/central_market_history`
rejected deterministic placeholder snapshot IDs with
`archive_snapshot_not_found`. A manifest-store probe found zero v2
`file_manifest` rows, zero archive snapshots, and no
`manifests/archive_snapshots.parquet` or `manifests/file_manifest.parquet`.

### Required resolution

Create a research-only v2 snapshot bridge or equivalent snapshot/coverage
export from existing central archive evidence, without collecting new data or
rewriting historical ledgers. Then rerun the strategy data-requirement
resolver, larger local panel benchmark, reference audit, and full replay
verification with real snapshot IDs before making any runtime or speedup
claim.

### Resolution notes

Resolved by WPR106-570. The read-only central archive snapshot bridge converts
existing central project validation, batch manifests, and normalized Parquet
files into a packet-local v2 snapshot-backed benchmark input root without
mutating `data/research/central_market_history/**`.

The bridge report at
`data/research/wpr106_570_central_archive_snapshot_bridge/bridge_archive/manifests/central_archive_snapshot_bridge_report.json`
records a BTCUSDT/ETHUSDT 1m bridge over `2024-01-01T00:00:00Z` through
`2024-07-01T00:00:00Z` with 12 derived file-manifest rows, 524,160 rows,
accepted-research coverage reports, real archive/universe snapshot IDs, and
`central_archive_mutated=false`.

The archive-first resolver over the bridge returned `ready=true`, usable
archive refs for BTCUSDT and ETHUSDT, and no `DataGapRequest`. The completed
larger 1m benchmark report at
`data/research/wpr106_570_central_archive_snapshot_bridge/benchmark_runs/wpr106570-btc-1m-jan-feb2024-smoke-tol1e9/benchmark_report.json`
uses real central archive BTCUSDT 1m rows for `2024-01-01T00:00:00Z` through
`2024-03-01T00:00:00Z` with 86,400 reported rows, metrics-only artifacts,
reference-vs-fast parity `pass` at `tolerance_abs=1e-9`, complete runtime,
data-load, artifact-write, memory, panel-size, instrument-count, timeframe,
artifact-mode, and runtime-context observations, and all research-only
boundary flags non-promotable.

The attempted BTCUSDT/ETHUSDT six-month panel benchmark exceeded the local
validation host timeout and was not used as resolution evidence. The completed
BTCUSDT two-month benchmark measured `speedup_ratio=0.07996443360632331`,
`speedup_claimed=false`; therefore WPR106-570 resolves the snapshot/coverage
bridge blocker but does not support any broad speedup claim.

## ISSUE-R106-034: Uploaded WPR106-555 strategies block autonomous-ready claim

Severity: P1
Stage discovered: WPR106-554 - V2 autonomous readiness with uploaded test strategies
Owner: Codex Research Agent
Status: resolved
Paths affected: `configs/strategies/wpr106_554/**`,
`configs/strategies/wpr106_555/**`,
`configs/strategies/wpr106_556/**`,
`data/research/wpr106_554_autonomous_readiness/**`,
`data/research/wpr106_555_autonomous_readiness/**`,
`data/research/wpr106_556_autonomous_readiness/**`,
`docs/work_packets/WPR106-554-v2-autonomous-readiness-test-strategies.md`,
`docs/work_packets/WPR106-555-v2-autonomous-readiness-policy-and-s31.md`,
`docs/work_packets/WPR106-556-v2-autonomous-readiness-atlas-strategy-pass.md`

### Problem

WPR106-555 applies the corrected operator policy: strategies whose required
data cannot be collected, deduced, or simulated truthfully are skipped with
evidence rather than blocking the whole readiness set. It also changes the
base cost model to taker fee `4.32` bps, maker reference fee `1.44` bps, and
median slippage `8` bps, while preserving `20` bps as the worst-case reference
and a stricter 3x stress lane at `24` bps.

The uploaded `S31` volatility-adjusted trend strategy now compiles and runs
through the bounded archive-ref cycle. A tuned in-range S31 spec is base-case
positive, but it does not pass accepted research validation because the cost
stress gate reports `cost_dependent_failure`.

The uploaded `S54` cross-sectional mean-reversion strategy compiles and runs,
but remains negative after costs and fails fold stability. The uploaded `S59`
aggressive-sweep reversal strategy is skipped for this readiness set because
the current bounded vectorized cycle cannot yet consume event-level trade/L2
sweep and replenishment state; a bar-only proxy must not be substituted.

### Evidence

WPR106-555 reuses the research-only `binance_usdm` 1h panel materialized from
the authoritative central 1m store for BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT
from `2024-01-01T00:00:00Z` through `2024-08-01T00:00:00Z` with full
per-instrument coverage. The archive snapshot is
`73c4c874731c6780570a3933cf7e137be178198dd7f37d63373c2cd083ef1ae6`; the
universe snapshot is
`99b9cdb5fe1f5cc11e35cb907557b5b0d728ab1adbc2887737dcea8cace97c2f`.

The final WPR106-555 tuned S31 bounded cycle evidence is under
`data/research/wpr106_555_autonomous_readiness/cycle_s31_vol_adjusted_trend_base8_tuned/**`.
It executed all planned jobs and produced a succeeded run manifest with
`usable_months=6`, `net_return=0.0022629838731449414`, and `trade_count=1228`,
but the cycle summary records `completed_with_blockers`. The validation gate
manifest records `fold_stability_score=1.0`, `validation_status=fail`, and
`blocker_reasons=["cost_dependent_failure"]`; cost sensitivity reports
`stress_2x_net_return=-0.07489973176516174` and
`stress_3x_net_return=-0.14612879144902113`.

The WPR106-555 S54 bounded cycle evidence is under
`data/research/wpr106_555_autonomous_readiness/cycle_s54_cross_reversion_base8/**`.
It records `net_return=-0.3254955638131598` and fails fold stability.

The S59 skip note is
`configs/strategies/wpr106_555/skipped/s59_aggressive_sweep_reversal.md`.

### Required resolution

Do not mark the repository `autonomous_research_ready` for the uploaded
strategy set until one of these is true:

- At least one included, testable uploaded strategy passes a blocker-free
  accepted-research archive-ref cycle under the declared base and stress cost
  policy, and the formal autonomous-readiness manager gate has zero P0/P1
  blockers.
- The user changes the validation policy or cost-stress requirements and a new
  work packet records the changed assumptions without weakening research-only
  boundaries.
- S59 receives accepted trade/L2 archive refs plus deterministic
  sweep/replenishment feature materialization and event-driven replay
  validation with documented queue/fill assumptions, if S59 is re-included in
  the readiness strategy set.

### Resolution

Resolved by WPR106-556. The uploaded combined strategy atlas was used as the
next input queue after WPR106-555. Funding, OI, spread, order-book, trade-flow,
liquidation, event, attention, on-chain, and options strategies were classified
as data-blocked for the current OHLCV-only archive-ref cycle rather than
proxied. Bar and cross-sectional atlas strategies were scanned under the same
WPR106-555 cost policy.

The first blocker-free strategy is the atlas S24/S65 long-only
cross-sectional momentum/top-gainer continuation spec at
`configs/strategies/wpr106_556/accepted/first_passing_atlas_rank_strategy.json`.
It ranks BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT by trailing 480-hour return,
holds the top half long-only with `max_gross_leverage=0.05`, and remains
research-only/non-promotable.

The durable archive-ref bounded cycle at
`data/research/wpr106_556_autonomous_readiness/cycle_s24_s65_cross_sectional_momentum_base8_summary.json`
completed all planned jobs, ran the audit, and reported zero blockers. The
validation gate passed with no blocker reasons. Metrics were
`net_return=0.02854830964529631`, `stress_2x_net_return=0.01864770640252944`,
`stress_3x_net_return=0.008841803210934085`, `trade_count=314`, and
`total_turnover=7.850000000000044`.

After the clean pushed baseline, the formal autonomous-readiness manager
report was rerun and returns `autonomous_research_ready=true` with
`blocker_count=0`. No open P0/P1 strategy-validation blocker remains.

## ISSUE-R106-033: LIT December 2025 official 1m archive gap blocks all-project strict bar readiness

Severity: P1
Stage discovered: WPR106-545 - V2 project-needed 1m parallel normalization
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/central_market_history/**`,
`docs/work_packets/WPR106-545-v2-project-needed-1m-parallel-normalization.md`

### Problem

The current project-needed 1m normalization path cannot truthfully mark every
current-public project symbol as strict full-month 1m backtest usable through
2026-05. `LITUSDT` December 2025 has an official Binance USD-M no-data gap
from `2025-12-23T00:00:00Z` through `2025-12-23T17:29:00Z`. The monthly and
daily official kline archives contain only 43,590 of 44,640 expected monthly
minutes, and the quality report correctly blocks the month with
`coverage_ratio=0.9764784946236559`.

### Evidence

WPR106-545 normalized 622 additional project-needed monthly archives and
validated 737 project manifests plus 740 raw ZIP/checksum/CRC sources with no
raw failures and zero `.part` files. The final validation report is
`data/research/central_market_history/manifests/wpr106-545-project-needed-1m-normalization-validation-report-after-gap-proof.json`.
It fails closed only on `LIT` period `2025-12`.

The gap proof is
`data/research/central_market_history/manifests/wpr106-545-lit-2025-12-daily-repair-source-discovery-report.json`.
It verifies the official daily kline and official daily aggTrades archives for
`2025-12-23`, both starting at `2025-12-23T17:30:00Z`. A direct public Binance
USD-M kline API probe for the missing start window returned `[]`, while a
probe at `2025-12-23T17:30:00Z` returned rows. No synthetic carry-forward or
zero-volume bars were written.

### Required resolution

Either obtain an additional official no-paid source that proves the missing
LIT interval, or keep LIT December 2025 masked as an unavailable/halted
provider interval in any bar-only backtest. Until then, all-symbol strict
continuous 1m readiness must remain blocked, although the other current
project symbols are normalized and validated for their collected windows.

### Resolution

Resolved by WPR106-546. The missing interval is not a recoverable data gap for
the current project symbol; it is the pre-onboard period before Binance's
current Lighter Protocol `LITUSDT` USD-M perpetual launched at
`2025-12-23T17:30:00Z`. Binance `exchangeInfo` reports
`onboardDate=1766511000000`, and the official launch announcement gives the
same launch time. WPR106-546 appended a lifecycle-scoped December 2025
manifest beginning at the onboard timestamp and regenerated project-needed
validation at
`data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-validation-report.json`.
That report passes all 29 project symbols with zero manifest failures, zero
raw ZIP failures, and zero `.part` files. The old full-month LIT artifact
remains blocked evidence and must not be used for the current Lighter Protocol
contract before the onboard timestamp.

## ISSUE-R106-032: Legacy Hyperliquid-native data-source conflict blocked readiness

Severity: P1
Stage discovered: WPR106-528 - V2 autonomous strategy readiness review
Owner: Codex Research Agent
Status: resolved
Paths affected: `docs/work_packets/WPR106-528-v2-autonomous-strategy-readiness-review.md`,
`docs/work_packets/WPR106-529-v2-autonomous-readiness-evidence-probe.md`,
`docs/contracts/autonomous_readiness_contract.md`,
`src/tradingbotsuite/v2/audit/readiness.py`,
local/generated autonomous-readiness evidence paths

### Problem

This issue was opened under the older strict Hyperliquid-native historical
evidence interpretation. That interpretation made the absence of native
Hyperliquid historical as-of archives and requester-pays official S3 history a
blocking data-source conflict even after the repo had usable strict-free
multi-provider evidence.

WPR106-551 supersedes that data-source interpretation for the current product
scope. The authoritative data baseline is the strict-free/no-paid venue data
that can actually be collected, validated, and reproduced. Missing
requester-pays or otherwise uncollectable native Hyperliquid historical data is
a provenance caveat only; it must not block final audit, agentic research
handoff, data readiness, or future readiness evidence packets.

### Evidence

During WPR106-528, the autonomous readiness CLI was run against the latest
local public diagnostic cycle with no checklist evidence supplied:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main audit autonomous-readiness --evidence-file <temp>\public_diagnostic_readiness_evidence.json --output-path <temp>\public_diagnostic_readiness_report.json
# status=blocked
# autonomous_research_ready=false
# blocker_count=88
```

The report blocked on missing manager checklist evidence, the local public
cycle status `completed_with_blockers`, public/current-window blocker reasons,
validation failure, missing historical as-of universe and accepted historical
candle coverage, missing independent completion audit evidence, and missing
authoritative full-suite evidence for that cycle. WPR106-528 also found and
fixed a readiness-manager alignment gap: stale pre-WPR106-522 cycle evidence
that omits `backtest_data_load` and backtest-data/data-manifest refs now blocks
readiness.

WPR106-529 re-probed the current worktree and latest local evidence. The
autonomous readiness CLI was run against
`data/research/wpr106_469_public_diagnostic_cycle/rerun_after_wpr106_471/wpr106-469-public-cycle-ledger-fix/**`
with the current cycle execution, final audit report, ledger, and Lead Book
paths supplied:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main audit autonomous-readiness --evidence-file <temp>\public_diagnostic_readiness_evidence.json --output-path <temp>\public_diagnostic_readiness_report.json
# status=blocked
# autonomous_research_ready=false
# blocker_count=89
```

The latest cycle remains `completed_with_blockers`, still carries
`sandbox_diagnostic_non_evidence`, `public_api_current_universe_not_historical_asof`,
`public_api_recent_window_non_evidence`,
`accepted_historical_coverage_proof_required`,
`independent_completion_audit_required`, and
`authoritative_full_suite_validation_required`, and its execution/final-audit
artifacts still lack the current `backtest_data_load` and backtest-data
manifest criteria. The ledger and Lead Book paths are nonempty, but the ledger
row is `sandbox_diagnostic`, the run manifest uses `universe_mode=current`,
and the validation gate failed with `cost_dependent_failure`. The local
WPR106-473 historical dataset reports are also not accepted evidence: they
state `accepted_research_ready=false`, `evidence_mode=sandbox_diagnostic`, and
`universe_mode=current_labeled_sandbox`; the largest top-25 daily run collected
25/25 instruments but only 14/25 passed technical coverage, and the 2024 H1
1h run collected 0/10 instruments.

WPR106-530 repeated the current-manager probe against the same latest local
public diagnostic cycle with no synthetic checklist evidence supplied:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main audit autonomous-readiness --evidence-file <temp>\public_diagnostic_readiness_evidence.json --output-path <temp>\public_diagnostic_readiness_report.json
# status=blocked
# autonomous_research_ready=false
# blocker_count=89
```

The WPR106-530 probe confirms no new real accepted bounded-loop evidence is
present in the current worktree. The cycle execution is still
`completed_with_blockers`, still lacks a `backtest_data_load` job, and still
blocks on public/current-window evidence, missing historical as-of universe
evidence, missing accepted historical candle coverage, missing independent
completion audit evidence, and missing authoritative full-suite evidence for
that cycle. The final audit is still `completed_with_blockers` and lacks the
current backtest-data/data-manifest requirements. The current public-cycle
backtest-data request row exists but is `evidence_mode=sandbox_diagnostic`.
The ledger is nonempty but its row is `evidence_mode=sandbox_diagnostic`,
`universe_mode=current`, and `validation_status=fail`; the Lead Book is
nonempty but remains `idea_only` with known blockers and missing-evidence
fields for the required real evidence. The standalone WPR106-468 universe
refresh is `current_labeled_sandbox` with
`accepted_research_evidence_allowed=false`, and all WPR106-473 historical
dataset reports remain `accepted_research_ready=false`,
`evidence_mode=sandbox_diagnostic`, and
`universe_mode=current_labeled_sandbox`.

WPR106-531 attempted an evidence buildout from the current worktree and found
no eligible accepted inputs to run. The local Hyperliquid operator historical
dataset roots contain raw/bronze/silver candle material, but 11 inspected
`universe_snapshots.parquet` files all contain 230
`current_labeled_sandbox` rows with
`accepted_research_evidence_allowed=false`; no historical `as_of` accepted
universe row is present. The WPR106-473 coverage manifests are all
`evidence_mode=sandbox_diagnostic`; the largest top-25 daily run has 25
coverage rows, 14 full-coverage rows, and a minimum coverage ratio of
`0.18253968253968253`, but still has no accepted coverage proof and no
historical as-of universe proof. WPR106-469 has nonempty ledger and Lead Book
outputs, but they remain sandbox/current diagnostic outputs (`idea_only` Lead
Book, sandbox backtest-data requests, and sandbox ledger rows). Running an
archive-ref bounded loop from these inputs would relabel non-evidence as
accepted evidence, so no WPR106-531 evidence was generated.

WPR106-532 autonomously exercised the strict-free public intake path in the
current worktree. The native Hyperliquid public collector can download useful
diagnostic daily data, but it still cannot supply accepted readiness evidence.
The old BTC/ETH/SOL 1h public attempt for 2024-01-01 through 2024-01-08
collected 0/3 instruments and skipped all validation rows with
`hyperliquid_candle_window_empty`. A current-public daily top-5 smoke collected
4/5 instruments with full technical coverage, and a broader 2024-01-01 through
2026-06-01 current-public daily run collected 30/30 selected current eligible
instruments with 20/30 full-coverage rows, `min_coverage_ratio=0.182539682540`,
29 Binance sanity passes, and 1 Binance warning. All WPR106-532 universe
manifests contain 230 `current_labeled_sandbox` rows and 0 accepted universe
rows; all generated coverage rows are `evidence_mode=sandbox_diagnostic`, and
all reports state `accepted_research_ready=false` with the caveat
`current_public_universe_not_historical_asof`. The added external venue and
downloader surfaces remain comparison/context capabilities and cannot be
converted into Hyperliquid-native historical as-of readiness proof.

WPR106-533 records the operator-approved decision to create a separate
multi-venue/proxy research lane where non-paid Binance, Bybit, and Hyperliquid
candles can be treated as comparable research inputs, with Hyperliquid priority
when it has usable coverage and passes quality checks. That packet collected
218,735 normalized non-paid Binance USD-M and Bybit linear candle rows under
`data/research/wpr106_533_multi_venue_proxy_intake/**` for the 30 WPR106-532
Hyperliquid-current symbols. The quality report keeps Hyperliquid as the
priority daily venue for 20 symbols, marks 18 symbols usable for the
Binance/Bybit 2024 H1 1h proxy lane, and blocks 12 symbols for insufficient
coverage or missing rows. This is useful proxy-readiness evidence, but it is
historically was not treated as readiness evidence under the older
Hyperliquid-native interpretation.

WPR106-534 centralizes the strict-free multi-provider market-history lane under
`data/research/central_market_history/**`. The generated batch writes 221462
deduped normalized rows from Hyperliquid public metadata/recent candles,
Binance Vision futures/spot archives, bounded Binance aggTrade/orderflow rows,
Bybit public API/archive candles, and bounded Bybit trading archive rows. The
central data-readiness report is allowed to pass when at least one no-paid
provider/timeframe group is usable, so it does not fail solely because a
Hyperliquid history window is missing. That readiness is data-storage readiness
only: it does not supply historical as-of Hyperliquid universe proof, accepted
Hyperliquid-native historical coverage proof, bounded-loop strategy evidence,
independent audit evidence, or authoritative full-suite evidence required to
close this issue.

WPR106-535 expands the same central store under a hard 150 GiB local cap. The
store now uses about 3.202 GiB and contains 1,489,783 normalized rows across
Bybit linear, Binance USD-M, Hyperliquid, Binance spot, and Bybit spot. It
also makes the non-conflicting data-lane rule explicit for future agents: the
central market-history data-readiness lane is not strict Hyperliquid-only and
must not fail solely because Hyperliquid history is missing for a
symbol/window when valid comparable no-paid provider data exists. This remains
data-storage readiness only and still does not provide the real
Hyperliquid-native bounded-loop strategy evidence required to close this
issue.

WPR106-536, WPR106-537, WPR106-538, WPR106-539, WPR106-540, and WPR106-541
continue expanding the central store under the same 150 GiB cap. WPR106-536 adds
BTC/ETH January 2024 trade, orderflow, spot-trade, premium-index, and
spot-index history; WPR106-537 adds SOL, BNB, XRP, and DOGE January 2024
Binance USD-M/Bybit linear trade/orderflow history; WPR106-538 adds ADA, AVAX,
LINK, SUI, LTC, DOT, TRX, UNI, and FIL January 2024 Binance USD-M
aggregate-trade/orderflow history; WPR106-539 adds BTC, ETH, SOL, BNB, XRP,
and DOGE February 2024 Binance USD-M aggregate-trade/orderflow history;
WPR106-540 adds ADA, AVAX, LINK, SUI, LTC, DOT, TRX, UNI, and FIL February
2024 Binance USD-M aggregate-trade/orderflow history; WPR106-541 adds BTC early
March, full BNB March, and full XRP March 2024 Binance USD-M/Bybit public
trade/orderflow history while recording exact BTC/ETH/SOL/DOGE March
continuation URLs as `deferred_next_packet`. Bybit public trading 404s and
bounded-pass deferrals are retained as provider-specific source status rather
than central-readiness failures. The central store now uses about 25.014 GiB
and contains 7,993,343 normalized rows. This is still central market-history
data readiness only, not an autonomous-readiness report.

WPR106-543 updates the active central market-history storage cap to 300 GiB,
adds bounded parallel official no-paid archive collection with atomic `.part`
downloads, source validation, source-discovery reports, quality reports, and
progress telemetry, and completes the remaining WPR106-541/WPR106-542 March
continuation targets: ETH March 18-31, BTC March 5-31, and full SOL/DOGE March
2024 Binance USD-M/Bybit public trade/orderflow history. The packet adds
1,030,000 normalized rows from 206 official no-paid source probes with zero
source blockers, leaving the central store at about 37.184 GiB, 9,193,343
normalized rows, and 174 append-manifest rows under the 300 GiB cap. This
remains central market-history data readiness only and still does not provide
the real Hyperliquid-native bounded-loop strategy evidence required to close
this issue.

### Required resolution

Close the data-source conflict by making the strict-free/free-venue baseline
authoritative in the product scope, autonomous readiness contract, data
catalog, static visibility page, issue register, and readiness-manager next
actions. Future readiness evidence may point to the WPR106-546 project bars,
WPR106-549/WPR106-550 external raw-heavy OF-style archive, central manifests,
coverage reports, archive snapshots, and universe snapshots. It must not ask
agents to obtain native Hyperliquid official S3 history that is outside the
strict-free constraint.

Future autonomous readiness reports still need real current artifact paths,
passing final durable audit, authoritative validation, independent audit
evidence when required, clean target-state evidence when claimed, and zero open
P0/P1 counts. Those are readiness-evidence requirements, not open data-source
blockers.

### Resolution notes

Resolved by WPR106-551 as a data-source/readiness-policy conflict. The older
Hyperliquid-native blocker is out of the picture for this branch's current
strict-free research scope. The WPR106-546 lifecycle-scoped official Binance
USD-M 1m project bars and WPR106-549/WPR106-550 external raw-heavy OF-style
archive are the authoritative data baseline for final audit and agentic
research handoff.

WPR106-552 adds the compact normalization/feature materialization proof for
that baseline. The materializer parsed 81,093,159 rows from 251 official
source files and wrote 256,523 research-only feature rows with zero blocked
sources across the nine requested OF-style families. Full all-file
feature-panel expansion is a compute scope decision, not a renewed
data-source blocker.

This resolution does not create a candidate pack, accepted autonomous-readiness
report, strategy-performance claim, paper/live signal, order placement, sizing
instruction, runtime-mode change, promotion behavior, or production trading
readiness. It resolves the data conflict so future agents work with the data
that exists and stop treating unavailable native Hyperliquid official history
as a blocker.

## ISSUE-R106-031: Active v2 reference-derivatives endpoint violates removed-source boundary scan

Severity: P1
Stage discovered: final independent audit after WPR106-526
Owner: Codex Manager Development Agent
Status: resolved by WPR106-527
Paths affected: `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`,
`tests/v2/test_reference_derivatives_availability_phase59.py`,
`tests/v2/test_reference_derivatives_fetch_normalize_phase60.py`

### Problem

The Python 3.11 monolithic suite failed at
`tests/test_removed_source_boundaries.py::test_removed_vendor_source_surfaces_stay_out_of_active_tree`
because active v2 reference-derivatives code used a removed vendor source token
in the Deribit public candle endpoint identifier and REST path literal.

### Evidence

During final independent audit validation:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
# 1 failed, 2457 passed, 2 skipped
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/test_removed_source_boundaries.py -q
# failed with offenders in src/tradingbotsuite/v2/data_sources/reference_derivatives.py
```

The failure was deterministic and not the local Windows `socket.socketpair()`
pytest setup caveat.

### Required resolution

Remove the removed source token from active source and test identifiers without
weakening the removed-source boundary test. Preserve the Deribit public candle
request behavior as research-only external comparison metadata and keep all
outputs non-native, non-accepted as historical coverage proof, non-candidate,
and non-promotable.

### Resolution notes

Resolved by WPR106-527. The Deribit reference endpoint now uses a neutral
internal endpoint ID, while the public REST path is constructed without the
removed token as a contiguous active-tree literal. Focused reference-derivatives
tests were updated to the neutral endpoint ID. No archive writes, accepted
research readiness, candidate pack, paper/live behavior, order placement,
sizing, runtime-mode change, or promotion behavior was introduced.

## ISSUE-R106-030: Hyperliquid public candleSnapshot old intraday windows return empty

Severity: P2
Stage discovered: WPR106-473 - V2 historical perp dataset collection validation
Owner: Codex Research Agent
Status: resolved by WPR106-526
Paths affected: public Hyperliquid historical data operation,
`src/tradingbotsuite/v2/collectors/historical_dataset.py`,
generated `data/research/operator_runs/v2_historical_dataset/**` reports

### Problem

The WPR106-473 historical-perps command can collect old daily Hyperliquid
candle history, but direct public `/info` `candleSnapshot` requests for old
1h windows returned no rows. Binance USD-M public klines did return matching
old 1h rows for the same BTCUSDT window, so Binance can be used as
cross-venue/proxy sanity data, but it is not Hyperliquid ground truth.

### Evidence

During WPR106-473 on 2026-06-22:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\operator_runs\v2_historical_dataset --run-id wpr106-473-liquid10-1h-2024h1 --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2024-07-01T00:00:00+00:00 --timeframe 1h --asof-date 2026-06-22 --max-instruments 0 --coin BTC --coin ETH --coin SOL --coin ZEC --coin WLD --coin SUI --coin NEAR --coin XRP --coin AVAX --coin UNI --binance-timeout 20 --max-public-info-pages 20
# selected_instrument_count=10
# collected_instrument_count=0
# binance_skipped_count=10
```

A direct provider probe showed:

```text
Hyperliquid BTC 1h 2024-01-01..2024-01-08: 0 rows
Hyperliquid BTC 1d 2024-01-01..2024-01-08: 8 rows
Hyperliquid BTC 1h 2026-06-01..2026-06-08: 169 rows
Binance BTCUSDT 1h 2024-01-01..2024-01-08: HTTP 200 with rows
```

### Required resolution

Before claiming accepted Hyperliquid intraday evidence, use a trusted
historical Hyperliquid source that actually supplies old intraday candles, or
import a manifest-backed official/vendor archive with provenance and coverage
proof. If Binance is used for 1h/15m research iteration, label it explicitly
as cross-venue/proxy data and do not treat it as accepted Hyperliquid
execution or venue-specific evidence.

### Resolution notes

Resolved by WPR106-526 as an operational collector gap. A fresh public probe on
2026-06-24 still returned zero BTC 1h rows for 2024-01-01 through 2024-01-08,
so the public `candleSnapshot` endpoint remains recent-window only and is not
the resolution path for old intraday coverage.

`redx collectors historical-perps` now supports explicit
`candle_source=trusted_records` / `--candle-source trusted_records` intake for
operator-supplied Hyperliquid-native candle JSON/JSONL files. That mode
requires a trusted source root, keeps file paths root-contained, rejects unsafe
file names/extensions, records file SHA-256 and row-count provenance, filters
rows to the requested window, validates symbol/timeframe/candle shape, writes
selected rows through the existing raw -> bronze -> silver archive pipeline,
and emits coverage evidence in the generated report. Reports remain
`sandbox_diagnostic` and `accepted_research_ready=false`; final acceptance
still requires as-of universe, archive snapshot, coverage, lockbox,
backtest-data, validation, ledger, audit, and readiness gates. Binance remains
cross-venue/proxy sanity data only.

## ISSUE-R106-029: Direct v2 worker-store import can hit data-quality circular import

Severity: P2
Stage discovered: WPR106-433 - V2 public Hyperliquid candle collector
Owner: Codex Manager Development Agent
Status: resolved by WPR106-437
Paths affected: `src/tradingbotsuite/v2/data_quality/__init__.py`, `src/tradingbotsuite/v2/workers/job_store.py`

### Problem

A fresh interpreter import of `WorkerJobStore` can fail when
`tradingbotsuite.v2.workers.job_store` imports archive helpers, archive rebuild
loads `tradingbotsuite.v2.data_quality.coverage`, and the `data_quality`
package eagerly imports `data_quality.jobs`, which imports `WorkerJobStore`
again while the module is only partially initialized.

The CLI worker entrypoint and the existing test import order still work, so this
is not a current stage stopper. It is a programmatic import-order risk for
standalone worker scripts and optional smoke utilities.

### Evidence

During WPR106-433 optional smoke work on 2026-06-21, this failed:

```powershell
$env:PYTHONPATH='src'
python -c "from tradingbotsuite.v2.workers.job_store import WorkerJobStore; print('worker-store-direct-import-ok')"
```

The command raised `ImportError: cannot import name 'WorkerJobStore' from
partially initialized module 'tradingbotsuite.v2.workers.job_store'`. The normal
CLI path still passed:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.v2.cli.main worker --help
```

An optional public-candle smoke also succeeded after importing the archive
package before worker modules.

### Required resolution

Use a scoped test-infrastructure or package-boundary packet to remove the eager
`run_data_quality_job` import from `tradingbotsuite.v2.data_quality.__init__`
or make it lazy, then add a fresh-interpreter regression for direct
`WorkerJobStore` import. Preserve existing package exports for callers that use
`from tradingbotsuite.v2.data_quality import run_data_quality_job`.

### Resolution

WPR106-437 replaces eager `tradingbotsuite.v2.data_quality` and
`tradingbotsuite.v2.archive` package exports with lazy `__getattr__` shims for
the exported symbols involved in the cycle. Fresh-interpreter regressions prove
both direct `WorkerJobStore` import and
`from tradingbotsuite.v2.data_quality import run_data_quality_job` succeed.

Validation evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_import_boundaries_phase25.py -q
# 2 passed
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 224 passed
python -m compileall -q src/tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
$env:PYTHONPATH='src'; python -c "from tradingbotsuite.v2.workers.job_store import WorkerJobStore; from tradingbotsuite.v2.data_quality import run_data_quality_job; print(WorkerJobStore.__name__, callable(run_data_quality_job))"
# WorkerJobStore True
```

## ISSUE-R106-026: Windows socket exhaustion blocks pytest-asyncio contract setup

Severity: P2
Stage discovered: Stage R106 - sandbox archive manifest builder validation
Owner: Codex Research Agent
Status: resolved by WPR106-472
Paths affected: local Windows validation environment, `tests/contracts/test_historical_fixture_pack_contract.py`

### Problem

The contract baseline can be blocked by local Windows socket resource
exhaustion before an async contract test body runs. Pytest-asyncio creates an
event loop self-pipe with `socket.socketpair()`, and the current host can fail
that setup with `WinError 10055`.

### Evidence

During WPR106-239 validation on 2026-06-18, `python -m compileall -q
src\tradingbotsuite` passed, focused sandbox/live-boundary/import-boundary
validation passed, but repeated contract-baseline attempts failed during setup
of
`tests/contracts/test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`.
The failure occurred while creating the asyncio event loop socketpair, before
the test body ran. A targeted rerun of the same test failed the same way, and
an explicit `WindowsSelectorEventLoopPolicy` attempt also failed at
`socket.socketpair()`.

WPR106-240 reproduced the same local blocker: focused sandbox,
live-boundary, import-boundary, and package compile validation passed, while
`PYTHONPATH=src python -m pytest tests/contracts -q` reached 460 passed tests
and then failed during the same async test's event-loop socketpair setup before
the test body ran.

WPR106-241 reproduced the same local blocker: focused sandbox,
live-boundary, import-boundary, and package compile validation passed, while
`PYTHONPATH=src python -m pytest tests/contracts -q` again reached 460 passed
tests and then failed during the same async test's event-loop socketpair setup
before the test body ran.

WPR106-243 reproduced the same local blocker: focused sandbox,
import-boundary, and package compile validation passed, while
`PYTHONPATH=src python -m pytest tests/contracts -q` reached 460 passed tests
and then failed during the same async test's event-loop socketpair setup before
the test body ran.

WPR106-417 reproduced the blocker during a v2 completion audit on
2026-06-21. Full package compile, contract tests, v2 tests, and many grouped
non-v2 suites passed, but monolithic and async/operator broad-suite validation
could not be certified in the Windows session. Failures were again in
`socket.socketpair()` while pytest-asyncio or Starlette/FastAPI TestClient was
creating event loops, with `WinError 10055` occurring before the affected test
bodies ran. A short cooldown sometimes made a direct `socket.socketpair()`
probe pass again, but the async test process could still exhaust the same host
resource. A temporary Python 3.11 validation environment outside the repo
confirmed the same underlying socketpair failure after the host entered the
bad state, so the audit kept this classified as a local validation-environment
blocker rather than a source assertion failure.

WPR106-420 installed the repo runtime/dev dependencies into the local Python
3.11.0 interpreter and proved the pinned v2 and contract lanes can run:
`py -3.11 -m pytest tests\v2 -q` passed 173 tests and
`py -3.11 -m pytest tests\contracts -q` passed 462 tests. The packet also
fixed a deterministic v2 worker transition ordering issue exposed by the
pinned lane. The monolithic `py -3.11 -m pytest tests -q` suite still could
not be certified: a long-process prefix failed before
`test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`
because Python 3.11.0 on this Windows host hit `WinError 10055` while creating
the asyncio loop self-pipe with `socket.socketpair()`. A direct post-run
`socket.socketpair()` probe also failed after four attempts even with no
leftover Python test processes, so the issue remains classified as a local
Windows/Python socket-stack validation blocker.

WPR106-421 reproduced the same blocker on the default Python runtime while
running an extra full `tests\contracts` sweep after packet-required validation
had passed. The run reached 462 passed tests and then failed during
`test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`
setup because Python failed to create the pytest-asyncio event-loop self-pipe
with `WinError 10055`; compile, diff hygiene, focused contracts/backtesting,
v2, and historical lanes all passed separately.

### Required resolution

Before using this Windows session as final full-suite evidence again, clear or
restart the local socket/network stack enough for pytest-asyncio event-loop
setup to succeed, then rerun both `PYTHONPATH=src py -3.11 -m pytest tests -q`
and default-Python `PYTHONPATH=src python -m pytest tests\contracts -q`. If
the condition persists across fresh sessions, use Linux CI as the authoritative
full-suite lane or add a scoped test-infrastructure packet that avoids
socketpair-dependent async setup for local contract tests without weakening the
async behavior under test.

### Resolution notes

Resolved by WPR106-472. The local Windows Python 3.11 validation lane now has
fresh full-suite evidence:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
# 2235 passed, 2 skipped, 6 warnings in 764.88s
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
```

The previous blocker is closed as a local environment/resource condition, not a
source assertion failure. This resolution does not create a sandbox
manifest-builder assertion change, candidate-pack write, paper/live signal,
sizing instruction, order placement, runtime-mode change, autonomous-ready
claim, or promotion claim.

WPR106-526 further removes the last pytest-asyncio dependency from
`tests/contracts` by converting the collected Binance context fixture-pack
contract to a synchronous collected-manifest fixture. Broader async/TestClient
suites can still hit host-level `WinError 10055` on exhausted local Windows
sessions, but the contract baseline no longer requires event-loop setup for
that fixture-pack assertion.

## ISSUE-R106-027: Official S3 backfill accepted arbitrary local source files

Severity: P1
Stage discovered: WPR106-418 v2 foundation baseline stabilization
Owner: Codex Manager Development Agent
Status: resolved
Paths affected: `src/tradingbotsuite/v2/archive/microstructure.py`, `src/tradingbotsuite/v2/collectors/jobs.py`, `tests/v2/test_microstructure_collection_phase17.py`

### Problem

The v2 official S3 backfill preservation path accepted a caller-controlled
`source_file` and only checked that it was a local file before copying it into
the raw archive. A malformed or careless job spec could copy `.env`,
credential files, local SQLite databases, or private cache files into archive
storage, which conflicts with the v2 no-touch registry for secrets and local
state.

### Evidence

The WPR106-418 boundary subagent found that
`_run_official_s3_backfill_job()` passed `source_file` directly to
`preserve_official_s3_backfill_file()`, and that preservation only checked
`Path(source_file).is_file()` before writing archive output and manifest rows.

### Required resolution

Official-file preservation must require a trusted source root, resolve source
files inside that root, reject traversal and secret/local-state file names
before archive writes, and add regressions proving rejected inputs do not write
raw files or manifest rows.

### Resolution notes

Resolved by WPR106-419. Official S3 backfill jobs now require
`trusted_source_root`; source paths are resolved under that root; traversal,
`.env`, credential/key-like names, and local database/cache suffixes fail before
archive layout writes or manifest rows. Focused tests cover valid preservation
and rejected `.env`, credential, and traversal sources. The fix does not create
candidate-pack, paper/live, order, sizing, runtime-mode, or promotion behavior.

## ISSUE-R106-028: Signal-bearing v2 artifacts omitted full boundary invariant

Severity: P1
Stage discovered: WPR106-418 v2 foundation baseline stabilization
Owner: Codex Manager Development Agent
Status: resolved
Paths affected: `src/tradingbotsuite/v2/strategy_specs/schemas.py`, `src/tradingbotsuite/v2/backtest_engine/engine.py`, `tests/v2/test_strategy_specs_phase10.py`, `tests/v2/test_backtest_engine_phase11.py`

### Problem

Some v2 artifacts carrying `signal` or weight fields only emitted
`research_only`, `observe_only`, and `promotion_ready` boundary fields. The
canonical v2 invariant also requires explicit false values for candidate,
paper/live signal, sizing, order-placement, and runtime-mode fields. Omitting
those fields made signal-bearing artifacts less self-describing than the
product-scope invariant requires.

### Evidence

The WPR106-418 boundary subagent found that `SignalRow`, `SignalFrame`,
`positions.parquet`, and `trades.parquet` omitted some canonical forbidden
flags even though those artifacts include strategy signal or target-weight
columns.

### Required resolution

Add the full canonical invariant to signal rows/frames and signal-bearing
backtest artifacts, validate that forbidden flags remain false, and add tests
for serialized signal rows plus Parquet columns and values.

### Resolution notes

Resolved by WPR106-419. Signal rows and frames now carry and validate the full
research-only invariant. Vectorized backtest positions and trades now write the
same invariant columns with forbidden flags set false. Focused tests assert the
compiled signal-frame fields and Parquet columns/values. The fix adds explicit
false boundary evidence only; it does not authorize candidate-pack, paper/live,
order, sizing, runtime-mode, or promotion behavior.

## ISSUE-R106-025: May 2026 holdout archive is not yet available locally

Severity: P2
Stage discovered: Stage R106 - 2024-forward broad strategy search
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/historical_data_cache/binance_vision_public_archive/downloads/**`, `data/research/wpr106_85_2024_forward_pre_may_archive_map/**`, future 2026-05 holdout benchmark artifacts

### Problem

WPR106-85 requires May 2026 to remain fully out of tuning and to be used only
as a benchmark holdout for promising leads. The current local Binance Vision
archive cache for BTCUSDT and ETHUSDT has monthly 15m, 1m, and aggTrade ZIPs
through 2026-04, but no 2026-05 monthly archives were present at audit time.

### Evidence

WPR106-85 mapped BTCUSDT and ETHUSDT no-RSI four-bar datasets from local
archives for 2024-01 through 2026-04 under
`data/research/wpr106_85_2024_forward_pre_may_archive_map/`. The generated
datasets contain rows from 2024-01-01 00:00:00 UTC through
2026-04-30 22:45:00 UTC and no 2026-05 rows. Directory audits of the local
Binance Vision cache found `BTCUSDT`/`ETHUSDT` 15m, 1m, and aggTrade monthly
ZIPs ending at `2026-04`.

WPR106-92 produced one pre-May loose holdout candidate,
`ETHUSDT` `eth-1h-4h-wick-flow-lorentzian-compatible-lower-meta`, with 564
meta trades, +0.069117 net after costs, +0.000123 expectancy, 2.452 trades per
active day, 10 active months, 5 positive months, 5 losing months, max
positive-month profit share 0.335295, and max split PnL share 0.366382. The
packet could not run the required May 2026 benchmark because the local May
archive dependency described by this issue remains unresolved.

WPR106-93 resolved the ETHUSDT portion needed for that specific benchmark by
downloading `ETHUSDT` May 2026 15m kline, 1m kline, and aggTrades ZIPs plus
their Binance Vision checksum sidecars. All three checksums verified. The
benchmark rejected the WPR106-92 ETHUSDT row: May 2026 meta-model holdout
recorded 268 trades, -0.353937 net after costs, -0.001321 expectancy, 10
positive days, 21 losing days, and -0.365293 max trade-sequence drawdown. Pure
KNN was also negative. No tuning feedback, candidate pack, paper/live artifact,
sizing, runtime, live-config, or promotion claim was created. The issue remains
open only because BTCUSDT May 2026 archive completeness has not yet been
verified for future BTC holdout benchmarks.

WPR106-95 found 40 pre-May cross-family portfolio-combination diagnostic leads
that pass loose monthly-stability screening without using May 2026. The leading
combinations include BTCUSDT sleeves, so this issue is now the immediate
dependency for any May benchmark of those combinations. They remain
research-only and not candidate-ready until BTCUSDT May 2026 archive data is
verified and the selected combination is benchmarked without tuning feedback.

WPR106-96 resolves the BTCUSDT portion by adding and checksum-verifying
BTCUSDT May 2026 15m kline, 1m kline, and aggTrades archives in the local
public-archive cache. It also reuses and re-verifies the WPR106-93 ETHUSDT May
files, writes a May archive intake manifest, materializes 2024-01 through
2026-05 feature context for the selected WPR106-95 rank-1 sleeves, and
benchmarks `combo-d9edcc252c323b03` on May entries without May tuning. The
holdout records 25 member trades, 20 active days, 1.250 trades per active day,
0.250 overlap-day share, and +0.026603 equal-sleeve portfolio return.

### Required resolution

Before any later promising 2024-forward BTCUSDT lead can receive the required
May 2026 benchmark, add a scoped intake or local-cache refresh packet for
BTCUSDT May 2026 archive data. Future non-ETH families must also verify their
required May source files before benchmarking. The packet must preserve
checksum/hash evidence, gap/duplicate checks, completed-bar semantics,
research-only metadata, and must not use May 2026 for tuning or candidate
selection.

### Resolution notes

Resolved by WPR106-96. BTCUSDT and ETHUSDT May 2026 archive dependencies for
the selected WPR106-95 portfolio benchmark are now locally verified with
checksum/hash, gap/duplicate, completed-bar, and aggTrade aggregation evidence.
The issue is resolved as a data/benchmark dependency only; it does not create a
candidate-ready, paper-ready, live-ready, or promotion-ready claim.

## ISSUE-R106-024: Candidate gate cannot yet represent explicit one-sided side-veto evidence

Severity: P2
Stage discovered: Stage R106 - sparse side-veto validation
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/**`, `src/tradingbotsuite/optimization/stability.py`, `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/**`, `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/**`

### Problem

WPR106-81 added explicit `allowed_sides` and `side_filter_stage` controls to
`sparse_event_filter_v1`. The post-selection long-only sparse rows can rank
above no-trade and survive split plus cost-stress evidence, but the current
candidate gate still expects same-candidate long/short side evidence. That
gate assumption is too broad for explicit one-sided strategies whose opposite
side is intentionally vetoed and separately tested as a control.

### Evidence

The WPR106-81 BTCUSDT side-veto cycle wrote
`data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/`. The rank
1 aggTrade-contrarian post-selection long row recorded 346 long trades, net
return after cycle costs of +9.420343, split trade-count minimum 116, and
cost-stress survival rate 1.0, but remained rejected with
`candidate_side_evidence_long_short_required` plus feature-ablation and
stability-region blockers.

### Required resolution

Before any explicit one-sided side-veto row can be candidate-pack eligible,
the gate should distinguish one-sided strategy contracts from missing side
evidence. A valid resolution should require paired opposite-side controls,
feature ablations, split/cost/stability evidence, and research-only provenance
without requiring both sides inside the same candidate.

Until resolved, WPR106 one-sided side-veto rows can only support optimizer
follow-up research. They cannot support candidate-pack, paper, live, sizing,
runtime-mode, or promotion claims.

### Progress notes

WPR106-82 confirmed the blocker after optimizer follow-up. The optimized
aggTrade-contrarian post-selection long row
`941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`
recorded +20.174216 net return after cycle costs, 319 long trades, minimum
split trade count 109, and 11/11 cost-stress scenarios passed, but remains
fail-closed on one-sided side evidence, feature ablation, and
stability-region requirements.

WPR106-84 resolves the gate representation blocker by adding explicit
one-sided side-veto semantics to the historical-cycle gate and candidate-pack
recheck. Declared one-sided `sparse_event_filter_v1` rows now require the
declared side, an exact paired opposite-side control with matching non-side
parameters, no-trade and transparent baseline evidence, feature ablation,
split, cost-stress, stability, and research-only provenance. The packet also
separates opposite-side controls from same-side stability neighborhoods and
fixes side metric accounting by writing compounded side return plus a separate
summed-return field.

The focused BTCUSDT evidence cycle at
`data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/`
shows the optimized lead has complete one-sided side-veto evidence, a passed
short control
`3518d10a359694814ef453358ed3a26b0b24065bfb749d265a5b3ab1b7ee4809`, a passed
price-only feature ablation comparator
`9af7ae11c5165cd12555125e59cca4eae99149800a74c2b05a8f1a9781d666ce`, 11/11
cost-stress survival, and accepted stability. The lead is still rejected by
split concentration with `max_single_split_pnl_share_above_limit`
(`0.9765691016445411`). No candidate pack, paper/live artifact, order, sizing,
runtime-mode change, live configuration write, or promotion claim exists.

## ISSUE-R106-023: Compact four-bar fixtures cannot support larger HMM/KNN walk-forward validation

Severity: P1
Stage discovered: Stage R106 - four-bar larger validation run
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/fixtures/*public_archive_multi_window_v1`, `data/research/hmm_knn_four_bar_validation/*`, `src/tradingbotsuite/research/knn_four_bar_validation.py`, `configs/research/no_rsi_knn_four_bar_*_r106_v1.json`

### Problem

The WPR106-76 four-bar no-RSI dataset contract is present, but the current
durable BTC/ETH fixture roots are compact contract fixtures, not large enough
to run HMM/KNN walk-forward validation. A larger-validation run can build the
schema and labels but cannot form valid split objects or meet walk-forward size
requirements.

### Evidence

WPR106-78 ran:

`PYTHONPATH=src python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_78_full_run --sample-rows-per-interval 8000 --workers 1 --skip-monitor`

The process completed and wrote
`data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/`, but both
generated datasets contain only 64 rows per symbol. The dataset manifests trace
that to compact source fixtures with 32 cycle rows per symbol, plus 480
lower-timeframe rows and 480 aggTrade rows. Both BTCUSDT and ETHUSDT matrices
failed:

- 15m->1h selected rows: `ValueError: No objects to concatenate`.
- 1h->4h selected rows: `ValueError: dataset is too small for HMM/KNN walk-forward research`.

No summary records, gate-pass records, candidate packs, paper/live artifacts,
or promotion evidence were produced.

### Required resolution

Before drawing larger-validation conclusions from KNN/filter rows, either map
an existing larger local BTC/ETH archive into the WPR106-76 four-bar dataset
contract or open a venue-derived feature intake packet for sufficient BTC/ETH
history. Required intake should preserve bars, lower-timeframe bars, aggTrade
or equivalent trade-flow proxies, event-end/purge metadata, fixed four-bar
labels, and explicit missingness for funding/open-interest/premium/basis
context when absent. Optional OKX/Bybit/Binance intake design may add funding,
open interest, premium/basis, and crowding context, but all outputs remain
research-only, observe-only, and `promotion_ready: false`.

Until resolved, WPR106 four-bar KNN larger validation was blocked by data
coverage and could not support candidate, paper, live, sizing, runtime-mode, or
promotion claims.

### Progress notes

WPR106-79 adds a research-only local Binance Vision archive mapper and
operator job for the first required resolution path. The mapper reads existing
local BTCUSDT/ETHUSDT monthly archive ZIPs, writes the WPR106-76 four-bar
dataset contract, preserves event-end/purge semantics, samples only after
fixed four-bar labels are built, and writes a replay command for the
archive-backed HMM/KNN matrix.

### Resolution notes

Resolved by WPR106-79 follow-up execution on 2026-06-09. The local archive
mapping run wrote BTCUSDT and ETHUSDT 2024 archive-backed datasets under
`data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/`.
Each symbol has 16,000 selected rows, with sampling after label construction
and same-entry fixed four-bar labels. The mapping manifest passes the research
boundary check, remains `research_only`, `observe_only`, and
`promotion_ready: false`, and records no live, sizing, or runtime-mode changes.

The generated archive-backed matrix replay completed for BTCUSDT and ETHUSDT:
both symbols wrote `matrices/<symbol>/experiment_manifest.json` and
`experiment_summary.csv`, each with 2/2 experiment rows passed and research
boundary checks passing. The tested rows remain promotion-blocked by research
status and negative/insufficient gate evidence, so this resolution clears the
data-coverage blocker only. It is not a KNN profitability conclusion, not an
exit-quality conclusion, and not promotion evidence.

## ISSUE-R106-021: Context exits can crash fast cycles when raw context columns are absent from the execution frame

Severity: P1
Stage discovered: Stage R106 - fast entry filter exit research
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `tests/historical/*`, `tests/backtesting/*`

### Problem

`funding_aware_exit_v1` and related context exits require raw context columns in
the primary-bar execution path. A fast latest-window context cycle can configure
those exits while the backtest frame lacks `funding_rate`, causing the cycle to
raise instead of writing a blocked or skipped comparison. This wastes fast
research iterations and makes context-exit coverage less reliable than fixed,
runner, and hard-stop exits.

### Evidence

`configs/research/fast_filter_probe_btcusdt_r106_v1.json` and
`configs/research/fast_filter_probe_ethusdt_r106_v1.json` initially included
`funding_aware_exit_v1`. Both fast-cycle launches failed on 2026-06-07 with
`ValueError: funding_aware_exit_v1 requires columns: funding_rate` during
aggregate candidate evaluation, before rankings were written.

### Required resolution

Either preserve validated context columns needed by context exits in the
research-cycle execution frame, or make unsupported context exits fail closed
per candidate with explicit blocker evidence. Add focused tests that exercise
latest-window context fixtures and verify no whole-cycle crash occurs when a
configured context exit lacks required context.

### Resolution notes

Resolved by WPR106-71. The research-cycle aggregate, split, and cost-stress
backtest paths now route context-exit column gaps through a fail-closed
candidate-level blocked backtest artifact instead of raising a whole-cycle
exception. Blocked rows record `exit_policy_context_unavailable`, negative
blocked metrics, `backtest_backend_used: blocked`, and the original context
column reason in rankings and backtest index evidence. The execution market
frame also preserves the `last_funding_rate` alias so funding-aware exits can
use any registered funding-rate alias that reaches the feature frame. Focused
regressions cover the funding alias and a synthetic historical cycle where
`funding_aware_exit_v1` lacks funding context. BTC/ETH fast-filter probes were
rerun with `funding_aware_exit_v1` restored; both completed, and each wrote 13
blocked price-feature funding-aware aggregate rows instead of crashing.

## ISSUE-R106-022: Combined price+aggTrade sparse-filter cost stress is too slow for compact validation

Severity: P2
Stage discovered: Stage R106 - sparse entry filter layer
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/research_cycle/runner.py`, `data/research/historical_cycles/sparse_entry_filter_*`

### Problem

WPR106-74 found aggregate-positive BTC sparse-filter rows that need split and
cost-stress follow-up, but full refinement over the combined
`features_price_perp_aggflow_no_wt` frame exceeded the compact iteration
budget. The feature builder also emits repeated pandas fragmentation warnings
when adding missingness columns for wide feature frames, which is likely adding
avoidable overhead.

### Evidence

The completed BTC sparse cycle wrote aggregate-positive sparse rows, but the
standard `top_regions_to_refine: 2` shortlist refined no-trade baselines before
the sparse rows. A follow-up full-cycle rerun with `top_regions_to_refine: 6`
remained active past the one-hour command timeout and was stopped. A bounded
offline audit of the two positive BTC sparse rows completed split backtests,
but full cost stress over the aggTrade-gated row was stopped after two of
eleven scenarios because each full-frame cost scenario was taking roughly ten
minutes. The output repeatedly warned:

`DataFrame is highly fragmented... Consider joining all columns at once using pd.concat(axis=1)`

### Required resolution

Open a focused performance/evidence packet before scaling sparse aggTrade
filters. Defragment wide feature-frame missingness construction or otherwise
make sparse-filter split/cost stress practical, and add a bounded test or
benchmark proving combined price+aggTrade sparse validation can complete
without exceeding compact-run budgets. Until then, aggregate-positive
aggTrade-gated sparse rows are diagnostic only and cannot support candidate,
paper, live, sizing, runtime-mode, or promotion claims.

### Resolution notes

WPR106-87 partially mitigated one sparse-filter bottleneck by caching
aggTrade flow-confirmation Series once per prediction frame in
`src/tradingbotsuite/strategies/sparse_event_filter.py`. That allowed the
BTCUSDT and ETHUSDT WPR106-87 sparse-event cycles to complete 74 aggregate
backtests and 60 validation backtests per symbol. WPR106-88 and WPR106-90 added
more completed sparse/exit-cycle data points, but WPR106-90 still emitted the
wide feature-frame fragmentation warning from missingness-column insertion.

WPR106-91 resolves the remaining feature-frame fragmentation portion by
batching missing manifest feature columns and missingness indicators with
`pd.concat` in `src/tradingbotsuite/features/packs.py`, then copying once to
defragment the final frame. The focused feature-builder regression
`test_price_perp_aggflow_no_wt_builds_wide_missingness_without_fragmentation_warning`
proves `features_price_perp_aggflow_no_wt` preserves missingness columns
without emitting pandas `PerformanceWarning`. The BTCUSDT and ETHUSDT
WPR106-91 active-rate density cycles each completed 134 wide-feature/transparent
candidate rows with split and cost-stress evidence using CPU execution and no
CUDA claim. The packet does not create a candidate, paper/live, sizing,
runtime-mode, or promotion claim; it only resolves this performance blocker for
continued research iteration.

## ISSUE-R106-020: Strategy and exit audit follow-up risks need focused tests

Severity: P2
Stage discovered: Stage R106 - strategy math audit and fast research nodes
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/strategies/*`, `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `src/tradingbotsuite/backtesting/cuda_engine.py`, `src/tradingbotsuite/backtesting/cuda_batched_engine.py`, `tests/contracts/test_strategy_contracts.py`, `tests/backtesting/*`, `tests/unit/test_execution_simulator.py`, `tests/historical/*`

### Problem

The WPR106-70 and WPR106-72 strategy/backtest audits found several
non-immediate follow-up risks that need focused packets before any promotion
interpretation is allowed. Perp context strategies and premium/basis exits
currently allow `quality_latest_window_context_only` rows when the rest of the
context quality passes; `gmm_transition_exit_v1` does not fail closed when
detector metadata is absent; fixed-holding time-exit aliases normalize trade
rows to `fixed_holding_window`, losing requested exit-policy identity;
lower-timeframe triple-barrier no-hit exits use the primary close while only
barrier hits use lower-frame OHLC sequence proof; fit-aware future strategies
would need an explicit train-context contract; cost-stress survival currently
combines per-trade expectancy with total net return in one scalar;
`volatility_scaled_barrier` is a static close-barrier in the current primary-bar
path despite its name; and funding-aware exits can trigger from path funding
context while realized funding-cost accounting is still based on the entry-row
funding-rate estimate.

### Evidence

The audit checked the current strategy registry, rule-based strategy outputs,
reference/vector/CUDA backtest engines, primary-bar and lower-timeframe exit
paths, split construction, and research-cycle gate aggregation. WPR106-70 fixes
the P1 deterministic issues found during the same pass: range reversion no
longer fabricates row-parity direction, `signal_bar_close_plus_latency` prices
from the latency-observable primary-bar open, and trade funding costs use the
available funding-rate alias columns. WPR106-72 sidecar review additionally
confirmed coherent sign conventions for trend, volatility breakout,
funding-crowding fade, perp-basis convergence, OI-flow breakout, fixed,
runner, trailing, hard-stop, and funding-aware policies, while recording the
static barrier and path-funding accounting caveats above as P2 follow-up.

### Required resolution

Resolved by WPR106-421. Perp-context strategies and basis/premium exits now
fail closed on `quality_latest_window_context_only`; GMM transition exits
require detector train/inference window, feature-version, params-hash, and
artifact-hash metadata; fixed-holding aliases preserve requested identity while
canonicalizing to `fixed_holding_window`; lower-timeframe no-hit exits use
lower-frame time-exit proof and reject stale horizon coverage; timestamped
funding-path rates feed realized funding costs in reference/vector/CUDA
fixed-holding engines; and the legacy `volatility_scaled_barrier` request now
records canonical artifact identity `static_primary_close_barrier`. Existing
v2 validation and cost-model tests cover train-only validation rows,
gross-only rejection, and base/stress cost rows. The resolution remains
research-only and does not create candidate, paper, live, sizing, runtime-mode,
or promotion claims.

## ISSUE-R106-019: Forced no-regime exact discovery produces failed trial ledgers

Severity: P1
Stage discovered: Stage R106 - latest autopilot run research analysis
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/knn_study.py`, `src/tradingbotsuite/research_discovery/spec.py`, `tests/research_discovery/test_discovery_runner.py`, `configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json`, `configs/discovery/exact_entry_sweep_ethusdt_durable_r104_v1.json`

### Problem

The latest forced Research Autopilot run successfully reached exact discovery
for BTCUSDT and ETHUSDT, but both isolated exact-discovery sweeps wrote only
failed trial records. The discovery manifests report 570240 completed trials
per symbol, while the candidate ledgers contain 570240 blocked rows per symbol,
zero interesting rows, and `blocker_code: trial_execution_error` throughout.
This makes the latest exact-discovery evidence analytically unusable for lead
selection, exit-lab work, validation floors, or candidate-pack eligibility.

### Evidence

Run
`run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e` completed with
`force_upstream_recompute: true`, `execution_status: executed_upstream_compute`,
and isolated BTC/ETH exact discovery outputs.

The BTC discovery manifest at
`data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-discovery/discovery_run_manifest.json`
records `completed_trials: 570240`, `interesting_candidates: 0`, and
`blocked_candidates: 570240`. The ETH manifest records the same counts.

Sampled BTC and ETH trial JSONs across the run, including `trial-000001`,
`trial-001000`, `trial-050000`, `trial-100000`, `trial-250000`,
`trial-400000`, and `trial-570240`, all have `status: failed`,
`blocker_code: trial_execution_error`, and
`error_payload.error: regime_model_backend must match regime_mode`. Their
payloads show no-regime fields such as `regime_mode: none`,
`regime_detector_type: none`, `regime_model_backend: none`,
`regime_gate_enabled: false`, and `same_regime_neighbor_pool_enabled: false`.
A direct current-checkout `KnnStudySpec` no-regime validation passes, so the
failure should be reproduced in the exact-discovery runtime path before
assigning root cause to the validator itself.

### Required resolution

Open a focused discovery-runtime packet. Reproduce the failed no-regime exact
discovery path with a bounded fixture/spec, identify where the no-regime
backend fields diverge or are validated against the wrong settings, and add a
regression that full exact-discovery trial execution can complete no-regime
payloads. Also harden manifest/ledger accounting so a run with all failed trial
records cannot look analytically complete merely because durable trial records
were written.

Until resolved, do not use the latest forced exact-discovery outputs for
research lead selection, exit labs, validation-floor materialization,
multiple-testing evidence, candidate-pack eligibility, or promotion claims.

### Resolution notes

Resolved by WPR106-68. The no-regime exact-discovery runtime path now passes
`regime_model_backend: none` through the cached KNN materialization path, so
no-regime trials no longer inherit the GMM default backend at validation time.
Large real discovery runs execute a bounded representative preflight before
the full sweep and stop fail-closed when preflight trial execution fails.
Discovery manifests and snapshots now separate successful `completed_trials`
from `failed_trials`, `durable_trial_records`, and
`processed_trial_records`, and real-discovery runs with runtime-failed trial
records end `blocked` instead of analytically `completed`. Candidate-pack
eligibility reports `discovery_failed_trial_records_present` for failed trial
records, and the operator evidence gate rejects failed-trial manifests while
accepting clean reduced exact runs. BTC/ETH exact configs were reduced from
570240 to 3456 no-regime trials per symbol as a research-only compute-reduction
phase; no candidate pack, live/paper/runtime, order-placement, sizing, or
promotion claim was introduced.

## ISSUE-R106-018: Forced autopilot cycle handoff injects operator keys into strict cycle spec

Severity: P1
Stage discovered: Stage R106 - autopilot operational readiness
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/operator_console.py`, `tests/tradingbotsuite/test_operator_ui.py`

### Problem

Forced Research Autopilot correctly requests upstream compute, but the isolated
historical-cycle wrapper writes operator-only bookkeeping keys directly into
`cycle_spec.json`. `HistoricalResearchCycleSpec` rejects those unknown top-level
keys before compute can start.

### Evidence

Local run `run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b` failed in
about 1.6 seconds with `force_upstream_recompute: true` and:

`historical_research_cycle unknown schema keys: operator_job_id, operator_original_spec_path, operator_overwrite_protection`

The manifest shows the catalog was skipped as ready, then BTC historical-cycle
attempt 1 and retry attempt 2 failed on the same schema error before any
upstream step completed.

### Required resolution

Keep historical-cycle specs schema-clean. Preserve operator audit metadata in a
sidecar file or job result rather than inserting it into the strict cycle spec.
Do not weaken `HistoricalResearchCycleSpec` schema validation.

### Resolution notes

Resolved by WPR106-66. The isolated historical-cycle wrapper now writes
operator bookkeeping to `operator_metadata.json` next to the isolated spec and
keeps `cycle_spec.json` free of `operator_*` keys. Focused tests cover both the
manual historical-cycle handoff and forced autopilot handoff. Historical-cycle
schema validation remains strict.

## ISSUE-R106-017: Autopilot primary action can review cached evidence instead of starting new compute

Severity: P1
Stage discovered: Stage R106 - autopilot operational readiness
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`

### Problem

The operator Research page still exposed the primary action as "Run Research
Autopilot" with a separate unchecked force checkbox. A user trying to start the
next compute iteration could click the primary button and get a successful run
in a few seconds because all existing catalog, cycle, discovery, analysis,
delta, exit-lab, and eligibility artifacts were reused.

### Evidence

Local runs `run-research-autopilot-5b3667d3f0cb4e98b6ad170313c6799d` and
`run-research-autopilot-ccd44aee842b4cb488656565c92e2998` completed in about
2-3 seconds with `force_upstream_recompute: false`, `executed_step_count: 0`,
`execution_status: reused_existing_evidence`, and all 13 steps skipped.

### Required resolution

Make new upstream compute a first-class explicit action, keep reuse review as a
separate action, and fail closed if a forced upstream request ever reaches
completion without upstream cycle/discovery/catalog compute.

### Resolution notes

Resolved by WPR106-65. The Research page now exposes `Run New Compute
Iteration`, which sends `force_upstream_recompute: true`, separately from
`Review Existing Evidence`, which sends `force_upstream_recompute: false`.
The service now blocks a forced upstream request if no upstream compute ran, so
it cannot be recorded as a successful new iteration. No generated research
artifacts, strategy math, live execution, sizing, runtime mode, candidate-pack
write, or promotion behavior were changed.

## ISSUE-R106-016: Autopilot reports downstream eligibility refresh as new iteration evidence

Severity: P1
Stage discovered: Stage R106 - autopilot operational readiness
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`

### Problem

`run-research-autopilot` reports `execution_status: executed_new_evidence`
whenever any helper step executes. A run that skips all upstream expensive
evidence and only refreshes BTC/ETH candidate eligibility can therefore look
like a completed new iteration, even though no historical-cycle, exact
discovery, analysis, delta, or exit-lab compute was rerun.

### Evidence

Operator job `run-research-autopilot-ba260d798eaf42e8a23634497986f3e6`
completed in about 80 seconds with `executed_step_count: 2`. Its manifest
shows both executed steps were `candidate_eligibility`; catalog, BTC/ETH
historical cycles, BTC/ETH exact discovery, analysis, deltas, and exit lab
were all skipped as existing complete artifacts.

### Required resolution

Add explicit compute-scope semantics to autopilot. Downstream-only refresh must
be surfaced separately from upstream compute. Add an explicit operator request
flag for forced upstream recompute so a deliberate new iteration can run
historical cycles and exact discovery even when stable current artifacts exist.

### Resolution notes

Resolved by WPR106-63. Autopilot completion now records compute-scope status
from executed step classes: zero execution is `reused_existing_evidence`,
downstream-only helper work is `refreshed_downstream_evidence`, and
cycle/discovery/catalog execution is `executed_upstream_compute`. The posted
eligibility-only run shape is covered by regression and no longer reports a
new upstream iteration. The operator route and Research UI expose
`force_upstream_recompute`; when enabled, autopilot bypasses reusable
cycle/discovery/analysis/delta/exit/eligibility artifacts and runs isolated
cycle/discovery/downstream helpers. Forced eligibility only attaches
multiple-testing and validation-floor manifests that match the fresh discovery
artifact; otherwise it records missing gate manifests fail-closed. No generated
research artifacts, strategy math, live execution, sizing, runtime mode, or
promotion behavior were changed.

WPR106-64 adds the final status hardening for the same issue class: blocked
and failed autopilot manifests now publish terminal `execution_status` and
`status_detail` instead of inheriting running or computed-scope labels, and
the API accepts only real JSON booleans for autopilot flags so string values
such as `"false"` cannot accidentally enable forced upstream recompute.

## ISSUE-R106-015: Stable exact-discovery overwrite protection can still fail autopilot

Severity: P1
Stage discovered: Stage R106 - autopilot operational readiness
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/operator_console.py`, `tests/tradingbotsuite/test_operator_ui.py`

### Problem

`run-research-autopilot` can still call exact discovery with a stable run-id
output directory and fail with `completed discovery runs refuse overwrite`.
That makes a compute iteration end as an operator failure instead of either
reusing current completed evidence, blocking stale evidence explicitly, or
running a fresh isolated discovery attempt.

### Evidence

An operator job submitted with `include_catalog_refresh: true`,
`include_eligibility: true`, and BTCUSDT/ETHUSDT failed with
`error_text: completed discovery runs refuse overwrite`.

### Required resolution

Keep stable discovery reuse and stale-spec blockers, but add a bounded fallback
that retries exact discovery in an isolated per-job output directory when the
stable output refuses overwrite. The fallback must remain research-only and
must not rewrite generated stable discovery artifacts.

### Resolution notes

Resolved by WPR106-62. Operator discovery jobs and autopilot exact-discovery
steps now call a stable-overwrite fallback wrapper. If the stable run-id output
raises `completed discovery runs refuse overwrite`, the service retries the
same discovery spec in a per-job nested output directory with
isolated-output routing, records `overwrite_fallback_used`, and leaves stable
generated artifacts untouched. Stable current evidence reuse and stale
completed stable-evidence blocking remain intact.

## ISSUE-R106-014: Runtime artifact validation is not mode-aware and not fail-closed for unknown manifests

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/promotion/artifact_validator.py`, `src/tradingbotsuite/live/preflight.py`, `src/tradingbotsuite/runtime.py`, `tests/live/**`, `tests/research_artifacts/test_candidate_pack.py`

### Problem

The artifact validator has `validate_artifact_for_live_input()`, but no
mode-aware `validate_artifact_for_runtime_mode()` contract. The live validator
rejects explicit research and observe-only flags, but it can allow an unknown
minimal manifest when `promotion_ready: true` is present and live-boundary
fields are missing.

### Evidence

The WPR106-32 execution and artifact audit found that a minimal unknown manifest
with `artifact_manifest_version` and `promotion_ready: true` can return
`allowed=True` from the generic live-input validator. Candidate-pack gates are
stricter for candidate-pack evidence, but the generic runtime/live validation
path is not fail-closed for unknown or mode-ambiguous manifests.

### Required resolution

Add mode-aware artifact validation for runtime/paper/live/shadow contexts.
Unknown manifests and manifests missing explicit live-boundary fields must fail
closed. Live mode must reject research-only, observe-only, shadow-only, unknown,
and mode-ambiguous artifacts before scorer, shadow-loader, or live adapter
construction.

### Resolution notes

Resolved by WPR106-38. `validate_artifact_for_runtime_mode()` now fail-closes
runtime artifact loading by mode. Minimal unknown or mode-ambiguous manifests
are rejected. Live validation now requires explicit runtime-mode allowance and
explicit live boundary fields. Paper runtime artifact loading is unsupported
and rejected until a later promotion process defines an explicit paper-runtime
contract. Shadow runtime loading is restricted to explicit shadow promotion
candidates that pass the existing shadow validator and declare shadow runtime
allowance. Live preflight activates artifact validation whenever an artifact
path is configured, including non-live modes, and `runtime.build_engine()`
validates before scorer or shadow-loader construction.

## ISSUE-R106-013: Local credential files can imply Hyperliquid live/testnet enablement

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/config.py`, `tests/test_config.py`, `tests/live/test_preflight.py`, `tests/tradingbotsuite/test_engine.py`

### Problem

Presence of a local Hyperliquid testnet credential file can imply live/testnet
enablement when `TBS_HL_ENABLE_LIVE` is absent. Live enablement must require an
explicit environment or secret-manager setting and an explicit operator choice;
credential-file presence must not activate live capability by default.

### Evidence

The WPR106-32 safety audit found `src/tradingbotsuite/config.py` loading
`hyperliquidtestnet.txt`, setting testnet `enable_live=True`, and using that
value when `TBS_HL_ENABLE_LIVE` is absent. Existing tests assert the current
behavior, while `docs/OPERATOR_QUICKSTART.md` says live/testnet requires
explicit `TBS_HL_ENABLE_LIVE=true`.

### Required resolution

Change config loading so credential files may provide signer/account data but
cannot satisfy live enablement unless explicit live-enable configuration is
present. Update tests to reject implicit enablement and prove live preflight
still blocks unsafe modes.

### Resolution notes

Resolved by WPR106-37. Hyperliquid credential files remain passive signer,
account, and endpoint inputs only. Testnet file parsing no longer emits
`enable_live`, and `AppConfig.from_env()` now resolves Hyperliquid live
enablement only from explicit `TBS_HL_ENABLE_LIVE`. Config regressions cover
file-only passive loading, explicit live opt-in, and explicit mainnet URL plus
file credentials with no live flag. Live preflight now has a regression proving
file-supplied key/account data still blocks on `hyperliquid_live_not_enabled`
when the explicit flag is absent.

## ISSUE-R106-012: Lower-timeframe entry pricing is labeled but not used

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/backtesting/execution_sim.py`, `tests/unit/test_execution_simulator.py`, `tests/backtesting/**`

### Problem

`lower_timeframe_execution_path` requires lower-timeframe data but does not use
that path to choose the latency fill time or fill price. The simulator still
selects the next primary bar and falls through to the primary bar open, which
can make latency entry pricing optimistic or mislabeled.

### Evidence

The WPR106-32 execution audit found that
`ExecutionSimulator._entry_index()` applies latency against primary
`bar_time_ms`, while `_entry_price()` ignores lower-timeframe rows for
`lower_timeframe_execution_path`. A 60-second latency inside a 15-minute bar can
therefore be represented as a next-primary-open fill rather than a
lower-timeframe observable fill.

### Required resolution

Either implement true lower-timeframe latency fill selection and price evidence
or reject `lower_timeframe_execution_path` until it is implemented. Add tests
where lower-timeframe and primary-bar prices differ and assert the exact
contract.

### Resolution notes

Resolved by WPR106-36. The reference research simulator now treats
`lower_timeframe_execution_path` as a proven lower-timeframe latency fill: it
selects the first symbol-matched lower-timeframe row at or after
`decision_time_ms + entry_latency_ms`, uses that row's open as the entry price,
propagates the actual lower-timeframe entry time into holding and exit timing,
and records `entry_target_time_ms`, `entry_primary_bar_time_ms`, and
`entry_sequence_proof`. Missing lower-frame open/timestamp coverage fails
closed. Vector, CUDA, and CUDA-batched fixed-holding engines remain unsupported
for lower-timeframe entry sources, but now emit matching primary-bar entry
proof metadata for supported paths.

## ISSUE-R106-011: Generic purge is fixed-bar based instead of label/event-end aware

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/research/dataset.py`, `src/tradingbotsuite/research/hmm_knn.py`, `src/tradingbotsuite/research_discovery/knn_study.py`, `src/tradingbotsuite/research_discovery/runner.py`, `tests/backtesting/test_splits.py`, `tests/research_discovery/**`, `tests/tradingbotsuite/**`

### Problem

The generic split engine purges by a fixed number of bars. Fixed-bar purge is
not reliable for long or overlapping labels; label interval or event end time
must drive purging.

### Evidence

The WPR106-32 data and validation audit found no active `LabelSpec` type.
`build_purged_walk_forward_splits()` sets
`train_end = validation_start - purge_embargo_bars - 1`. Legacy research
dataset code has `label_interval_start_ms`, `label_interval_end_ms`, and
`label_exit_time_ms`, and discovery KNN has a separate label-horizon training
filter, but the active generic split contract lacks explicit event-end-aware
purge evidence.

### Required resolution

Add explicit LabelSpec/event-end metadata for label-producing research paths and
make split purge horizon-aware where long or overlapping labels can leak. Fixed
bar purge may remain only as a documented fallback for cases with no event-end
labels and must be clearly identified as such in manifests.

### Resolution notes

Resolved by WPR106-35. `LabelSpec` and split payload evidence now distinguish
event-end-aware purge from fixed-bar fallback. Label/event-end-aware splits use
`label_event_end_time_ms`, `event_end_time_ms`, `label_exit_time_ms`,
`label_interval_end_ms`, or `label_future_end_time_ms` when supplied, convert
embargo bars to milliseconds, and exclude train rows whose label/event end plus
embargo reaches the validation start. Missing required event-end columns fail
closed. Discovery directional labels now stamp `label_event_end_time_ms`, HMM
and KNN materialization honor explicit event-safe train indices, and historical
cycle split manifests record purge-method counts plus compact train-index
evidence instead of raw index dumps. Fixed-bar purge remains only as identified
fallback evidence when no event-end metadata is available.

## ISSUE-R106-010: Synthetic fallback and source selection are not explicit enough

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_discovery/spec.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `configs/research/**`, `configs/discovery/**`, `tests/contracts/**`, `tests/historical/**`, `tests/research_discovery/**`

### Problem

Historical-cycle source loading can synthesize data when no data source is
declared. Configs and tests include `synthetic_fallback_allowed`, but
`CycleDataSpec` does not parse it as a contract field. Source selection evidence
is also implicit rather than a clear selected/skipped/rejected source ledger.

### Evidence

The WPR106-32 data contract audit found that historical cycles try
`dataset_path`, `dataset_manifest_paths`, and `local_fixture_dir`, then
synthesize when `synthetic_fixture` is true or no source is declared. Discovery
missing-data paths are stricter and candidate-pack gates reject synthetic or
non-ready evidence, but the historical research-cycle contract does not fail
closed on the explicit non-negotiable flag.

### Required resolution

Parse and enforce explicit synthetic fallback policy. Synthetic must be
explicit, demo/test-only, non-promotable, and rejected for candidate-ready
evidence. Historical and discovery runs should write source-selection evidence
that records selected, skipped, rejected, and missing sources.

### Resolution notes

Resolved by WPR106-34. `CycleDataSpec` now parses and round-trips
`synthetic_fallback_allowed` plus explicit synthetic use-case metadata. No
declared data source now fails closed unless `synthetic_fixture: true` is
explicitly requested. Synthetic fixtures are restricted to `test_only`,
`demo_only`, or `benchmark_only`, cannot be combined with declared real source
paths, and remain non-promotable. Historical cycle manifests now include a
required `source_selection_manifest` with selected/skipped/rejected source
records. Ambiguous `local_fixture_dir` directories with multiple Parquet files
fail closed instead of selecting the first file.

## ISSUE-R106-009: CI and reproducible research install checks are missing

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `.github/workflows/**`, `pyproject.toml`, `README.md`, `docs/ACTIVE_INDEX.md`, `tests/**`

### Problem

The repository has no checked-in GitHub Actions workflow or equivalent CI gate
for reproducible installation and baseline validation. Without a repeatable
install/check surface, research evidence can drift by local environment.

### Evidence

The WPR106-32 pre-edit audit found no `.github` workflow files. Current docs
list local validation commands, but there is no repository CI artifact proving
editable install, compile, contracts, and focused research-only checks run in a
clean environment.

### Required resolution

Add a CI/reproducible research install packet that installs the package in a
clean Python 3.11 environment, runs compile, contracts, and a focused safety
baseline, and documents any intentional optional dependency exclusions.

### Resolution notes

Resolved by WPR106-33. `.github/workflows/research-validation.yml` now installs
`.[dev]` in a clean Python 3.11 GitHub Actions job, runs `pip check`, compiles
`src/tradingbotsuite`, runs contract tests, and runs focused live/artifact
boundary tests. Optional research, Crypto Lake, and GPU extras are explicitly
outside this baseline.

## ISSUE-R106-008: Active index and ResearchEngineDeluxe identity were missing

Severity: P0
Stage discovered: Stage R106 - active index and research identity audit
Owner: Codex Research Agent
Status: resolved
Paths affected: `docs/ACTIVE_INDEX.md`, `START_HERE.md`, `README.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`

### Problem

Agents had no current active index and onboarding docs still emphasized
TradingBotSuite or the old research branch name. That increased the chance that
future work would follow stale docs, miss current P0 blockers, or treat package
identity as product identity.

### Evidence

The WPR106-32 repo cartography audit found `docs/ACTIVE_INDEX.md` missing, the
current checkout on `main`, and stale branch/identity wording in onboarding
docs. The external master report also recommends canonical ResearchEngineDeluxe
research-only identity while keeping `tradingbotsuite` as a package
implementation detail.

### Required resolution

Create `docs/ACTIVE_INDEX.md`, update onboarding identity, and point future
agents to current stage, latest evidence, open blockers, and research-only
rules before source work.

### Resolution notes

Resolved by WPR106-32. The active index and onboarding updates clarify current
checkout identity, research-only boundaries, latest R106 evidence, and the open
P0 stop condition. No source behavior or generated research evidence was
changed.

## ISSUE-R104-001: Durable R104 fixtures are too compact for candidate-ready brute-force evidence

Severity: P1
Stage discovered: Stage R104 - candidate validation on durable evidence
Owner: Codex Research Agent
Status: resolved
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

Previously open. WPR104-04 adds truthful brute-force-scale run profiles and UI/progress
wiring, but it does not fabricate additional durable data or claim candidate
readiness from the compact screening fixture. WPR105-104 hardens the operator
surface so the compact BTC/ETH fixtures are reported as integrity-ready
screening windows, not candidate-depth-ready evidence; old/simple artifacts no
longer completed the required checklist while this issue was open.
WPR105-106 adds the missing runnable Step 0 collection pipeline and operator
button, validates Binance Vision checksum sidecars plus fixture integrity, and
wires generated candidate-depth packs into readiness, cycle, and discovery
defaults. This issue remained open until the full collection was run and the
resulting deep cycles, exact sweeps, and candidate eligibility review were
complete.
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
issue remained open until the refreshed catalog, deep cycles, exact sweeps, and
eligibility review complete on candidate-depth evidence. WPR106-46 implements
the Option A exact replay-overlay domain and bounded cycle-smoke path: all 48
WPR106-31 replay leads are representable and 48 singleton overlay specs were
generated locally, with bounded BTC/ETH smokes proving overlay provenance
through rankings, backtest index, and gate reports. The issue remained open
because WPR106-46 does not complete the required deep cycles, exact sweeps,
full exit labs, negative controls, or eligibility review.
WPR106-47 verifies full 48-lead frozen-entry exit-lab evidence and adds
separate full-window, modern-window, negative-control, and eligibility audit
artifacts. It kept the issue open because all exit-lab gates remain blocked,
modern-window replay artifacts are missing locally, first-class negative
controls are missing, WPR106-47-scope multiple-testing and validation floors are
missing, eligibility rows remain 0/48, and no candidate pack was emitted.
WPR106-48 adds first-class negative-control artifacts and hardens bridge/pack
rejection. The issue remained open because all 192 first-class control rows are
blocked by missing replay profile provenance, validation manifests, and
modern-window evidence; source label/timestamp inputs are also missing for the
shuffled-label and shifted-context control families. Refreshed eligibility
audits still have 0/48 eligible rows and no candidate pack.
WPR106-49 materializes replay-scope multiple-testing and validation-floor
manifests for all 48 WPR106-31 replay leads and refreshes eligibility. The
missing-manifest blockers are gone, but the issue remained open because all
48 rows still block on exit-lab no-improvement, blocked multiple-testing,
diagnostic validation floors, partial cycle-ranking overlap, unavailable
modern-window evidence, and unavailable passing negative controls. No candidate
pack was emitted.
WPR106-56 resolves this issue as a fail-closed no-candidate empirical outcome.
The compact R104 fixture blocker has been superseded by the completed R106
Historical Data Catalog under
`refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb`, where
BTCUSDT and ETHUSDT are candidate-depth ready with 221,952 primary 15m bars,
3,329,280 lower-timeframe rows, checksum evidence, active readiness manifests,
and generated active cycle/discovery specs. The downstream evidence does not
support a candidate pack: active cycles have 63 rejected candidates per symbol;
exact discovery completed 570,240 trials per symbol; WPR106-29 materialized
active multiple-testing, validation-floor, and capped eligibility evidence with
22,560 BTCUSDT and 23,040 ETHUSDT blocked rows, zero discovery-to-cycle ranking
overlap, zero eligible rows, and no candidate packs; WPR106-49 replay-scope
evidence likewise leaves all 48 replay rows blocked. Resolution is explicitly
not a candidate-ready, paper-ready, live-ready, or promotion-ready claim.

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
before operator isolated specs are written. `ISSUE-R104-001` was still open as an
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
machinery. Candidate-ready evidence was still blocked by empirical gates under
`ISSUE-R104-001` at WPR106-16 close; no promotion claim was made.

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

## ISSUE-R106-004: Full OF-style raw trades exceed central-history cap

Severity: P1
Stage discovered: WPR106-549 v2 Project OF-Style Data Expansion
Owner: Codex Research Agent
Status: resolved
Paths affected: `data/research/central_market_history/**`, `src/tradingbotsuite/v2/data_sources/central_market_history*.py`

### Problem

The official no-paid Binance Vision USD-M daily `trades` archives for the 29
project symbols cannot be bulk-collected into the current central market-history
store under the 300 GiB cap. The raw compressed files alone exceed the remaining
budget before normalized Parquet, source metadata, manifests, and quality
reports are added.

### Evidence

WPR106-549 source discovery found 22,256 project-symbol `trades` ZIP archives
with 282,126,518,523 compressed bytes and no existing cache hits. At the same
time, the central market-history store already used about 51 GiB, so full raw
trade collection would exceed the 322,122,547,200 byte cap even before
normalization. `bookTicker` also needs staged normalized-budget checks despite
raw bytes fitting, while `aggTrades` raw bytes fit but require staged
normalization checks.

### Required resolution

Choose one explicit operator-approved path before full raw-trade collection:
raise or partition the storage cap, attach a larger archive volume, collect a
narrower symbol/date window, or add a separately budgeted raw-only cold-storage
lane with clear non-normalized coverage semantics. Keep research-only boundary
flags and no-paid provenance intact.

### Resolution notes

Resolved by the WPR106-549 external raw-heavy archive lane and cataloged by
WPR106-550. The central market-history 300 GiB cap still correctly blocks full
raw `trades` ingestion into `data/research/central_market_history/**`, but the
operator-approved separate raw-only archive at
`M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw` satisfies
the required resolution path without changing central normalized coverage
semantics. The external validation report
`M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json`
records 22,256 complete `trades` sources and 1,159,478 complete sources across
all requested OF-style families, with zero missing, invalid, metadata-missing,
SHA-sidecar-missing, SHA-mismatch, CRC-failure, or `.part` files in the fresh
WPR106-550 report check. WPR106-552 then adds an explicit raw-archive
materializer and writes a compact feature proof pack with 251 materialized
sources, 81,093,159 parsed input rows, 256,523 feature rows, and zero blocked
sources. Full all-file feature-panel expansion remains compute scope; the
resolution is raw collection plus materialization proof readiness, not central
full-normalized coverage, autonomous readiness, candidate evidence,
paper/live/order/sizing/runtime behavior, or promotion readiness.

## Issue template

```markdown
## ISSUE-XXXX: Short title

Severity: P0/P1/P2/P3
Stage discovered:
Owner:
Status options: open | in_progress | resolved | accepted_debt
Paths affected:

### Problem

### Evidence

### Required resolution

### Resolution notes
```
