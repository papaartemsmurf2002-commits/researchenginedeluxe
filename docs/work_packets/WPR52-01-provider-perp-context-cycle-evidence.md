# WPR52-01 Provider Perp Context Cycle Evidence

Owner: Codex Research Agent
Status: closed
Stage: R52 provider perp context cycle evidence
Date opened: 2026-05-05

## Goal

Run BTCUSDT provider-backed historical cycle evidence with `features_perp_context_v2` and `perp_basis_convergence_v2`, preserving fail-closed research gates and non-promotion evidence boundaries.

## Allowed Paths

```text
configs/research/full_cycle_btcusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
src/tradingbotsuite/strategies/no_trade.py
tests/contracts/test_research_cycle_contract.py
tests/contracts/test_strategy_contracts.py
tests/historical/
docs/work_packets/WPR52-01-provider-perp-context-cycle-evidence.md
docs/stage_reports/STAGE_R52_PROVIDER_PERP_CONTEXT_CYCLE_EVIDENCE_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Use non-synthetic provider fixture evidence.
- Prefer durable repo fixtures and Binance public-source fixtures already present in the branch.
- Use Crypto Lake free sample only as diagnostic fallback; do not use it as durable cycle evidence in this packet.
- Candidate gates remain fail-closed.
- No candidate pack is expected unless all existing gates pass.
- Blocked candidates are acceptable when recorded truthfully.
- Do not claim OOS acceptance or promotion readiness.
- Do not touch live execution, promotion, order placement, or runtime mode.

## Required Work

- Add checked research cycle spec `full_cycle_btcusdt_perp_context_v2.json`.
- Ensure the no-trade comparator can run against `features_perp_context_v2` without adding trading behavior.
- Add historical/contract coverage proving the checked spec consumes the provider context fixture, materializes v2 features, includes `perp_basis_convergence_v2`, writes backtest/index/ranking artifacts, and remains research-only/non-promotable.
- Run the checked provider-backed cycle into `data/research/historical_cycles/btcusdt_perp_context_v2_foundation`.
- Record gate outcome truthfully, including blocked candidates if evidence floors do not pass.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\historical -q
```

## Close Evidence

Record validation results, touched paths, cycle artifact paths, gate outcomes, and remaining risks in `docs/stage_reports/STAGE_R52_PROVIDER_PERP_CONTEXT_CYCLE_EVIDENCE_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R52_PROVIDER_PERP_CONTEXT_CYCLE_EVIDENCE_REPORT.md`.
