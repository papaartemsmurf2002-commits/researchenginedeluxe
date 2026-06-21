# WPR106-418 V2 Foundation Baseline Stabilization

Status: closed
Owner: Codex Manager Development Agent
Created: 2026-06-21

## Objective

Stabilize the current uncommitted v2 foundation so later autonomous-loop
implementation starts from a committed, auditable baseline. This packet
classifies the existing WPR106-388 through WPR106-417 v2 foundation files,
runs focused baseline validation, stages intentional files only, commits the
baseline, pushes it when credentials/remotes permit, and records the resulting
evidence.

This packet does not implement new strategy behavior, run collectors, run
backtests, write generated research evidence, create candidate packs, place
orders, produce paper/live signals, emit sizing instructions, change runtime
mode, or create promotion-ready artifacts.

## Audit IDs

- `V2-AUD-STAB-001`

## Dependencies

- `docs/REDX_V2_AGENTING_DEVELOPMENT_EXECUTION_BRIEF_2026_06_21.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`

## Allowed Paths

Classification/staging scope:

- `AGENTS.md`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/BRANCH_PURPOSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/REDX_V2_AGENTING_DEVELOPMENT_EXECUTION_BRIEF_2026_06_21.md`
- `docs/REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md`
- `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`
- `docs/RESEARCH_ROADMAP_DIRECTION_COMPARISON_2026_06_20.md`
- `docs/V2_*.md`
- `docs/audit/**`
- `docs/contracts/*_contract.md`
- `docs/work_packets/WPR106-388-*.md`
- `docs/work_packets/WPR106-389-*.md`
- `docs/work_packets/WPR106-390-*.md`
- `docs/work_packets/WPR106-391-*.md`
- `docs/work_packets/WPR106-392-*.md`
- `docs/work_packets/WPR106-393-*.md`
- `docs/work_packets/WPR106-394-*.md`
- `docs/work_packets/WPR106-395-*.md`
- `docs/work_packets/WPR106-396-*.md`
- `docs/work_packets/WPR106-397-*.md`
- `docs/work_packets/WPR106-398-*.md`
- `docs/work_packets/WPR106-399-*.md`
- `docs/work_packets/WPR106-400-*.md`
- `docs/work_packets/WPR106-401-*.md`
- `docs/work_packets/WPR106-402-*.md`
- `docs/work_packets/WPR106-403-*.md`
- `docs/work_packets/WPR106-404-*.md`
- `docs/work_packets/WPR106-405-*.md`
- `docs/work_packets/WPR106-406-*.md`
- `docs/work_packets/WPR106-407-*.md`
- `docs/work_packets/WPR106-408-*.md`
- `docs/work_packets/WPR106-409-*.md`
- `docs/work_packets/WPR106-410-*.md`
- `docs/work_packets/WPR106-411-*.md`
- `docs/work_packets/WPR106-412-*.md`
- `docs/work_packets/WPR106-413-*.md`
- `docs/work_packets/WPR106-414-*.md`
- `docs/work_packets/WPR106-415-*.md`
- `docs/work_packets/WPR106-416-*.md`
- `docs/work_packets/WPR106-417-*.md`
- `docs/work_packets/WPR106-418-v2-foundation-baseline-stabilization.md`
- `src/tradingbotsuite/v2/**`
- `tests/v2/**`

Update scope for this packet's own evidence:

- `docs/work_packets/WPR106-418-v2-foundation-baseline-stabilization.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

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
- legacy GUI/web/operator paths
- `src/tradingbot/**`
- `.env`, credential files, local SQLite operator DBs, private caches

## Boundary Constraints

- The packet may classify, validate, stage, commit, and push the existing v2
  foundation, but it may not expand source behavior beyond the existing
  WPR106-388 through WPR106-417 foundation scope.
- No generated research evidence may be rewritten.
- No live, paper, order, sizing, runtime-mode, candidate-pack, or promotion
  behavior may be added or implied.
- Python 3.14 local validation may be used only as non-authoritative support;
  Python 3.11 validation is preferred and must be reported explicitly.
- If push or credentials fail, record the blocker and keep the goal active.

## Acceptance Criteria

- Current modified and untracked files are classified as intentional v2
  foundation, packet evidence, or blocker/temporary files.
- Focused baseline validation is run with exact commands and results.
- The packet records Python version, branch, pre-baseline SHA, and validation
  limitations.
- Intentional files are staged and committed.
- Baseline is pushed when possible.
- Control docs record the baseline stabilization without claiming
  autonomous-ready, candidate-ready, paper-ready, live-ready, sizing-ready,
  order-ready, runtime-ready, or promotion-ready status.

## Expected Validation

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
git diff --check
```

If Python 3.11 dependencies are incomplete, record the exact failure and use
the next scoped packet to repair validation environment pinning.

## Stop Conditions

- A P0 or P1 issue is found; record it in `docs/KNOWN_ISSUES.md` before
  closing.
- The tree contains unexplained temporary, credential, generated-evidence, or
  local-state files.
- Staging would include no-touch path changes not already scoped by the v2
  foundation packets.
- Validation failures point to source behavior rather than environment setup.

## Completion Notes

Closed on 2026-06-21.

Baseline commit:

- `9bea1b87025fb8b17df54362101b6d3ffb0213d6`

Classification:

- Modified top-level control docs, v2 source docs, v2 package code, and v2
  tests were classified as intentional WPR106-388 through WPR106-417 v2
  foundation work plus WPR106-418/WPR106-419 stabilization evidence.
- No generated research evidence, credential files, local SQLite operator DBs,
  private caches, legacy GUI paths, live/runtime/order/sizing/promotion paths,
  `src/tradingbot/**`, or candidate-pack truth-layer paths were staged.
- The staged file set contained docs, `src/tradingbotsuite/v2/**`, and
  `tests/v2/**`.

Decisions made:

- Baseline commit was delayed until independent boundary review completed.
- Two P1 findings were fixed before baseline commit rather than merely logged:
  - `ISSUE-R106-027`: official S3 backfill accepted arbitrary local source
    files;
  - `ISSUE-R106-028`: signal-bearing v2 artifacts omitted the full boundary
    invariant.
- Fake provider-shaped secret fixtures were replaced with neutral redaction
  fixtures before push so repository history does not resemble real
  credentials.
- Python 3.11 compile evidence is authoritative for syntax, but Python 3.11
  test evidence is still blocked until the 3.11 environment has pytest/dev
  dependencies installed.

Validation:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_security_hygiene_phase21.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_microstructure_collection_phase17.py tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --cached --check
```

Result:

- Python 3.11 compile passed.
- Python 3.11 pytest command could not run because the local Python 3.11
  interpreter has no `pytest` module installed.
- Focused security hygiene test passed: 14 passed.
- Focused WPR106-419 tests passed: 28 passed.
- Full v2 tests passed after P1 fixes and whitespace cleanup: 173 passed.
- Contract tests passed in the default local Python environment: 462 passed.
- Cached diff hygiene passed after mechanical whitespace cleanup.

Open blockers:

- `ISSUE-R106-026` remains open as a P2 local Windows/async validation
  environment risk.
- `ISSUE-R106-020` remains open as P2 strategy/exit semantics debt and as a
  pre-autonomy blocker under the execution brief.
- Final autonomous-ready status is not claimed; this packet only stabilizes the
  v2 foundation baseline.
