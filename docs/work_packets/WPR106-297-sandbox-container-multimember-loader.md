# WPR106-297 Sandbox Container Multimember Loader

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expand sandbox ZIP and TAR/TGZ local archive loading so containers with
multiple market-data members of the selected priority class are loaded as one
combined 2024+ market frame instead of silently using only the first member.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-297-sandbox-container-multimember-loader.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CONTAINER_MULTIMEMBER_LOADER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, download provider data, mutate source archive files, extract
  archive members to disk, or claim promotion readiness.
- Preserve the 2024+ sandbox date floor and completed-row normalization.
- Preserve deterministic archive descriptor IDs, trial IDs, rankings,
  evidence-request descriptors, blocker semantics, source-integrity metadata,
  and sandbox boundary flags.
- Preserve member priority semantics: select the highest-priority available
  member type and concatenate only members of that selected type.
- Use deterministic member-name ordering for combined frames.

## Plan

1. Load every ZIP/TAR member for the selected priority suffix instead of only
   the first member.
2. Concatenate raw member frames before market normalization, preserving
   source-transformation metadata such as Hyperliquid L2 flattening counts.
3. Add focused tests for multi-member ZIP JSONL loading, TAR CSV loading, and
   archive manifest row counts.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Completion Notes

Implemented and closed on 2026-06-19. ZIP and TAR/TGZ sandbox loading now
selects the highest-priority available market-data member suffix, loads every
member of that selected suffix in deterministic member-name order, and
concatenates the raw frames before 2024+ market normalization. Containers still
do not mix lower-priority member types into the loaded frame. Source
transformation metadata, including Hyperliquid L2 flattening row counts, is
merged across member frames before normalization metadata is written.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "multimember or concatenates_zip or concatenates_tar"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused container multimember tests passed, 157 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
