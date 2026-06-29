# WPR106-561 - V2 Autonomous Research Math And Performance Roadmap

Status: completed
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Perform a final docs-only audit of math correctness and possible speed
improvements in the v2 autonomous research code path, then publish a final
roadmap and a next-agent implementation handoff.

This packet may inspect source, tests, contracts, and generated manifests, but
it must not change source behavior, run new research cycles, collect data,
materialize data, append ledgers, update Lead Book rows, rewrite generated
evidence, or create candidate/paper/live/order/sizing/runtime/promotion
implications.

## Allowed paths

- `docs/work_packets/WPR106-561-v2-autonomous-research-math-performance-roadmap.md`
- `docs/audit/V2_AUTONOMOUS_RESEARCH_MATH_PERFORMANCE_FINAL_ROADMAP_2026_06_29.md`
- `docs/hand_offs/WPR106-561-next-agent-implementation-handoff.md`

## Read-only inspection scope

- `src/tradingbotsuite/v2/autonomy/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/costs/**`
- `src/tradingbotsuite/v2/validation/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `src/tradingbotsuite/v2/ledger/**`
- `src/tradingbotsuite/v2/lead_book/**`
- focused tests under `tests/v2/**`
- current v2 control docs, contracts, and work packets

## No-touch review

- No live/runtime, order-placement, sizing, promotion, candidate-pack truth,
  generated evidence, old-output, or secret/local-state paths are in scope.
- This packet may recommend future implementation changes but must not
  implement them.
- Research-only, observe-only, promotion-false boundary semantics must remain
  unchanged.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

Broaden only if the docs audit uncovers a source-level blocker that must be
recorded outside the roadmap.

## Outputs

- `docs/audit/V2_AUTONOMOUS_RESEARCH_MATH_PERFORMANCE_FINAL_ROADMAP_2026_06_29.md`
- `docs/hand_offs/WPR106-561-next-agent-implementation-handoff.md`

## Completion notes

Published the final roadmap and next-agent handoff. The audit validated the
following future implementation priorities:

- USD 10,000 account-notional capacity participation math;
- 5 bps default spread fallback with explicit-unit preference;
- monthly fold validation based on the tested timeline, capped at four folds;
- 10 average trades per usable month and at most 4 losing months per year;
- funding zero-value handling, funding-unit metadata, and `next_bar_open`
  causality tests;
- panel-loading, strategy-compiler, stress-rerun, ledger, worker-claim, and
  strategy-queue speed improvements.

Validation completed:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

Results: compileall passed, `test_autonomy_agent_context_phase79.py` passed
`4` tests, `test_contract_docs.py` passed `2` tests, and `git diff --check`
reported no whitespace errors. It emitted line-ending warnings for pre-existing
dirty files outside this packet.
