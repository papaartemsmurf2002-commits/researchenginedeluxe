# WPR10-11 Candidate Pack Fixture Provenance

Status: closed
Owner: Codex Research Agent
Stage: Stage R10/R11 candidate pack fixture provenance
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Harden research candidate-pack eligibility so a pack can only be written from complete, durable, research-only, fixture-backed evidence. Candidate packs must remain observe-only and non-promotable, and the gate must block when cycle manifests, data source provenance, required outputs, gate reports, stability rows, or candidate backtest evidence are incomplete or live-adjacent.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR10-11-candidate-pack-fixture-provenance.md`
- `docs/stage_reports/STAGE_R10_R11_CANDIDATE_PACK_FIXTURE_PROVENANCE_REPORT.md`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No weakening of candidate acceptance gates.
- No attempt to force synthetic or local fixture tests to produce pack-eligible candidates.
- No long-range real market dataset ingestion.
- No changes to strategy scoring, optimizer ranking, or backtest execution behavior.

## Implementation plan

1. Add candidate-pack gate checks for cycle manifest research/live boundary fields.
2. Require candidate-pack data evidence to come from a validated non-synthetic historical fixture pack.
3. Require complete required output paths before a pack can pass the gate.
4. Require durable candidate gate, stability, and candidate backtest evidence rows to agree with pack eligibility.
5. Add source-data provenance and evidence summary fields to written candidate-pack manifests.
6. Extend tests for successful fixture-backed mock packs, missing data provenance, unsafe cycle flags, missing required outputs, and live-adjacent evidence rejection.

## Exit criteria

- Candidate packs cannot pass from synthetic evidence, missing source provenance, unsafe cycle manifests, missing required outputs, or incomplete candidate backtest evidence.
- Written pack manifests include source fixture provenance and evidence summaries.
- Pack manifests remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Full-cycle local fixture tests continue to write gate reports but do not write packs without research-gate-passed candidates.
- Focused tests, live preflight, contracts, compileall, and diff checks pass.

## Risk controls

- Treat candidate packs as research evidence only; never as promotion or live input.
- Do not alter ranking/scoring to make candidates pass.
- Keep edits confined to WPR10-11 allowed paths.
- Treat earlier uncommitted WPR files in the dirty tree as out of scope.

## Exit evidence

- Candidate-pack gates require cycle manifests to be research-only, observe-only, non-promotable, non-live-signal, non-sizing, non-operator, non-runtime, non-execution, no live-fetch, and no order-placement.
- Candidate-pack gates require validated non-synthetic `historical_fixture_pack` source evidence, fixture ID, existing fixture manifest and dataset paths, matching fixture manifest SHA-256, safe fixture manifest metadata, and matching fixture manifest identity.
- Required outputs are fixed and must exist; declared JSON evidence is rejected when live-adjacent, promotion-ready, non-research, non-observe, or live/control flagged.
- Candidate-specific durable evidence now requires clean passed gate rows, accepted validation-enriched stability rows, candidate-tied metric rows, aggregate/split/cost-stress backtest rows, existing backtest manifests/metrics, safe backtest manifests/metrics, and no execution-cache reuse claims.
- Written candidate-pack manifests include `source_data_evidence`, `evidence_summary`, and explicit non-live runtime/operator/fetch/order flags while remaining `research_only`, `observe_only`, and `promotion_ready: false`.
- Historical fixture-pack cycles emit fixture manifest SHA-256, candidate-tied holding-window metric rows, and only advertise candidate-pack paths after durable gate selection; pack path claims are reset if writing fails.
- Read-only reviewer passes found and rechecked P1/P2 gaps around live-adjacent evidence, fixture identity, metric row completeness, and runner pack-path claims; final rechecks reported no blocking findings.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py tests/historical/test_full_cycle_local_fixture_pack.py tests/live/test_preflight.py -q` passed: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/historical -q` passed: 9 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts tests/live/test_preflight.py -q` passed: 43 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.
