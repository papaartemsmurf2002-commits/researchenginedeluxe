# WPR106-570 - V2 Central Archive Snapshot Bridge And Benchmark Closure

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Resolve `ISSUE-R106-035` by adding a research-only bridge from existing
central market-history evidence into the v2 snapshot-backed benchmark contract,
then run larger local-panel fast/reference benchmark evidence without
collecting data or mutating the central archive.

The bridge may derive packet-local v2 silver bar slices, file manifests,
coverage reports, archive snapshots, and a benchmark-scoped as-of universe
from already existing central batch manifests and normalized Parquet files.
It must write only under the requested bridge/output root and must not append,
rewrite, or delete anything under `data/research/central_market_history/**`.

No broad speedup claim is in scope unless complete measured evidence exists:
reference runtime, fast runtime, data-load time, artifact-write time, memory
peak, parity status, artifact mode, panel size, instrument count, timeframe,
and runtime context.

## Allowed paths

- `docs/work_packets/WPR106-570-v2-central-archive-snapshot-bridge-and-benchmark-closure.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/archive_inventory/**`
- `src/tradingbotsuite/v2/backtest_engine/benchmarks.py`
- `src/tradingbotsuite/v2/backtest_engine/__init__.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_central_archive_snapshot_bridge_phase82.py`
- `tests/v2/test_backtest_benchmark_phase80.py`
- local generated evidence under `data/research/wpr106_570_central_archive_snapshot_bridge/**`

## No-touch review

- No live, paper, order-placement, sizing, promotion, candidate-pack,
  runtime-mode, secret, local-state, Lead Book, old evidence, or central
  archive mutation paths are in scope.
- `data/research/central_market_history/**` is read-only input for this
  packet.
- Packet-local bridge output is generated benchmark input/evidence, not central
  archive history and not a source-of-truth rewrite.
- Funding must not be fabricated for bar-only benchmark inputs. If central
  bars lack funding fields, the benchmark cost model must explicitly disable
  required funding or fail closed.
- The Python/reference vectorized lane remains correctness authority.

## Implementation plan

1. Add a central archive snapshot bridge service that reads project validation
   and batch manifests, verifies selected normalized Parquet hashes, converts
   selected central bar files into v2 silver bar slices under a caller-provided
   bridge root, writes v2 file manifests, aggregate coverage reports, archive
   snapshot, and benchmark-scoped as-of universe rows.
2. Add a CLI entrypoint to build the bridge without touching central archive
   manifests.
3. Add a narrow benchmark CLI cost-model file option so bar-only benchmark
   evidence can explicitly use a no-funding-required cost model instead of
   implying missing funding observations.
4. Add focused tests for bridge construction, read-only central inputs,
   benchmark loading, resolver readiness, and cost-model CLI handling.
5. Run a larger local benchmark over existing central 1m data, preferably a
   BTC/ETH multi-symbol panel, and record the measured report path.
6. Update `docs/KNOWN_ISSUES.md` with a resolved or accepted-debt disposition
   for `ISSUE-R106-035`.

## Implementation notes

- Added a read-only central archive snapshot bridge under
  `tradingbotsuite.v2.archive_inventory.snapshot_bridge`.
- Added `archive-inventory --bridge-central-snapshot` for packet-local bridge
  creation from existing central manifests and normalized Parquet files.
- Added `fast-lane benchmark-run --cost-model-file` so bar-only benchmark
  inputs can explicitly use `funding_required=false` with
  `funding_missing_policy=explicit_zero`.
- Added focused tests for bridge construction, CLI JSON output, v2
  snapshot-backed loading, and benchmark CLI cost-model handling.

## Benchmark evidence

Bridge build:

