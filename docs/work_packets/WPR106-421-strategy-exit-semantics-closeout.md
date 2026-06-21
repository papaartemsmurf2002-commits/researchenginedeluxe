# WPR106-421 Strategy Exit Semantics Closeout

Status: self_checked
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Resolve the concrete strategy and exit semantics risks tracked by
`ISSUE-R106-020` enough that autonomous v2 research runs are not blocked by
ambiguous legacy strategy/backtest behavior. This packet preserves the
strangler migration approach: it adds or tightens focused contracts around the
existing research engine rather than redesigning v2 from scratch.

This packet is research-only. It may not create candidate packs, paper/live
signals, sizing instructions, order-placement behavior, runtime-mode changes,
promotion-ready artifacts, or generated research evidence.

## Audit IDs

- `V2-AUD-STRAT-004`
- `V2-AUD-BTENG-004`
- `V2-AUD-VALIDATION-002`

## Allowed Paths

- `docs/work_packets/WPR106-421-strategy-exit-semantics-closeout.md`
- `docs/KNOWN_ISSUES.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/audit/V2_COMPLETION_AUDIT_ISSUES_AND_HOLES_2026_06_21.md`
- `docs/contracts/strategy_contract.md`
- `docs/contracts/backtest_engine_contract.md`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/metrics.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/strategies/**`
- `tests/contracts/test_strategy_contracts.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/backtesting/**`
- `tests/unit/test_execution_simulator.py`
- `tests/historical/**`

## No-Touch Paths

- `src/**/live/**`
- `src/**/runtime.py`
- `run_live_smoke.py`
- `run_manual.py`
- order-placement adapters, broker helpers, exchange submit helpers
- sizing/runtime configuration paths
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/promotion/**`
- `src/tradingbotsuite/live/shadow_loader.py`
- committed generated research evidence under `data/research/**`
- legacy GUI/web/operator source paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- No no-touch path may be edited.
- No generated research evidence may be written or rewritten.
- Any existing legacy behavior that remains intentionally diagnostic must be
  explicitly labeled and tested as non-promotable research evidence.
- If a sub-issue is already covered by current source/tests, record the
  current evidence instead of inventing replacement behavior.
- Decisions that would change coverage floors, date floors, lockbox policy,
  candidate/promotion language, or data licensing are out of scope and must
  stop the packet.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\contracts\test_backtest_contracts.py tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\historical -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

Python 3.11 focused runs should be used where the local Windows socket state
allows, but `ISSUE-R106-026` remains the known blocker for monolithic Python
3.11 certification on this host.

## Acceptance Criteria

- Latest-window context use is blocked before strategy execution where accepted
  evidence would otherwise consume lockbox/latest context.
- GMM transition exits require detector metadata sufficient to identify train
  window, inference window, feature version, parameters, and artifact hash.
- Fixed-holding aliases resolve to a canonical rule ID while preserving the
  requested policy identity in artifacts.
- Lower-timeframe no-hit exits use the last completed lower-timeframe bar at
  or before the scheduled horizon and reject missing horizon coverage.
- Fit-aware train-context requirements are explicit and covered by leakage
  tests.
- Cost-stress metrics distinguish base/conservative/severe net evidence rather
  than accepting gross-only or base-only summaries.
- Volatility-scaled primary-bar barrier identities expose estimator/window/
  scale/timeframe/as-of components or are explicitly renamed as static.
- Funding-aware path behavior is either accounted by timestamped position path
  funding evidence or explicitly blocked from accepted semantics.
- `ISSUE-R106-020` is either resolved with evidence or narrowed with remaining
  sub-issues recorded as new specific known issues.

## Completion Notes

Implemented and self-checked on 2026-06-21.

Changed files stayed inside the declared packet scope after the scope was
expanded to include CUDA fixed-holding parity paths and
`tests/unit/test_execution_simulator.py`.

Decisions made:

- Latest-window perp context is diagnostic-only and now fails closed for the
  retained legacy perp-context strategies plus basis/premium normalization
  exits.
- GMM transition exits require detector train/inference windows, detector
  feature version, params hash, and artifact hash.
- Fixed-holding exit aliases keep the requested ID in trade artifacts while
  canonicalizing to `fixed_holding_window`.
- Lower-timeframe triple-barrier no-hit exits require lower-frame horizon
  coverage and use the lower-frame close/proof for time exits.
- The legacy `volatility_scaled_barrier` request is preserved for compatibility
  but records canonical artifact identity `static_primary_close_barrier`.
- Realized funding costs use timestamped in-trade funding-path rates when
  funding rows are available across reference/vector/CUDA fixed-holding lanes.
- Existing v2 train-only validation, gross-only rejection, and base/stress
  cost-row tests provide the fit-aware/cost-stress acceptance evidence.

Acceptance evidence:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\contracts\test_backtest_contracts.py tests\backtesting tests\unit\test_execution_simulator.py -q
# 459 passed, 1 skipped

$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 173 passed

$env:PYTHONPATH='src'; python -m pytest tests\historical -q
# 50 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with existing LF-to-CRLF warnings only
```

Additional validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# reached 462 passed, then hit known ISSUE-R106-026 WinError 10055
# pytest-asyncio socketpair setup before the affected async test body
```

`ISSUE-R106-020` is resolved. No candidate pack, paper/live signal,
order-placement behavior, sizing instruction, runtime-mode change, generated
research evidence, or promotion-ready claim was created.
