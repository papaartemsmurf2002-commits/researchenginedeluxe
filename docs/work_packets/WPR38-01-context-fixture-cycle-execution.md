# WPR38-01 Context Fixture Cycle Execution

Status: closed
Owner: Codex Research Agent
Stage: Stage R38 context fixture cycle execution
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Run the actual historical research-cycle command against the generated BTCUSDT provider context fixture pack from WPR37, then audit the produced artifacts for research-only provenance, context-family materialization, candidate ranking/gate behavior, and reproducibility limits.

## Allowed paths

- `data/research/historical_cycles/btcusdt_context_provider_cycle/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR38-01-context-fixture-cycle-execution.md`
- `docs/stage_reports/STAGE_R38_CONTEXT_FIXTURE_CYCLE_EXECUTION_REPORT.md`

## Inputs

- Fixture pack manifest: `data/research/fixtures/btcusdt_context_provider_v1/fixture_pack_manifest.json`
- Fixture ID: `btcusdt-context-provider-v1`
- Fixture context families: `funding_rate`, `premium_index`, `open_interest`

## Non-goals

- No legacy chart export, Pine, parity, or synthetic input use.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No tracked canonical config pointing at ignored generated data.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Create an ignored local cycle spec under `data/research/historical_cycles/btcusdt_context_provider_cycle/specs/`.
2. Keep the cycle bounded to one holding window, one context feature set, one context strategy, and a one-candidate metadata search.
3. Execute `run-historical-research-cycle` with `synthetic_fixture: false`.
4. Audit required outputs, data-source provenance, feature context materialization, rankings, gate report, and candidate-pack status.
5. Run the validation baseline and record evidence.
6. Stop and report if the run fails closed in a way that requires code changes outside the packet.

## Exit criteria

- The historical cycle command completes using the generated context fixture pack.
- Research-cycle artifacts are written under ignored `data/research/historical_cycles/btcusdt_context_provider_cycle/**`.
- Feature-build evidence shows funding, premium, and open-interest context joined from the fixture.
- Candidate ranking/gate behavior is recorded truthfully with no live or promotion claim.
- Validation evidence is recorded in the stage report.

## Completion evidence

- Local ignored spec: `data/research/historical_cycles/btcusdt_context_provider_cycle/specs/btcusdt_context_provider_cycle.json`.
- Run output: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/research_cycle_manifest.json`.
- Cycle manifest SHA-256: `452dcc078e9fc5eadef767e06adff8f42d4f1ee1fcfa3f4362fb0406834d1346`.
- Data source: `historical_fixture_pack`, fixture ID `btcusdt-context-provider-v1`.
- Fixture manifest SHA-256: `7c97dfb0abfd8459e72998815b8fee25af42aac78fd0e9bd1cf9ef3523e26464`.
- Fixture context SHA-256: `5a8312582a987b551b2bbb8dbe5ecdd7a2050b12b3a57ecf78b8db7524fd5250`.
- Joined context families: `funding_rate`, `premium_index`, `open_interest`.
- Candidate rows: 4.
- Backtest index rows: 17.
- Candidate pack status: `candidate_pack_written: false`, all gates blocked.
- Scope remains `research_only`, `observe_only`, and `promotion_ready: false`.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only existing LF-to-CRLF normalization warnings.
