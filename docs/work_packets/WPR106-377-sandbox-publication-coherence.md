# WPR106-377 - Sandbox Publication Coherence

## Status

closed

## Objective

Resolve the audit H1 publication blocker for the Rapid Strategy Iteration
Sandbox by adding the intended sandbox source, tests, and smoke config to the
Git index, while removing tracked pytest cache noise from the index without
deleting local cache files.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-365-sandbox-commit-coherence-classification.md`
- `docs/work_packets/WPR106-376-deterministic-archive-fixture-checksums.md`

## Allowed paths and index actions

- Stage tracked content under `src/tradingbotsuite/research_sandbox/**`.
- Stage tracked content under `tests/research_sandbox/**`.
- Stage tracked content under `configs/sandbox/**`.
- Stage `docs/contracts/sandbox_research_contract.md`.
- Stage `.gitignore` because the existing `/outputs/` ignore rule is part of
  generated-output hygiene.
- Stage this packet and its stage report.
- Stage `docs/ACTIVE_INDEX.md` and `docs/ORCHESTRATOR_STAGE_LEDGER.md`.
- Remove tracked `.pytest_cache/**` entries from the Git index only; do not
  delete local cache files.

## Boundary constraints

- Do not stage unrelated dirty tracked files or unrelated untracked research
  experiment artifacts.
- Do not delete generated outputs or user files.
- Do not change sandbox runtime semantics except through already-completed
  packets.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live
  configuration, claim candidate evidence, or authorize promotion.

## Acceptance criteria

- `git ls-files src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox`
  returns the intended sandbox files.
- `git ls-files --others --exclude-standard src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox`
  returns no intended sandbox source/test/config files.
- `.pytest_cache` is ignored and no longer tracked in the index.
- `tradingbotsuite.main` imports from the staged sandbox package.
- Focused sandbox validation still passes.

## Validation

```powershell
git ls-files src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox
git ls-files --others --exclude-standard src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox
git ls-files .pytest_cache
$env:PYTHONPATH='src'; python -c "import tradingbotsuite.main"
$env:PYTHONPATH='src'; python -m tradingbotsuite.main --help
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
git diff --check
```

Exit evidence:

- `git ls-files src/tradingbotsuite/research_sandbox tests/research_sandbox configs/sandbox | Measure-Object`
  - `35`
- `git ls-files --others --exclude-standard src\tradingbotsuite\research_sandbox tests\research_sandbox configs\sandbox`
  - no output
- `git ls-files .pytest_cache`
  - no output
- `$env:PYTHONPATH='src'; python -c "import tradingbotsuite.main"`
  - passed
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main --help`
  - passed and listed rapid strategy sandbox commands
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `212 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only
- `git diff --cached --check`
  - passed

## Stop conditions

- Staging would need to include unrelated local research artifacts or generated
  outputs to make imports work.
- Import smoke fails from the staged sandbox surface.
- `.pytest_cache` removal would delete local files instead of only untracking
  generated cache state.
