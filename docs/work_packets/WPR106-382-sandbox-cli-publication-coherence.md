# WPR106-382 - Sandbox CLI Publication Coherence

## Status

closed

## Objective

Make the staged rapid strategy sandbox package, tests, and CI workflow
publication-coherent by staging the matching sandbox CLI command surface,
research-command registry entries, and live CLI boundary containment tests
without pulling unrelated four-bar research commands into this packet.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`
- `docs/work_packets/WPR106-380-sandbox-ci-validation-coverage.md`

## Allowed paths

- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/live/test_cli_boundary.py`
- `docs/work_packets/WPR106-382-sandbox-cli-publication-coherence.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_CLI_PUBLICATION_COHERENCE_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Stage only sandbox CLI and live-boundary behavior from mixed local files.
- Do not stage unrelated four-bar KNN commands or their untracked modules.
- Sandbox commands must remain research-only, output-root contained, and
  rejected from live-mode command paths.
- Do not execute strict validation, write candidate packs, create paper/live
  signals, define sizing, place orders, change runtime mode, write live config,
  claim candidate evidence, or authorize promotion.

## Acceptance criteria

- The staged `main.py` includes rapid strategy sandbox parser and dispatch
  functions without references to unrelated four-bar command modules.
- The staged research command registry includes sandbox commands for live-mode
  rejection without unrelated four-bar command registrations.
- Live CLI boundary tests cover sandbox output-root containment.
- Focused sandbox and live CLI validation pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --cached --check
```

Exit evidence:

- Staged `src/tradingbotsuite/main.py` and
  `src/tradingbotsuite/research/command_registry.py` parse successfully from
  the Git index.
- Staged sandbox CLI/registry blobs contain no unrelated four-bar command
  references.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  passed with 26 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q` passed
  with 220 tests.
- `python -m compileall -q src\tradingbotsuite` passed.

## Stop conditions

- The staged CLI surface requires unrelated untracked modules.
- Sandbox commands are not registered as research commands for live rejection.
- Any command can write outside the configured research output root.
