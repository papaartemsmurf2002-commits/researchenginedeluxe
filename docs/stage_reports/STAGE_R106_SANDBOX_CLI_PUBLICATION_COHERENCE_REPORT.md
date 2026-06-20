# Stage R106 Sandbox CLI Publication Coherence Report

## Summary

WPR106-382 closes the sandbox CLI publication-coherence gap left after staging
the sandbox package, tests, and CI coverage. The packet stages the matching
canonical CLI parser/dispatch surface, research-command registry entries, and
live CLI boundary containment tests for the Rapid Strategy Iteration Sandbox.

The source files involved also contain unrelated local four-bar KNN command
work in the working tree. This packet deliberately stages index-filtered
sandbox-only blobs for `src/tradingbotsuite/main.py` and
`src/tradingbotsuite/research/command_registry.py` so the sandbox can be
published coherently without pulling unrelated untracked modules into this
review surface.

## Implemented

- Staged the sandbox CLI command surface from `src/tradingbotsuite/main.py`.
- Staged the sandbox research-command registry entries used for live-mode
  rejection.
- Staged live CLI boundary tests that enforce sandbox output-root containment.
- Verified the staged CLI/registry blobs parse and contain no unrelated
  four-bar command references.

## Followed Audit And Roadmap Items

- Followed the Phase 0 repo-state stabilization requirement by repairing a
  staged-code coherence gap before additional sandbox feature work.
- Followed the audit commit-coherence finding by making the staged sandbox
  package, tests, workflow, CLI, and registry match each other.
- Preserved the strict validation boundary: sandbox commands can request later
  descriptor-only validation work, but cannot validate, promote, or write
  candidate artifacts.

## Deviations

The packet uses index-only staging for two mixed local source files instead of
editing the working tree back to a sandbox-only shape. That is intentional: the
working tree contains unrelated four-bar KNN research command work owned by
other local packets, and reverting it would violate the dirty-worktree rule.
The staged review surface is therefore coherent while the unrelated work remains
unstaged.

## Validation

```powershell
# Staged-index Python AST parse for:
# - src/tradingbotsuite/main.py
# - src/tradingbotsuite/research/command_registry.py

git diff --cached -- src\tradingbotsuite\main.py src\tradingbotsuite\research\command_registry.py |
  Select-String -Pattern 'four_bar|FOUR_BAR|build-four|run-four|map-binance'

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
```

Results:

- Staged-index Python AST parse passed.
- Four-bar command reference scan over the staged CLI/registry diff returned no
  matches.
- `tests\live\test_cli_boundary.py`: 26 passed.
- `tests\research_sandbox`: 220 passed.
- Package compileall passed.

## Broader Validation Note

The roadmap's full-suite command was also attempted after packet validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider
```

It timed out after 904 seconds without pass/fail evidence. No lingering Python
test process remained after the timeout. The two audit-named H2 regressions were
rerun directly and passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\optimization\test_search_space_expansion.py::test_holding_window_search_space_includes_metadata_and_window_defaults tests\research_discovery\test_discovery_runner.py::test_discovery_runner_large_zero_stop_resume_recovers_lag_without_full_hydration -q
```

Result: 2 passed.

## Boundary Confirmation

This packet does not execute sandbox sweeps, strict validation, candidate-pack
assembly, live trading, paper trading, sizing, order placement, runtime-mode
changes, live-configuration writes, candidate-evidence claims, or promotion
actions. Sandbox outputs remain research-only, observe-only, sandbox-only,
non-promotable, non-candidate-evidence, and descriptor-only for strict
validation handoff.
