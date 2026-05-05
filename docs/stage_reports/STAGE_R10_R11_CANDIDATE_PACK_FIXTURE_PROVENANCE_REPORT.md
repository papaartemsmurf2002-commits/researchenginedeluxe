# Stage R10/R11 Candidate Pack Fixture Provenance Report

Status: closed - candidate pack fixture provenance hardened
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This wave completed a bounded R10/R11 candidate-pack hardening slice:

- Research candidate-pack gates now require validated non-synthetic historical fixture-pack provenance.
- Fixture provenance includes source type, fixture ID, validation payload, fixture manifest path, fixture manifest SHA-256 verification, dataset existence, safe fixture manifest metadata, and matching fixture identity.
- Cycle manifests and evidence JSON are rejected when live-adjacent, promotion-ready, non-research, non-observe, or live/control flagged.
- Required candidate-pack outputs are fixed and must exist before pack eligibility can pass.
- Candidate durable evidence requires clean passed gate rows, accepted validation-enriched stability rows, candidate-tied metric rows, aggregate/split/cost-stress backtest rows, safe backtest manifests/metrics, and no execution-cache reuse claims.
- Historical research-cycle runner pack paths now derive from the durable gate and reset if pack writing fails.
- Holding-window metrics now include candidate-tied rows so candidate-pack evidence cannot rely on shared window aggregates.

## Path Audit

WPR10-11-specific edits were confined to the packet's allowed paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR10-11-candidate-pack-fixture-provenance.md`
- `docs/stage_reports/STAGE_R10_R11_CANDIDATE_PACK_FIXTURE_PROVENANCE_REPORT.md`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`

`docs/KNOWN_ISSUES.md` and `tests/live/test_preflight.py` remained allowed but did not need edits. The working tree still contains many earlier uncommitted WPR files and modifications already represented in the ledger. Those prior packet changes are out of scope for this WPR10-11 closure and were not reverted or normalized.

## Research Boundary

All candidate-pack artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `intended_use: research_observe_only`
- no live signal, sizing, operator, execution, runtime, live-fetch, or order-placement use

No live, paper, shadow, testnet, canary, promotion, order-placement, live-mode mutation, capital allocation, ranking/scoring change, or backtest behavior change was added.

## Review Resolution

Read-only reviewers identified and rechecked these issues:

- Fixture source provenance was not required. Resolved by requiring validated non-synthetic `historical_fixture_pack` evidence with manifest hash and dataset existence.
- Cycle and evidence JSON could be live-adjacent. Resolved by checking cycle manifests, required JSON outputs, fixture manifests, backtest manifests, and backtest metrics for live/promotion/control flags.
- Required outputs and candidate backtest evidence were incomplete. Resolved by requiring fixed outputs, candidate-tied metric rows, aggregate/split/cost-stress backtest scopes, existing manifests/metrics, and no execution-cache reuse claims.
- Durable gate rows could disagree with pack eligibility. Resolved by requiring `gate_status == "passed"`, `pack_eligible is true`, and empty `gate_reasons`.
- Runner pack paths could be declared before durable write success. Resolved by deriving pack IDs from the durable gate and resetting pack-path claims if writing fails.
- Holding-window evidence could rely on shared window aggregates. Resolved by making holding-window metrics candidate-tied and requiring `candidate_id` rows for all candidate metric evidence.

Final reviewer rechecks reported no remaining blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py tests/historical/test_full_cycle_local_fixture_pack.py tests/live/test_preflight.py -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 9 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts tests/live/test_preflight.py -q` passed: 43 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Remaining Limitations

- Candidate-pack eligibility remains research-only and observe-only; it does not promote candidates or imply live readiness.
- The local fixture-pack full-cycle test still writes gate reports but no candidate packs because empirical candidate acceptance remains blocked.
- Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