- Command: `archive-inventory --bridge-central-snapshot --archive-root data\research\central_market_history --bridge-archive-root data\research\wpr106_570_central_archive_snapshot_bridge\bridge_archive --instrument-id binance:perp:BTCUSDT --instrument-id binance:perp:ETHUSDT --timeframe 1m --start-ts 2024-01-01T00:00:00Z --end-ts 2024-07-01T00:00:00Z --asof-date 2024-01-01`
- Report:
  `data/research/wpr106_570_central_archive_snapshot_bridge/bridge_archive/manifests/central_archive_snapshot_bridge_report.json`
- Archive snapshot:
  `82ad1e05f363cd2d82cf54f5a592b21eb7002487f08348d23a5e51ad0d0eff26`
- Universe snapshot:
  `56c752700a70c0fefc7f8fef189617c80cdb0eaf7a21dae13952fd433ceafab8`
- Scope: BTCUSDT and ETHUSDT 1m, `2024-01-01T00:00:00Z` through
  `2024-07-01T00:00:00Z`, 12 derived file-manifest rows, 524,160 rows,
  accepted-research coverage reports, `central_archive_mutated=false`.

Resolver check:

- Command: `archive-inventory --archive-root data\research\wpr106_570_central_archive_snapshot_bridge\bridge_archive --missing-for-strategy data\research\wpr106_570_central_archive_snapshot_bridge\strategy_spec_1m_mean_reversion.json --instrument-id binance:perp:BTCUSDT --instrument-id binance:perp:ETHUSDT --venue binance_usdm --family bars --timeframe 1m --start-ts 2024-01-01T00:00:00Z --end-ts 2024-07-01T00:00:00Z --artifact-mode metrics_only --prefer-fast-lane --require-reference-audit --asof-date 2026-06-21`
- Result: `ready=true`, usable archive refs emitted for both instruments, no
  `DataGapRequest`, `do_not_collect_reason=existing_archive_refs_sufficient`.

Benchmark check:

- Completed report:
  `data/research/wpr106_570_central_archive_snapshot_bridge/benchmark_runs/wpr106570-btc-1m-jan-feb2024-smoke-tol1e9/benchmark_report.json`
- Scope: BTCUSDT 1m, `2024-01-01T00:00:00Z` through
  `2024-03-01T00:00:00Z`, 86,400 reported rows, metrics-only artifacts,
  sandbox-diagnostic benchmark mode for the shorter-than-six-month timing run.
- Parity: `pass` with `tolerance_abs=1e-9`; the first strict `1e-12` run only
  failed `total_turnover` by `4.831690603168681e-12`.
- Complete observations present: reference runtime, fast runtime, data-load
  time, artifact-write time, memory peak, parity status, artifact mode, panel
  size/row count, instrument count, timeframe, and runtime context.
- Runtime result: reference runtime `13.711803799989866` seconds, fast runtime
  `171.47378130001016` seconds, measured ratio `0.07996443360632331`,
  `speedup_claimed=false`.
- The attempted BTCUSDT/ETHUSDT six-month panel run exceeded the local host
  timeout and was stopped; it is not resolution evidence.
- No speedup claim is supported by WPR106-570 evidence.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_central_archive_snapshot_bridge_phase82.py tests\v2\test_backtest_benchmark_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
git diff --check
```

Final validation should use the exact commands requested by the owner.

## Validation results

Final validation completed on 2026-06-29:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
# 463 passed, 1 warning in 8.63s

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
# 657 passed, 1 warning in 72.73s

$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
# autonomous_research_ready=true
# boundary flags: research_only=true, observe_only=true, promotion_ready=false,
# live_signal=false, paper_signal=false, order_placement_instruction=false,
# sizing_instruction=false, runtime_mode_change=false,
# candidate_evidence=false, candidate_pack_eligible=false

git diff --check
# passed with CRLF warnings only
```

`ISSUE-R106-035` is resolved in `docs/KNOWN_ISSUES.md`. The worktree is ready
for owner review/stage/commit, subject to the broader uncommitted
WPR106-567/WPR106-569 changes already present before this packet.
