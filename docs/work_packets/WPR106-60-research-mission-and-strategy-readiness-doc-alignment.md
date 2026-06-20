# Work Packet: WPR106-60 Research Mission And Strategy Readiness Doc Alignment

## Goal

Audit whether the current strategy-development surface is structurally complete
for the next research iteration, then align orientation docs with the current
project mission: rapidly test new strategy theories and refine existing
strategies on a modular, reproducible, high-throughput research architecture
that generates analyzable evidence patterns.

## Current Repo Facts

- Current checkout is `main`, with uncommitted WPR106-57 through WPR106-59
  changes already present and preserved.
- Strategy registry contains the active baseline, trend/range/volatility,
  perp-context v2, funding, regime, HMM/KNN, liquidation, and LC reference
  plugins.
- Strategy contract tests cover registry membership, config loading, strategy
  family matrices, candidate blueprints, BTC/ETH durable cycle configs, and
  fail-closed candidate-pack status.
- Existing docs are correct that research outputs must not be treated as live
  signals, but several docs are stale or overemphasize live-boundary language
  instead of the research mission: generate useful evidence, rejection
  patterns, ablations, and comparable artifacts for iteration.

## Allowed Edit Paths

- `docs/work_packets/WPR106-60-*.md`
- `README.md`
- `docs/ACTIVE_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/RESEARCH_BRANCH_DISTILLATION.md`

## Research Boundary

- Documentation-only packet.
- Do not change strategy code, candidate gates, generated evidence, configs,
  runtime behavior, live/paper behavior, order placement, sizing, or promotion
  logic.
- Do not start catalog rebuilds, historical cycles, discovery runs, or any
  other long compute job.

## Plan

1. Record the strategy-readiness audit conclusion in orientation docs.
2. Reframe project identity around modular fast research, evidence generation,
   falsification, ablation, and iteration.
3. Keep no-live/no-order/no-sizing language, but describe it as a boundary that
   preserves evidence quality rather than as the product's main purpose.
4. Refresh stale R44-era distillation status and strategy-family list.
5. Run focused strategy contract validation plus baseline compile/contracts.

## Acceptance Criteria

- Docs state that the current strategy implementation is structurally complete
  for research iteration, while current evidence still has zero eligible
  candidate-pack rows.
- Docs explicitly distinguish research evidence controls from live-system
  safety framing.
- Docs describe knowledge generation outputs: manifests, metrics, rejections,
  ablations, validation floors, multiple-testing evidence, and analyzable
  patterns.
- Validation passes for strategy contracts and baseline checks.

## Outcome

- Audited the active strategy implementation surface:
  - `strategy_registry()` exposes 16 active IDs, including the baseline,
    trend/range/volatility, perp-context v2, funding/OI, regime, HMM/KNN,
    liquidation, LC reference, and compatibility trend alias.
  - `configs/strategies/*.json` load successfully against the registry.
  - Strategy contracts cover registry membership, config compatibility,
    strategy-family matrices, BTC/ETH candidate blueprints, durable cycle
    configs, deferred HMM/KNN overlay status, and fail-closed candidate-pack
    eligibility.
- Conclusion: the strategy implementation is structurally complete for the
  next research iteration. The missing piece is not more guardrail code; it is
  empirical iteration: compute new evidence, study rejection patterns, refine
  hypotheses, and rerun focused strategy families.
- Preserved the no-live/no-order/no-sizing boundary, but reframed it in docs
  as evidence hygiene rather than the project's main purpose.
- Updated orientation docs to describe ResearchEngineDeluxe as a modular,
  high-throughput strategy evidence factory for testing, rejecting, ablation,
  validation, and iteration.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q`
  passed: 277 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed:
  441 tests.
